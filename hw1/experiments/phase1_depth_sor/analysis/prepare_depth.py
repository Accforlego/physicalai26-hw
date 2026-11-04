"""Make a separate capture with per-frame statistical point-outlier masks.

Run from hw1. The source capture and baseline artifacts are never modified.
No GT positions are inspected; GT is copied verbatim for later evaluation.
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import utils


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = Path(__file__).resolve().parent
    source = ROOT / "eval/first_floor"
    target = ROOT / "eval/first_floor_sor_nb20_std3"
    if target.exists() or (out / "preprocessing.json").exists():
        raise FileExistsError("Derived capture/results already exist; use a new experiment")
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source.rglob("*") if p.is_file()}
    baseline_hashes = {str(p.relative_to(ROOT)): sha(p)
                       for p in (ROOT / "experiments/phase1_baseline").rglob("*") if p.is_file()}
    (out / "source_hashes.json").write_text(json.dumps(source_hashes, indent=2)+"\n")
    (out / "baseline_hashes.json").write_text(json.dumps(baseline_hashes, indent=2)+"\n")
    started = time.perf_counter()
    intr = json.loads((source / "intrinsics.json").read_text())
    (target / "rgb").mkdir(parents=True)
    (target / "depth").mkdir()
    records = []
    for path in sorted((source / "depth").glob("*.png"), key=lambda p: int(p.stem)):
        rgb_path = source / "rgb" / path.name
        depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        rgb = cv2.imread(str(rgb_path))
        assert depth.dtype == np.uint16 and depth.shape == (intr["height"], intr["width"])
        cloud = utils.depth_image_to_point_cloud(rgb, depth, intr["width"], intr["height"], intr["hfov"])
        _, kept = cloud.remove_statistical_outlier(nb_neighbors=20, std_ratio=3.0)
        valid_pixels = np.flatnonzero(depth.ravel() > 0)
        assert len(valid_pixels) == len(cloud.points) and len(kept) > 0
        keep = np.zeros(len(valid_pixels), dtype=bool)
        keep[np.asarray(kept, dtype=int)] = True
        masked = depth.copy()
        masked.ravel()[valid_pixels[~keep]] = 0
        assert np.count_nonzero(masked) == len(kept)
        assert np.array_equal(masked[masked > 0], depth[masked > 0])
        assert cv2.imwrite(str(target / "depth" / path.name), masked)
        shutil.copy2(rgb_path, target / "rgb" / path.name)
        record = {"frame": int(path.stem), "raw_points": len(valid_pixels),
                  "retained_points": len(kept), "removed_points": int((~keep).sum()),
                  "removed_fraction": float((~keep).mean()),
                  "derived_depth_sha256": sha(target / "depth" / path.name)}
        records.append(record)
        if len(records) % 25 == 0:
            print(f"Prepared {len(records)} frames", flush=True)
    for name in ("intrinsics.json", "GT_pose.npy"):
        shutil.copy2(source / name, target / name)
    result = {"source_capture": str(source.relative_to(ROOT)),
              "derived_capture": str(target.relative_to(ROOT)),
              "method": "Open3D per-frame statistical outlier removal before voxelization",
              "nb_neighbors": 20, "std_ratio": 3.0,
              "frame_count": len(records), "frames": records,
              "preprocessing_seconds": time.perf_counter()-started,
              "mean_removed_fraction": float(np.mean([r["removed_fraction"] for r in records])),
              "max_removed_fraction": max(r["removed_fraction"] for r in records),
              "total_raw_points": sum(r["raw_points"] for r in records),
              "total_removed_points": sum(r["removed_points"] for r in records),
              "original_positive_depths_unchanged": True,
              "rgb_gt_intrinsics_copied_verbatim": True}
    (out / "preprocessing.json").write_text(json.dumps(result, indent=2)+"\n")
    (target / "preprocessing.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "frames"}, indent=2))


if __name__ == "__main__":
    main()
