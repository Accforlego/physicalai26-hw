"""Run the declared selection once, inspect outputs, then record via --record.

Run from hw1 using the habitat Python environment. No GT is used to select
frames or estimate poses. The sealed baseline and factor evidence are preserved.
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import api
import reconstruct
import utils
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true",
                        help="Record the already inspected result without rerunning")
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    out = workspace / "analysis"
    ttl = workspace / "phase1_baseline.ttl"
    query = workspace / "queries/conservative_depth_icp.rq"
    exp = api.read_experiment(str(ttl))
    frames = api.frames_from_sparql_query(exp, str(query))
    segments = reconstruct._segments_from_frames(frames)
    metadata = reconstruct._segment_metadata(segments)
    query_digest = hashlib.sha256(query.read_bytes()).hexdigest()

    if args.record:
        result = json.loads((out / "intervention_results.json").read_text())
        if result["frames"] != frames or result["query_sha256"] != query_digest:
            raise ValueError("Selection differs from the inspected reconstruction")
        api.write_run(str(ttl), "selected",
                      {"mapMeanL2": result["selected_mean_l2_m"]},
                      used_frames=frames, frame_count=len(frames), metadata=metadata)
        api.read_experiment(str(ttl))  # Verify seal and occurrence completeness.
        print("Recorded selected run; original baseline and factor evidence preserved.")
        return

    if (out / "intervention_results.json").exists():
        raise FileExistsError("This treatment already has results; create a new snapshot directory for a new experiment.")

    started = time.perf_counter()
    print(f"Selected {len(frames)} frames; metadata={metadata}", flush=True)
    print("Starting Open3D reconstruction: voxel=0.05 m, seed=0", flush=True)
    pipeline_started = time.perf_counter()
    cloud, pred_camera = utils.reconstruct(
        exp["batch_path"], version="open3d", voxel_size=0.05,
        registration_seed=0, frames=frames, build_cloud=True, verbose=True)
    pipeline_seconds = time.perf_counter() - pipeline_started
    if len(pred_camera) != len(frames):
        raise ValueError("Not all selected frames were reconstructed")

    # Only now load GT for evaluation, mapping frame stems to capture ordinals.
    data = Path(exp["batch_path"])
    stems = sorted(int(p.stem) for p in (data / "rgb").glob("*.png"))
    rows = [stems.index(i) for i in frames]
    gt_raw = np.load(data / "GT_pose.npy")[rows]
    rotation0 = Rotation.from_quat(gt_raw[0, [4, 5, 6, 3]]).as_matrix()
    gt = (gt_raw[:, :3] - gt_raw[0, :3]) @ rotation0
    pred = pred_camera @ utils.CAM_TO_GT_AXES
    errors = np.linalg.norm(pred - gt, axis=1)
    scored = utils.visualize_and_evaluate(
        cloud, pred_camera, str(data), frames=frames, show=False)
    if not np.isclose(scored, errors.mean(), rtol=0, atol=1e-12):
        raise ValueError("Independent per-frame scoring differs from course evaluator")
    baseline = np.load(out / "trajectory_diagnostic.npz")
    baseline_rows = [list(baseline["frames"]).index(i) for i in frames]
    baseline_common = baseline["error"][baseline_rows]
    np.savez(out / "selected_trajectory.npz", frames=frames, pred=pred,
             pred_camera=pred_camera, gt=gt, error=errors)

    # A ceiling-cropped top view with fixed metric axes and unoccluded trajectories.
    # This is a visualization downsample only; registration has already finished.
    display = cloud.voxel_down_sample(0.04)
    xyz = np.asarray(display.points) @ utils.CAM_TO_GT_AXES
    colors = np.asarray(display.colors)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(xyz[:, 0], xyz[:, 2], c=colors, s=0.6, linewidths=0, rasterized=True)
    ax.plot(gt[:, 0], gt[:, 2], color="black", lw=2.2, label="GT", zorder=4)
    ax.plot(pred[:, 0], pred[:, 2], color="red", lw=1.2, label="Estimated", zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("First-camera X (m)")
    ax.set_ylabel("First-camera Z (m)")
    ax.margins(0.04)
    ax.legend()
    ax.set_title(f"Selected reconstruction: {len(frames)}/191 frames | Mean L2 {scored*100:.2f} cm")
    fig.tight_layout()
    fig.savefig(workspace / "reconstruction_selected.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].plot(gt[:, 0], gt[:, 2], color="black", lw=2, label="GT")
    axes[0].plot(baseline["pred"][:, 0], baseline["pred"][:, 2],
                 color="steelblue", lw=1, label="Baseline")
    axes[0].plot(pred[:, 0], pred[:, 2], color="red", lw=1, label="Selected")
    axes[0].set_aspect("equal")
    axes[0].set_xlabel("First-camera X (m)")
    axes[0].set_ylabel("First-camera Z (m)")
    axes[0].legend()
    axes[1].plot(baseline["frames"], baseline["error"]*100,
                 color="steelblue", label="Baseline (191 frames)")
    axes[1].plot(frames, errors*100, color="red", label="Selected (retained frames)")
    axes[1].scatter(sorted(set(stems)-set(frames)),
                    np.zeros(len(stems)-len(frames)), marker="x", color="gray",
                    label="Excluded frames")
    axes[1].set_xlabel("Original frame index")
    axes[1].set_ylabel("Position L2 error (cm)")
    axes[1].legend()
    for ax in axes:
        ax.grid(alpha=0.2)
    fig.suptitle("Conservative depth + ICP selection | voxel=0.05 m, seed=0")
    fig.tight_layout()
    fig.savefig(out / "intervention_comparison.png", dpi=160)
    plt.close(fig)

    result = {
        "frames": frames, "removed_frames": sorted(set(stems)-set(frames)),
        "query_sha256": query_digest,
        "selected_mean_l2_m": float(scored),
        "baseline_all_mean_l2_m": float(baseline["error"].mean()),
        "baseline_common_frames_mean_l2_m": float(baseline_common.mean()),
        "selected_max_l2_m": float(errors.max()),
        "selected_max_error_frame": int(frames[int(errors.argmax())]),
        "retained_fraction": len(frames)/len(stems),
        "reconstruction_seconds": pipeline_seconds,
        "total_seconds": time.perf_counter()-started,
        "timing_scope": "query excluded; reconstruction, evaluation, NPZ and plot output included",
        "baseline_runtime_seconds": None,
        "voxel_size_m": 0.05, "seed": 0, "icp_backend": "open3d",
        "map_point_count_after_ceiling_removal": len(cloud.points),
        **metadata,
    }
    (out / "intervention_results.json").write_text(json.dumps(result, indent=2)+"\n")
    with (out / "intervention_comparison.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run", "frame_count", "mean_l2_m", "retained_fraction",
                         "reconstruction_seconds", "total_seconds", "voxel_size_m", "seed"])
        writer.writerow(["baseline_recorded", len(stems), baseline["error"].mean(), 1,
                         "not recorded", "not recorded", 0.05, 0])
        writer.writerow(["baseline_on_selected_frames", len(frames), baseline_common.mean(),
                         len(frames)/len(stems), "not rerun", "not rerun", 0.05, 0])
        writer.writerow(["selected", len(frames), scored, result["retained_fraction"],
                         pipeline_seconds, result["total_seconds"], 0.05, 0])
    print(json.dumps({k:v for k,v in result.items() if k!="frames"}, indent=2), flush=True)
    print("Dry run complete. Inspect outputs, then use --record to save selected evidence.")


if __name__ == "__main__":
    main()
