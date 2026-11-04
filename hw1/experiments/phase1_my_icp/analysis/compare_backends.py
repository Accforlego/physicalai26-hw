"""Compare the measured custom ICP run with a fresh Open3D reference."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import api


def main():
    out = Path(__file__).resolve().parent
    ref = ROOT / "experiments/phase1_open3d_reference/analysis"
    original = np.load(ROOT / "experiments/phase1_baseline/analysis/trajectory_diagnostic.npz")
    paths = {"my_icp": out, "open3d": ref}
    results = {k: json.loads((p / "results.json").read_text()) for k, p in paths.items()}
    trajectories = {k: np.load(p / "trajectory.npz") for k, p in paths.items()}
    checks = {}
    for backend, path in paths.items():
        trajectory = trajectories[backend]
        result = results[backend]
        assert result["icp_backend"] == backend
        assert np.array_equal(trajectory["frames"], original["frames"])
        assert np.allclose(trajectory["gt"], original["gt"], rtol=0, atol=1e-12)
        error = np.linalg.norm(trajectory["pred"]-trajectory["gt"], axis=1)
        assert np.allclose(error, trajectory["error"], rtol=0, atol=1e-12)
        assert np.isclose(error.mean(), result["mean_l2_m"], rtol=0, atol=1e-12)
        transforms = trajectory["estimated_transforms"]
        assert np.allclose(transforms[:, :3, 3], trajectory["pred_camera"], rtol=0, atol=1e-12)
        assert np.isfinite(transforms).all()
        assert np.allclose(np.linalg.det(transforms[:, :3, :3]), 1, atol=1e-8)
        assert np.allclose(transforms[:, :3, :3].transpose(0, 2, 1) @ transforms[:, :3, :3], np.eye(3), atol=1e-8)
        assert result["frame_factor_occurrences"] == 382 and result["pair_factor_occurrences"] == 1140
        assert len(json.loads((path / "pair_diagnostics.json").read_text())) == 190
        for filename, digest in json.loads((path / "source_hashes.json").read_text()).items():
            assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == digest, filename
        exp_name = path.parent.name
        assert api.read_experiment(str(path.parent / f"{exp_name}.ttl")) is not None
        checks[backend] = {"all_191_frames": True, "source_capture_and_original_baseline_unchanged": True,
                           "score_verified": True, "finite_valid_rotations": True,
                           "complete_measured_factors": 1522, "sealed_readback": True}
    for key in ("voxel_size_m", "seed", "normal_radius_m", "fpfh_radius_m", "matching_gate_m", "capture_dir", "frames"):
        assert results["my_icp"][key] == results["open3d"][key], key
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    gt = original["gt"]
    axes[0].plot(gt[:, 0], gt[:, 2], color="black", lw=2, label="GT")
    for backend, color in (("open3d", "steelblue"), ("my_icp", "red")):
        t = trajectories[backend]
        axes[0].plot(t["pred"][:, 0], t["pred"][:, 2], color=color, lw=1, label=backend)
        axes[1].plot(t["frames"], t["error"]*100, color=color, label=backend)
    axes[0].set_aspect("equal"); axes[0].set_xlabel("First-camera X (m)"); axes[0].set_ylabel("First-camera Z (m)")
    axes[1].set_xlabel("Frame index"); axes[1].set_ylabel("Position L2 error (cm)")
    for ax in axes:
        ax.grid(alpha=.2); ax.legend()
    fig.suptitle("Phase 1 ICP comparison | full 191 frames, voxel=0.05 m, seed=0")
    fig.tight_layout(); fig.savefig(out / "backend_comparison.png", dpi=160); plt.close(fig)
    with (out / "backend_comparison.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["run", "frame_count", "mean_l2_m", "max_l2_m", "reconstruction_seconds", "total_seconds", "voxel_size_m", "seed"])
        writer.writerow(["original_saved_open3d", 191, original["error"].mean(), original["error"].max(), "not recorded", "not recorded", .05, 0])
        for backend in ("open3d", "my_icp"):
            r = results[backend]
            writer.writerow([backend, r["frame_count"], r["mean_l2_m"], r["max_l2_m"], r["reconstruction_seconds"], r["total_seconds"], r["voxel_size_m"], r["seed"]])
    summary = {"original_saved_open3d_mean_l2_m": float(original["error"].mean()),
               "fresh_open3d_mean_l2_m": results["open3d"]["mean_l2_m"],
               "my_icp_mean_l2_m": results["my_icp"]["mean_l2_m"],
               "custom_to_open3d_reconstruction_time_ratio": results["my_icp"]["reconstruction_seconds"]/results["open3d"]["reconstruction_seconds"],
               "same_data_and_shared_hyperparameters": True, "checks": checks,
               "timing_limitations": "Single runs, OMP_NUM_THREADS=8. End-to-end reconstruction includes unprojection, features, RANSAC, ICP and cloud merge; not isolated ICP timing. Native convergence rules differ (custom max 60, Open3D max 100)."}
    (out / "comparison_and_integrity.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
