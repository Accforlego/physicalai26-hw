"""Run Phase 1 open3d full-batch baseline with 0.05 m/Open3D/seed 0, then --record."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    out = workspace / "analysis"
    ttl = workspace / "phase1_open3d_reference.ttl"
    if api.is_assessed(str(ttl)):
        raise FileExistsError("Experiment already sealed; do not overwrite it")
    decl = api.read_declaration(str(ttl))
    frames = api._pair_frames(decl["batch_path"])
    stems = [int(stem) for stem, _, _ in frames]
    digest = hashlib.sha256(ttl.read_bytes()).hexdigest()
    if args.record:
        result = json.loads((out / "results.json").read_text())
        if result["declaration_sha256"] != digest or stems != result["frames"]:
            raise ValueError("Declaration/frame set differs from measured result")
        records = json.loads((out / "pipeline_measurements.json").read_text())
        api.seal_experiment(str(ttl), decl, frames,
                            pipeline_frame_records={tuple(k):v for k,v in records["frame"]},
                            pipeline_pair_records={tuple(k):v for k,v in records["pair"]})
        api.write_run(str(ttl), "baseline", {"mapMeanL2":result["mean_l2_m"]},
                      frame_count=len(stems))
        api.read_experiment(str(ttl))
        print("Phase 1 open3d baseline sealed with fresh factor measurements.")
        return
    if (out / "results.json").exists():
        raise FileExistsError("Results already exist; inspect and use --record")
    started = time.perf_counter()
    measure, frame_records, pair_records = api.make_pipeline_measurement_callback(api.load_quality_factors())
    transforms = [np.eye(4)]
    diagnostics = []

    def callback(kind, values):
        measure(kind, values)
        if kind=="pair" and values["stem"]%10==0:
            print(f"Pair -> {values['stem']}: ICP fitness={values['icp_fitness']:.4f}, RMSE={values['icp_rmse']:.4f} m",flush=True)

    def diagnostic(values):
        transforms.append(transforms[-1] @ values["icp_transformation"])
        diagnostics.append({k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in values.items()})

    print(f"Reconstructing {len(stems)} frames: voxel=0.05 m, Open3D, seed=0",flush=True)
    pipeline_started = time.perf_counter()
    cloud, pred_camera = utils.reconstruct(
        decl["batch_path"], "open3d", frames=stems, voxel_size=0.05,
        registration_seed=0, build_cloud=True, verbose=True,
        pipeline_callback=callback, diagnostics_callback=diagnostic)
    pipeline_seconds = time.perf_counter()-pipeline_started
    if len(pred_camera)!=len(stems) or len(frame_records)!=2*len(stems) or len(pair_records)!=6*(len(stems)-1):
        raise ValueError("Incomplete trajectory or pipeline factors")
    transforms = np.asarray(transforms)
    if not np.allclose(transforms[:,:3,3],pred_camera,rtol=0,atol=1e-12):
        raise ValueError("Saved diagnostic transforms disagree with reconstructed positions")
    (out / "pipeline_measurements.json").write_text(json.dumps({"frame":list(frame_records.items()),"pair":list(pair_records.items())},indent=2)+"\n")
    (out / "pair_diagnostics.json").write_text(json.dumps(diagnostics,indent=2)+"\n")

    # Load GT only after reconstruction. No pose fitting or frame exclusion.
    raw = np.load(Path(decl["batch_path"])/"GT_pose.npy")
    rotation = Rotation.from_quat(raw[0,[4,5,6,3]]).as_matrix()
    gt = (raw[:,:3]-raw[0,:3]) @ rotation
    pred = pred_camera @ utils.CAM_TO_GT_AXES
    errors = np.linalg.norm(pred-gt,axis=1)
    score = utils.visualize_and_evaluate(cloud,pred_camera,decl["batch_path"],frames=stems,show=False)
    if not np.isclose(score,errors.mean(),rtol=0,atol=1e-12):
        raise ValueError("Independent scoring differs from course evaluator")
    np.savez(out/"trajectory.npz",frames=stems,pred=pred,pred_camera=pred_camera,
             gt=gt,error=errors,estimated_transforms=transforms)

    display = cloud.voxel_down_sample(0.04)  # rendering only
    xyz = np.asarray(display.points) @ utils.CAM_TO_GT_AXES
    fig,ax = plt.subplots(figsize=(10,10))
    ax.scatter(xyz[:,0],xyz[:,2],c=np.asarray(display.colors),s=0.6,linewidths=0,rasterized=True)
    ax.plot(gt[:,0],gt[:,2],color="black",lw=2.2,label="GT",zorder=4)
    ax.plot(pred[:,0],pred[:,2],color="red",lw=1.2,label="Estimated",zorder=5)
    ax.set_aspect("equal");ax.margins(.04);ax.legend();ax.set_xlabel("First-camera X (m)");ax.set_ylabel("First-camera Z (m)")
    ax.set_title(f"Phase 1 open3d baseline | {len(stems)} frames | voxel=0.05 m | Mean L2={score:.4f} m")
    fig.tight_layout();fig.savefig(workspace/"reconstruction_baseline.png",dpi=180);plt.close(fig)

    fig,axes = plt.subplots(1,2,figsize=(14,6))
    axes[0].plot(gt[:,0],gt[:,2],color="black",lw=2,label="GT")
    axes[0].plot(pred[:,0],pred[:,2],color="red",lw=1,label="Estimated")
    axes[0].set_aspect("equal");axes[0].set_xlabel("First-camera X (m)");axes[0].set_ylabel("First-camera Z (m)");axes[0].legend()
    axes[1].plot(stems,errors,color="purple");axes[1].set_xlabel("Frame index");axes[1].set_ylabel("Position L2 error (m)")
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle("Phase 1 open3d full-batch baseline | Open3D, voxel=0.05 m, seed=0")
    fig.tight_layout();fig.savefig(out/"trajectory_diagnostic.png",dpi=160);plt.close(fig)
    result={"frames":stems,"frame_count":len(stems),"retained_fraction":1.0,
            "voxel_size_m":.05,"seed":0,"icp_backend":"open3d",
            "normal_radius_m":.10,"fpfh_radius_m":.25,"matching_gate_m":.075,
            "mean_l2_m":float(score),"max_l2_m":float(errors.max()),
            "max_error_frame":int(stems[int(errors.argmax())]),
            "reconstruction_seconds":pipeline_seconds,"total_seconds":time.perf_counter()-started,
            "timing_scope":"reconstruction, measurements, diagnostics, evaluation and PNG/NPZ outputs; excludes declaration, sealing, dashboard",
            "frame_factor_occurrences":len(frame_records),"pair_factor_occurrences":len(pair_records),
            "declaration_sha256":digest,"capture_dir":decl["batch_path"]}
    (out/"results.json").write_text(json.dumps(result,indent=2)+"\n")
    with (out/"baseline_results.csv").open("w",newline="") as handle:
        writer=csv.writer(handle,lineterminator="\n")
        keys=["frame_count","retained_fraction","voxel_size_m","seed","mean_l2_m","max_l2_m","reconstruction_seconds","total_seconds"]
        writer.writerow(keys);writer.writerow([result[k] for k in keys])
    print(json.dumps({k:v for k,v in result.items() if k!="frames"},indent=2),flush=True)
    print("Inspect results, then use --record to seal the measured full-batch baseline.")


if __name__=="__main__":
    main()
