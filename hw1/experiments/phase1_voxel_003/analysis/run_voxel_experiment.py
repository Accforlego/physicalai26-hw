"""Measure a fresh full-batch voxel=0.03 m treatment, then --record its run.

Run from hw1. Existing results and sealed experiments are never overwritten.
GT is loaded only after reconstruction for evaluation, not pose estimation.
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
import utils
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VOXEL_SIZE = 0.03
SEED = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    out = workspace / "analysis"
    ttl = workspace / f"{workspace.name}.ttl"
    if api.is_assessed(str(ttl)):
        raise FileExistsError("This experiment is sealed; create a new declaration instead of overwriting it")
    decl = api.read_declaration(str(ttl))
    frames = api._pair_frames(decl["batch_path"])
    stems = [int(stem) for stem, _, _ in frames]
    declaration_sha = hashlib.sha256(ttl.read_bytes()).hexdigest()
    if args.record:
        result = json.loads((out / "results.json").read_text())
        if declaration_sha != result["declaration_sha256"] or stems != result["frames"]:
            raise ValueError("Declaration or frame set differs from the measured run")
        records = json.loads((out / "pipeline_measurements.json").read_text())
        frame_records = {tuple(key): value for key, value in records["frame"]}
        pair_records = {tuple(key): value for key, value in records["pair"]}
        api.seal_experiment(str(ttl), decl, frames,
                            pipeline_frame_records=frame_records,
                            pipeline_pair_records=pair_records)
        api.write_run(str(ttl), "baseline", {"mapMeanL2": result["mean_l2_m"]},
                      frame_count=len(stems))
        api.read_experiment(str(ttl))
        print("Recorded new full-batch treatment with fresh pipeline evidence.")
        return
    if (out / "results.json").exists():
        raise FileExistsError("Results already exist; inspect and use --record instead of rerunning")

    started = time.perf_counter()
    callback, frame_records, pair_records = api.make_pipeline_measurement_callback(
        api.load_quality_factors())
    print(f"Measuring {len(stems)} frames; voxel={VOXEL_SIZE} m; seed={SEED}", flush=True)
    pipeline_started = time.perf_counter()
    cloud, pred_camera = utils.reconstruct(
        decl["batch_path"], "open3d", frames=stems, voxel_size=VOXEL_SIZE,
        registration_seed=SEED, build_cloud=True, verbose=True,
        pipeline_callback=callback)
    pipeline_seconds = time.perf_counter()-pipeline_started
    if len(pred_camera) != len(stems):
        raise ValueError("Some frames were not reconstructed")
    expected_frame = {(name, i) for i in stems
                      for name in ("RawPointCount", "VoxelizedPointYield")}
    pair_names = ("CoarseRANSACFitness", "CoarseRANSACRMSE", "CoarseRANSACCorrespondences",
                  "ICPInlierFitness", "ICPInlierRMSE", "ICPInlierCorrespondences")
    expected_pair = {(name, i, j) for i, j in zip(stems, stems[1:]) for name in pair_names}
    if set(frame_records) != expected_frame or set(pair_records) != expected_pair:
        raise ValueError("Incomplete pipeline evidence")
    (out / "pipeline_measurements.json").write_text(json.dumps({
        "frame": list(frame_records.items()), "pair": list(pair_records.items())}, indent=2)+"\n")

    # Evaluation only: the first original frame remains the common reference.
    gt_raw = np.load(Path(decl["batch_path"]) / "GT_pose.npy")
    rotation0 = Rotation.from_quat(gt_raw[0, [4, 5, 6, 3]]).as_matrix()
    gt = (gt_raw[:, :3]-gt_raw[0, :3]) @ rotation0
    pred = pred_camera @ utils.CAM_TO_GT_AXES
    errors = np.linalg.norm(pred-gt, axis=1)
    score = utils.visualize_and_evaluate(
        cloud, pred_camera, decl["batch_path"], frames=stems, show=False)
    if not np.isclose(score, errors.mean(), rtol=0, atol=1e-12):
        raise ValueError("Independent score differs from course evaluator")
    baseline = np.load(ROOT / "experiments/phase1_baseline/analysis/trajectory_diagnostic.npz")
    if list(baseline["frames"]) != stems:
        raise ValueError("Reference and treatment frame sets differ")
    np.savez(out / "trajectory.npz", frames=stems, pred=pred,
             pred_camera=pred_camera, gt=gt, error=errors)

    display = cloud.voxel_down_sample(0.04)  # visualization only, after registration
    xyz = np.asarray(display.points) @ utils.CAM_TO_GT_AXES
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter(xyz[:, 0], xyz[:, 2], c=np.asarray(display.colors), s=0.6,
               linewidths=0, rasterized=True)
    ax.plot(gt[:, 0], gt[:, 2], color="black", lw=2.2, label="GT", zorder=4)
    ax.plot(pred[:, 0], pred[:, 2], color="red", lw=1.2, label="Estimated", zorder=5)
    ax.set_aspect("equal"); ax.margins(0.04); ax.legend()
    ax.set_xlabel("First-camera X (m)"); ax.set_ylabel("First-camera Z (m)")
    ax.set_title(f"Full 191-frame capture | voxel=0.03 m | Mean L2 {score*100:.2f} cm")
    fig.tight_layout(); fig.savefig(workspace / "reconstruction_voxel_003.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].plot(gt[:, 0], gt[:, 2], color="black", lw=2, label="GT")
    for positions, color, label in [(baseline["pred"], "steelblue", "voxel=0.05 m"),
                                     (pred, "red", "voxel=0.03 m")]:
        axes[0].plot(positions[:, 0], positions[:, 2], color=color, lw=1, label=label)
    axes[0].set_aspect("equal"); axes[0].set_xlabel("First-camera X (m)")
    axes[0].set_ylabel("First-camera Z (m)"); axes[0].legend()
    axes[1].plot(stems, baseline["error"]*100, color="steelblue", label="voxel=0.05 m")
    axes[1].plot(stems, errors*100, color="red", label="voxel=0.03 m")
    axes[1].set_xlabel("Original frame index"); axes[1].set_ylabel("Position L2 error (cm)")
    axes[1].legend()
    for ax in axes: ax.grid(alpha=0.2)
    fig.suptitle("Full-batch voxel-size comparison | same 191 frames, Open3D, seed=0")
    fig.tight_layout(); fig.savefig(out / "voxel_comparison.png", dpi=160); plt.close(fig)

    ref = api.read_experiment(str(ROOT / "experiments/phase1_baseline/phase1_baseline.ttl"))
    h = api.HW1; graph = ref["graph"]
    ref_yield = [float(graph.value(node, h.value))
                 for node in graph.subjects(h.hasDefinition, h.VoxelizedPointYield)]
    new_yield = [v["value"] for k, v in frame_records.items() if k[0]=="VoxelizedPointYield"]
    result = {
        "frames": stems, "frame_count": len(stems), "retained_fraction": 1.0,
        "voxel_size_m": VOXEL_SIZE, "seed": SEED, "icp_backend": "open3d",
        "normal_radius_m": VOXEL_SIZE*2, "fpfh_radius_m": VOXEL_SIZE*5,
        "ransac_and_icp_distance_gate_m": VOXEL_SIZE*1.5,
        "mean_l2_m": float(score), "reference_mean_l2_m": float(baseline["error"].mean()),
        "max_l2_m": float(errors.max()), "max_error_frame": int(stems[int(errors.argmax())]),
        "reference_mean_voxelized_points": float(np.mean(ref_yield)),
        "mean_voxelized_points": float(np.mean(new_yield)),
        "reconstruction_seconds": pipeline_seconds, "total_seconds": time.perf_counter()-started,
        "timing_scope": "reconstruction, fresh measurements, evaluation, NPZ and plots; excludes declaration, sealing and dashboard",
        "reference_runtime_seconds": None, "declaration_sha256": declaration_sha,
        "frame_factor_occurrences": len(frame_records), "pair_factor_occurrences": len(pair_records),
    }
    (out / "results.json").write_text(json.dumps(result, indent=2)+"\n")
    with (out / "voxel_comparison.csv").open("w", newline="") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["run", "frames", "voxel_size_m", "mean_l2_m", "mean_voxelized_points",
                    "normal_radius_m", "fpfh_radius_m", "matching_gate_m", "reconstruction_seconds", "total_seconds"])
        w.writerow(["reference", 191, 0.05, result["reference_mean_l2_m"],
                    np.mean(ref_yield), 0.10, 0.25, 0.075, "not recorded", "not recorded"])
        w.writerow(["voxel_003", len(stems), VOXEL_SIZE, score, np.mean(new_yield),
                    VOXEL_SIZE*2, VOXEL_SIZE*5, VOXEL_SIZE*1.5, pipeline_seconds, result["total_seconds"]])
    print(json.dumps({k:v for k,v in result.items() if k!="frames"}, indent=2), flush=True)
    print("Inspection outputs saved. Use --record to seal the fresh measurements and full-batch run.")


if __name__ == "__main__":
    main()
