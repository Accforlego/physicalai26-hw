"""Compare the completed SOR run with the original Phase 1 baseline."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import api


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = Path(__file__).resolve().parent
    workspace = out.parent
    original = ROOT / "eval/first_floor"
    derived = ROOT / "eval/first_floor_sor_nb20_std3"
    baseline = np.load(ROOT / "experiments/phase1_baseline/analysis/trajectory_diagnostic.npz")
    treatment = np.load(out / "trajectory.npz")
    result = json.loads((out / "results.json").read_text())
    prep = json.loads((out / "preprocessing.json").read_text())
    assert np.array_equal(baseline["frames"], treatment["frames"])
    assert np.allclose(baseline["gt"], treatment["gt"], rtol=0, atol=1e-12)
    assert np.allclose(np.linalg.norm(treatment["pred"]-treatment["gt"], axis=1), treatment["error"])
    assert np.isclose(treatment["error"].mean(), result["mean_l2_m"], rtol=0, atol=1e-12)
    for name in ("source_hashes.json", "baseline_hashes.json"):
        for path, digest in json.loads((out / name).read_text()).items():
            assert sha(ROOT / path) == digest, path
    for name in ("GT_pose.npy", "intrinsics.json"):
        assert sha(original / name) == sha(derived / name)
    records = json.loads((out / "pipeline_measurements.json").read_text())
    frame_factors = {tuple(key): value["value"] for key, value in records["frame"]}
    for row in prep["frames"]:
        name = f'{row["frame"]}.png'
        before = cv2.imread(str(original / "depth" / name), -1)
        after = cv2.imread(str(derived / "depth" / name), -1)
        assert sha(original / "rgb" / name) == sha(derived / "rgb" / name)
        assert sha(derived / "depth" / name) == row["derived_depth_sha256"]
        assert np.all((after == 0) | (after == before))
        assert np.count_nonzero(before)-np.count_nonzero(after) == row["removed_points"]
        assert np.count_nonzero(after) == frame_factors["RawPointCount", row["frame"]]
    assert len(records["frame"]) == 382 and len(records["pair"]) == 1140
    exp = api.read_experiment(str(workspace / "phase1_depth_sor.ttl"))
    assert exp is not None
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for key, color, label in (("gt", "black", "GT"), ("pred", "steelblue", "Original baseline")):
        axes[0].plot(baseline[key][:, 0], baseline[key][:, 2], color=color, label=label)
    axes[0].plot(treatment["pred"][:, 0], treatment["pred"][:, 2], color="red", label="Depth SOR")
    axes[0].set_aspect("equal"); axes[0].set_xlabel("First-camera X (m)"); axes[0].set_ylabel("First-camera Z (m)")
    axes[1].plot(baseline["frames"], baseline["error"]*100, color="steelblue", label="Original baseline")
    axes[1].plot(treatment["frames"], treatment["error"]*100, color="red", label="Depth SOR")
    axes[1].set_xlabel("Original frame"); axes[1].set_ylabel("Position L2 error (cm)")
    for ax in axes:
        ax.grid(alpha=.2); ax.legend()
    fig.suptitle("Phase 1 | All 191 frames, voxel=0.05 m, Open3D, seed=0")
    fig.tight_layout(); fig.savefig(out / "intervention_comparison.png", dpi=160); plt.close(fig)
    summary = {"frame_count_each": 191, "retained_frame_fraction": 1.0,
               "baseline_mean_l2_m": float(baseline["error"].mean()),
               "sor_mean_l2_m": result["mean_l2_m"],
               "baseline_max_l2_m": float(baseline["error"].max()),
               "sor_max_l2_m": result["max_l2_m"],
               "mean_removed_point_fraction": prep["mean_removed_fraction"],
               "preprocessing_seconds": prep["preprocessing_seconds"],
               "sor_reconstruction_seconds": result["reconstruction_seconds"],
               "sor_total_including_preprocessing_seconds": prep["preprocessing_seconds"]+result["total_seconds"],
               "baseline_runtime_seconds": None,
               "all_original_capture_and_baseline_hashes_unchanged": True,
               "all_rgb_gt_intrinsics_identical": True,
               "all_retained_positive_depth_values_unchanged": True,
               "all_derived_raw_counts_match_new_pipeline_factors": True,
               "factor_occurrences": 1522,
               "independent_score_verified": True}
    (out / "comparison_and_integrity.json").write_text(json.dumps(summary, indent=2)+"\n")
    with (out / "intervention_comparison.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["run", "frames", "retained_fraction", "mean_l2_m", "voxel_m", "seed", "preprocessing_seconds", "reconstruction_seconds", "total_seconds"])
        writer.writerow(["original_baseline", 191, 1, summary["baseline_mean_l2_m"], .05, 0, 0, "not recorded", "not recorded"])
        writer.writerow(["depth_sor", 191, 1, result["mean_l2_m"], .05, 0, prep["preprocessing_seconds"], result["reconstruction_seconds"], summary["sor_total_including_preprocessing_seconds"]])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
