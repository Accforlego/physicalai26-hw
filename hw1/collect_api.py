"""Collect RGB-D by actual Habitat navigation, without pygame keyboard input.

Navigation uses the simulator NavMesh, not reconstruction or estimated poses.
The resulting GT is evaluation-only input to the reconstruction pipeline.
"""
import argparse
import json
from pathlib import Path

import habitat_sim
import numpy as np

from simulator import (Engine, ZoneScheduler, load_config, prepare_capture_dirs,
                       save_frame, zone_frame_counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/second_floor.yaml")
    parser.add_argument("--output-root", default="eval/_data/second_floor/115062519_api")
    parser.add_argument("--navigation-seed", type=int, default=20)
    args = parser.parse_args()
    root = Path(args.output_root)
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite existing capture: {root}")
    cfg = load_config(args.config)
    cfg["output"].update(root=str(root), clear_existing=False)
    prepare_capture_dirs(cfg, str(root))
    scheduler = ZoneScheduler(cfg["uncertainties"]) if cfg["uncertainties"]["enabled"] else None
    engine = Engine(cfg, scheduler=scheduler, fps_nominal=30)
    poses, trace, reached, failed = [], [], [], []
    goals = []
    start_requested = np.asarray(cfg["agent"]["start_position"], dtype=float)
    action_index = 0
    initial = None
    island = None
    samples = np.empty((0, 3))
    completed = False

    def save_progress():
        array = np.asarray(poses, dtype=np.float32).reshape(-1, 7)
        np.save(root / "GT_pose.npy", array)
        metadata = {
            "collection_mode": "automatic actual discrete-action navigation (not manual, not teleport replay)",
            "source_config": args.config, "config": cfg,
            "navigation_seed": args.navigation_seed,
            "requested_start": start_requested.tolist(),
            "navmesh_start": None if initial is None else initial.tolist(),
            "navmesh_island": island,
            "goals": goals, "reached": reached, "failed": failed,
            "frame_count": len(poses), "action_count": action_index,
            "completed_route": completed,
            "time_policy": "observe(action_index / 30); deterministic action-time clock",
            "capture_policy": "initial, each 0.2 m forward action, every second 6-degree turn, and goal arrival",
            "zone_frame_counts": zone_frame_counts(cfg, array) if len(array) else {},
        }
        if len(array) and len(samples):
            # Navigation-route support proxy, not a map completeness metric.
            dist = np.linalg.norm(samples[:, None, [0, 2]] - array[None, :, [0, 2]], axis=2)
            metadata["nav_sample_fraction_within_1_5m_of_capture"] = float((dist.min(axis=1)<=1.5).mean())
        (root / "capture_metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
        (root / "action_trace.json").write_text(json.dumps(trace, indent=2)+"\n")

    last_capture_action = -1

    def capture(reason):
        nonlocal last_capture_action
        if last_capture_action == action_index:
            return
        if len(poses) >= 480:
            raise RuntimeError("Capture limit reached; partial data preserved")
        frame = engine.observe(action_index / 30.0)
        state = engine.agent.get_state().sensor_states["color_sensor"]
        poses.append(save_frame(frame, state, str(root), cfg["output"], len(poses)+1))
        last_capture_action = action_index
        trace.append({"kind": "capture", "frame": len(poses), "after_action": action_index,
                      "reason": reason, "sensor_pose": [float(v) for v in poses[-1]]})
        save_progress()
        if len(poses)%25 == 0:
            print(f"Captured {len(poses)} frames, {action_index} navigation actions", flush=True)

    try:
        pf = engine.sim.pathfinder
        if not pf.is_loaded:
            raise RuntimeError("Scene has no loaded NavMesh")
        initial = np.asarray(pf.snap_point(start_requested), dtype=float)
        if not np.isfinite(initial).all():
            raise RuntimeError("Configured start cannot be snapped to NavMesh")
        island = int(pf.get_island(initial))
        state = engine.agent.get_state()
        state.position = initial.astype(np.float32)
        engine.agent.set_state(state)
        pf.seed(args.navigation_seed)
        samples = np.asarray([pf.get_random_navigable_point(island_index=island) for _ in range(400)])
        samples = samples[np.abs(samples[:, 1]-initial[1])<0.35]
        if not len(samples):
            raise RuntimeError("No navigable samples at the configured floor")

        # Include quality zones explicitly, then add spatially separated targets.
        for zone in cfg["uncertainties"]["zones"]:
            x, z = zone["center"]
            goal = np.asarray(pf.snap_point(np.array([x, initial[1], z]), island_index=island))
            if not np.isfinite(goal).all() or np.linalg.norm(goal[[0,2]]-[x,z])>=zone["radius"]:
                raise RuntimeError(f"Cannot navigate inside zone {zone['name']}")
            goals.append({"name": zone["name"], "position": goal.tolist()})
        anchors = [initial] + [np.asarray(g["position"]) for g in goals]
        for i in range(4):
            distance = np.linalg.norm(samples[:,None,[0,2]]-np.asarray(anchors)[None,:,[0,2]],axis=2).min(axis=1)
            farthest = int(distance.argmax())
            if distance[farthest]<1.8:
                break
            point = samples[farthest].copy()
            goals.append({"name": f"coverage_{i+1}", "position": point.tolist()})
            anchors.append(point)

        def geodesic(goal):
            path = habitat_sim.ShortestPath()
            path.requested_start = engine.agent.get_state().position
            path.requested_end = np.asarray(goal["position"], dtype=np.float32)
            return float(path.geodesic_distance) if pf.find_path(path) else float("inf")

        remaining = list(goals)
        ordered = []
        # Choose next goal at run time from the actual reached position.
        capture("initial_navmesh_start")
        while remaining:
            goal = min(remaining, key=geodesic)
            remaining.remove(goal)
            ordered.append(goal["name"])
            print(f"Navigating to {goal['name']}: {goal['position']}", flush=True)
            follower = engine.sim.make_greedy_follower(
                0, goal_radius=0.25, stop_key="stop", forward_key="move_forward",
                left_key="turn_left", right_key="turn_right")
            consecutive_turns = 0
            arrived = False
            try:
                for _ in range(400):
                    action = follower.next_action_along(np.asarray(goal["position"],dtype=np.float32))
                    if action in (None, "stop"):
                        arrived = True
                        break
                    if action_index>=1800:
                        raise RuntimeError("Navigation limit reached")
                    before = engine.agent.get_state().position.copy()
                    engine.step(action)
                    action_index += 1
                    after = engine.agent.get_state().position.copy()
                    trace.append({"kind": "action", "index": action_index, "action": action,
                                  "before": before.tolist(), "after": after.tolist()})
                    if action=="move_forward":
                        consecutive_turns = 0
                        capture("forward")
                    else:
                        consecutive_turns += 1
                        if consecutive_turns%2==0:
                            capture("turn")
            except habitat_sim.errors.GreedyFollowerError as error:
                failed.append({"name": goal["name"], "error": str(error)})
            if arrived:
                reached.append(goal["name"])
                capture("goal_arrival")
            elif not any(g["name"]==goal["name"] for g in failed):
                failed.append({"name":goal["name"],"error":"goal action limit reached"})
            save_progress()
        completed = not failed
        capture("route_end")
        save_progress()
        print("CAPTURE_COMPLETE", json.dumps({"root":str(root.resolve()),"frames":len(poses),
              "actions":action_index,"reached":reached,"failed":failed,
              "zones":zone_frame_counts(cfg,np.asarray(poses))}),flush=True)
    finally:
        save_progress()
        engine.close()


if __name__ == "__main__":
    main()
