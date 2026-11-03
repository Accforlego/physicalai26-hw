import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import json
import numpy as np
import open3d as o3d
import os
import cv2
from types import SimpleNamespace
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

DEPTH_SCALE  = 1000.0     # uint16 depth PNGs store millimetres
# Image axes (+X right, +Y down, +Z forward) to Habitat's sensor axes
# (+X right, +Y up, +Z backward), used by the scorer.
CAM_TO_GT_AXES = np.diag([1.0, -1.0, -1.0])



def depth_image_to_point_cloud(rgb, depth_m, width, height, hfov):
    """Back-project one RGB-D frame into a colored 3-D point cloud.

    `rgb` is HxWx3 uint8 in BGR order and `depth_m` the same frame's HxW
    depths in metres; `width`/`height`/`hfov` are that capture's own camera
    parameters (read from its `intrinsics.json` by the caller — never
    hardcoded, so one capture is never unprojected through another's
    camera). Geometry is a pinhole with square pixels, image-centre
    principal point, and focal length derived from `width` and `hfov`.

    Returns points in metres in the frame's camera frame (+X right, +Y
    down, +Z forward) with colors as RGB floats in [0, 1]. A pixel yields
    a point iff `depth_m > 0` (zero means no return and is dropped, never
    placed at the origin).
    Points come out in row-major pixel order; an all-invalid frame yields
    an empty cloud. Inputs are not modified.
    """
    rgb = np.asarray(rgb)
    depth = np.asarray(depth_m)
    if depth.shape != (height, width) or rgb.shape != (height, width, 3):
        raise ValueError("RGB and depth shapes must match the capture intrinsics")
    if np.issubdtype(depth.dtype, np.integer):
        depth = depth.astype(np.float64) / DEPTH_SCALE
    else:
        depth = depth.astype(np.float64, copy=False)
    valid = np.isfinite(depth) & (depth > 0)
    v, u = np.indices((height, width))
    z = depth[valid]
    focal = width / (2.0 * np.tan(np.deg2rad(hfov) / 2.0))
    cx, cy = width / 2.0, height / 2.0
    points = np.column_stack(((u[valid] - cx) * z / focal,
                              (v[valid] - cy) * z / focal, z))
    colors = rgb[valid][:, ::-1].astype(np.float64) / 255.0
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    cloud.colors = o3d.utility.Vector3dVector(colors)
    return cloud


def preprocess_point_cloud(pcd, voxel_size):
    """Downsample a cloud and prepare it for feature matching and ICP.

    Voxel-downsamples at `voxel_size`, estimates normals (radius
    `voxel_size * 2`, up to 30 neighbours) for point-to-plane ICP, and
    computes FPFH descriptors (radius `voxel_size * 5`, up to 100
    neighbours) for RANSAC matching. Returns the downsampled cloud and
    its FPFH feature set. Pairwise registration is performed by reconstruct().
    """
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(
        radius=voxel_size * 2, max_nn=30))
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down, o3d.geometry.KDTreeSearchParamHybrid(
            radius=voxel_size * 5, max_nn=100))
    return pcd_down, fpfh


def local_icp_algorithm(source_down, target_down, trans_init, threshold):
    """Refine an initial alignment with point-to-plane ICP.

    Estimates normals on either cloud if missing (radius `threshold * 2`,
    up to 30 neighbours), then runs up to 100 ICP iterations at the single
    correspondence `threshold`. Returns the RegistrationResult; its
    `.transformation` is the refined 4x4.
    """
    for cloud in (source_down, target_down):
        if not cloud.has_normals():
            cloud.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(
                radius=threshold * 2, max_nn=30))
    return o3d.pipelines.registration.registration_icp(
        source_down, target_down, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=100))


def my_local_icp_algorithm(source_down, target_down, trans_init, voxel_size):
    """From-scratch point-to-plane ICP (the optional Bonus Track backend).

    Transform the source, match nearest target points, and solve a linearized
    point-to-plane pose update for up to 60 iterations. The result exposes
    transformation and the registration metrics used by diagnostics.
    """
    transform = np.asarray(trans_init, dtype=np.float64).copy()
    source = np.asarray(source_down.points)
    target = np.asarray(target_down.points)
    if not len(source) or not len(target):
        return SimpleNamespace(transformation=transform, fitness=0.0,
                               inlier_rmse=0.0, correspondence_set=[])
    if not target_down.has_normals():
        target_down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(
            radius=voxel_size * 3, max_nn=30))
    normals = np.asarray(target_down.normals)
    tree = cKDTree(target)
    gate = voxel_size * 1.5
    last_error = np.inf
    for _ in range(60):
        moved = source @ transform[:3, :3].T + transform[:3, 3]
        distances, indices = tree.query(moved)
        valid = (distances < gate) & np.all(np.isfinite(normals[indices]), axis=1)
        if np.count_nonzero(valid) < 10:
            break
        p, q, n = moved[valid], target[indices[valid]], normals[indices[valid]]
        jacobian = np.column_stack((np.cross(p, n), n))
        residual = np.sum(n * (p - q), axis=1)
        step = np.linalg.lstsq(jacobian, -residual, rcond=None)[0]
        delta = np.eye(4)
        delta[:3, :3] = Rotation.from_rotvec(step[:3]).as_matrix()
        delta[:3, 3] = step[3:]
        transform = delta @ transform
        error = np.mean(np.abs(residual))
        if abs(last_error - error) < 1e-6 or np.linalg.norm(step) < 1e-6:
            break
        last_error = error
    moved = source @ transform[:3, :3].T + transform[:3, 3]
    distances, indices = tree.query(moved)
    valid = distances < gate
    correspondence_set = np.column_stack((np.flatnonzero(valid), indices[valid]))
    return SimpleNamespace(
        transformation=transform, fitness=float(np.mean(valid)),
        inlier_rmse=float(np.sqrt(np.mean(distances[valid] ** 2))) if np.any(valid) else 0.0,
        correspondence_set=correspondence_set)


def remove_ceiling_points(point_cloud, margin=1.0):
    """Return the map without the ceiling band, in frame-0 camera coordinates.

    Camera-frame +Y points down, so ceiling returns occupy the map's minimum
    Y values. Drop the same 1 m band that the viewer historically hid. This
    operates only on the merged output map; registration and trajectory scores
    continue to use the original per-frame depth clouds.
    """
    points = np.asarray(point_cloud.points)
    if len(points) == 0:
        return point_cloud
    keep = points[:, 1] > (points[:, 1].min() + float(margin))
    return point_cloud.select_by_index(np.flatnonzero(keep))


# ══════════════════════════════════════════════════════════════════════════════
#  Reconstruction (headless) + metric
# ══════════════════════════════════════════════════════════════════════════════
def reconstruct(data_root, version="open3d", voxel_size=0.05, verbose=True,
                build_cloud=True, frames=None,
                down_voxel=None, registration_seed=0,
                pipeline_callback=None,
                diagnostics_callback=None):
    """Reconstruct a camera trajectory and optionally merge its point clouds.

    Steps for each selected frame: build and preprocess an RGB-D cloud; register
    it to the previous frame with RANSAC initialization and ICP refinement; chain
    the transform and, when requested, add the cloud to the map.

    Frame selection:
      frames=None -> whole batch: every stem present under BOTH rgb/ and
        depth/, ascending numeric order.
      frames=[...] -> only those integer stems, IN THE GIVEN ORDER;
        "consecutive" means consecutive in the subset.

    Returns (global_pcd, pred_cam_pos):
      global_pcd   : every frame's cloud in the FRAME-0 CAMERA frame
                     (+X right, +Y down, +Z forward). Empty when
                     build_cloud=False (trajectory identical either way).
      pred_cam_pos : (N,3) float64 camera centres, frame-0 anchored.
                     GT stays on disk; visualize_and_evaluate loads and
                     subsets it by the same stems when scoring.
    """
    with open(os.path.join(data_root, "intrinsics.json"), encoding="utf-8") as handle:
        intrinsics = json.load(handle)
    width, height = int(intrinsics["width"]), int(intrinsics["height"])
    hfov = float(intrinsics["hfov"])
    rgb_dir, depth_dir = (os.path.join(data_root, name) for name in ("rgb", "depth"))
    def stems(directory):
        return {int(name[:-4]) for name in os.listdir(directory)
                if name.lower().endswith(".png") and name[:-4].isdigit()}
    available = stems(rgb_dir) & stems(depth_dir)
    selected = sorted(available) if frames is None else [int(stem) for stem in frames
                                                         if int(stem) in available]
    pairs = [(os.path.join(rgb_dir, f"{stem}.png"),
              os.path.join(depth_dir, f"{stem}.png")) for stem in selected]
    o3d.utility.random.seed(registration_seed)

    T_global = np.eye(4)          # frame i -> frame-0 camera frame
    pred_cam_pos = []
    global_pcd = o3d.geometry.PointCloud()
    prev_down = prev_fpfh = None
    prev_depth_path = None
    prev_stem = None
    prev_pair_index = None
    icp_thr = voxel_size * 1.5

    for i, (rgb_path, depth_path) in enumerate(pairs):
        stem = selected[i]
        rgb = cv2.imread(rgb_path, cv2.IMREAD_COLOR)
        depth = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
        depth_m = None if depth is None else depth.astype(np.float64) / DEPTH_SCALE
        if (rgb is not None and depth_m is not None and
                (rgb.shape[:2] != (height, width) or depth_m.shape != (height, width))):
            rgb = None
        if rgb is None or depth_m is None:
            if verbose:
                print(f"  Warning: could not load frame {i}, skipping.")
            continue

        pcd = depth_image_to_point_cloud(rgb, depth_m, width, height, hfov)
        cur_down, cur_fpfh = preprocess_point_cloud(pcd, voxel_size)
        if pipeline_callback is not None:
            pipeline_callback("frame", {
                "stem": stem,
                "raw_point_count": len(pcd.points),
                "point_yield": len(cur_down.points),
            })

        if prev_down is not None:
            coarse_result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
                cur_down, prev_down, cur_fpfh, prev_fpfh, True,
                voxel_size * 1.5,
                o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
                3, [o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
                    o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                        voxel_size * 1.5)],
                o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999))
            trans_init = coarse_result.transformation
            if version == 'open3d':
                result_icp = local_icp_algorithm(
                    cur_down, prev_down, trans_init, icp_thr)
            else:   # my_icp
                result_icp = my_local_icp_algorithm(
                    cur_down, prev_down, trans_init, voxel_size)
            T_global = T_global @ result_icp.transformation
            if pipeline_callback is not None and prev_pair_index == i - 1:
                pipeline_callback("pair", {
                    "prev_stem": prev_stem,
                    "stem": stem,
                    "coarse_fitness": float(coarse_result.fitness),
                    "coarse_rmse": float(coarse_result.inlier_rmse),
                    "coarse_correspondences": len(coarse_result.correspondence_set),
                    "icp_fitness": float(getattr(result_icp, "fitness", float("nan"))),
                    "icp_rmse": float(getattr(result_icp, "inlier_rmse", float("nan"))),
                    "icp_correspondences": len(getattr(result_icp, "correspondence_set", [])),
                })
            if diagnostics_callback is not None and prev_pair_index == i - 1:
                diagnostics_callback({
                    "frame_index": i,
                    "prev_stem": prev_stem,
                    "stem": stem,
                    "raw_point_count": len(pcd.points),
                    "point_yield": len(cur_down.points),
                    "coarse_fitness": float(coarse_result.fitness),
                    "coarse_rmse": float(coarse_result.inlier_rmse),
                    "coarse_correspondences": len(coarse_result.correspondence_set),
                    "icp_fitness": float(result_icp.fitness),
                    "icp_rmse": float(result_icp.inlier_rmse),
                    "icp_correspondences": len(getattr(result_icp, "correspondence_set", [])),
                    "trans_init": trans_init,
                    "icp_transformation": result_icp.transformation,
                })

        pred_cam_pos.append(T_global[:3, 3].copy())

        if build_cloud:
            map_frame = pcd.voxel_down_sample(down_voxel) if down_voxel else pcd
            map_frame.transform(T_global)
            global_pcd += map_frame

        prev_down, prev_fpfh = cur_down, cur_fpfh
        prev_depth_path = depth_path
        prev_stem = stem
        prev_pair_index = i

        if verbose and (i % 25 == 0 or i == len(pairs) - 1):
            print(f"  frame {i:>4d}/{len(pairs)-1}")

    if not pred_cam_pos:
        return o3d.geometry.PointCloud(), np.zeros((0, 3))
    if build_cloud:
        global_pcd = remove_ceiling_points(global_pcd)
    return global_pcd, np.array(pred_cam_pos, dtype=np.float64)


# ══════════════════════════════════════════════════════════════════════════════
#  Evaluation + visualisation (used by the thin reconstruct.py CLI)
# ══════════════════════════════════════════════════════════════════════════════
def visualize_and_evaluate(reconstructed_pcd, predicted_cam_poses, data_root,
                           frames=None, title="reconstruction", show=True,
                           save_path=None):
    """Score the trajectory and visualise map + trajectories.

    GT is loaded here from data_root/GT_pose.npy as (M,7)
    [x,y,z,qw,qx,qy,qz], or None when absent. GT rows are in capture order
    while image stems are identifiers, so when `frames` is given each stem
    is mapped to its ordinal in the sorted common RGB/depth frame list
    before indexing (stems absent from the capture or beyond GT are skipped,
    requested order preserved) — the score stays meaningful on subsets.

    1. Mean L2 over camera centres: reconcile frames first (pred is frame-0
       camera on image axes → flip Y and Z; GT world poses → R0^T (t_i - t_0)
       via pose 0), then mean over i of ||pred[i] - gt[i]||_2 with
       L2 = sqrt(dx^2 + dy^2 + dz^2). No scale/rotation/offset fitting TO the
       GT. inf when either side is missing/empty. Prints it and returns it.
    2. Estimated trajectory LineSet (red), GT trajectory LineSet (black).
    3. Open3D window with the ceiling-cropped map plus both trajectories
       (skipped when show=False, e.g. headless scoring). Ceiling points have
       already been removed from the merged map by `reconstruct`.
    """
    pred = (np.empty((0, 3)) if predicted_cam_poses is None else
            np.asarray(predicted_cam_poses, dtype=np.float64).reshape(-1, 3))
    pred_disp = pred @ CAM_TO_GT_AXES
    gt_disp = np.empty((0, 3))
    gt_path = os.path.join(data_root, "GT_pose.npy") if data_root else None
    if gt_path and os.path.isfile(gt_path):
        gt = np.load(gt_path)
        if frames is not None:
            rgb_dir = os.path.join(data_root, "rgb")
            depth_dir = os.path.join(data_root, "depth")
            if os.path.isdir(rgb_dir) and os.path.isdir(depth_dir):
                def stems(directory):
                    return {int(name[:-4]) for name in os.listdir(directory)
                            if name.lower().endswith(".png") and name[:-4].isdigit()}
                ordered = sorted(stems(rgb_dir) & stems(depth_dir))
                rows = {stem: i for i, stem in enumerate(ordered)}
                gt = gt[[rows[int(stem)] for stem in frames
                         if int(stem) in rows and rows[int(stem)] < len(gt)]]
            else:
                gt = gt[:len(frames)]
        if len(gt):
            qw, qx, qy, qz = gt[0, 3:7]
            R0 = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
            gt_disp = (gt[:, :3] - gt[0, :3]) @ R0
    n = min(len(pred_disp), len(gt_disp))
    mean_l2_error = (float(np.mean(np.linalg.norm(pred_disp[:n] - gt_disp[:n], axis=1)))
                     if n else float("inf"))
    print(f"Mean L2 distance: {mean_l2_error:.6f} meters  (over {n} frames, "
          f"{0 if predicted_cam_poses is None else len(predicted_cam_poses)} "
          f"reconstructed)")
    if save_path is not None:
        save_reconstruction_image(
            reconstructed_pcd, predicted_cam_poses, data_root,
            save_path, frames=frames, title=title)
    if not show:
        return mean_l2_error
    geoms = []
    if reconstructed_pcd is not None and len(reconstructed_pcd.points):
        map_display = o3d.geometry.PointCloud(reconstructed_pcd)
        axes = np.eye(4)
        axes[:3, :3] = CAM_TO_GT_AXES
        map_display.transform(axes)
        geoms.append(map_display)
    for trajectory, color in ((pred_disp, [1.0, 0.0, 0.0]),
                              (gt_disp, [0.0, 0.0, 0.0])):
        if len(trajectory) > 1:
            lines = o3d.geometry.LineSet()
            lines.points = o3d.utility.Vector3dVector(trajectory)
            edges = [[i, i + 1] for i in range(len(trajectory) - 1)]
            lines.lines = o3d.utility.Vector2iVector(edges)
            lines.colors = o3d.utility.Vector3dVector([color] * len(edges))
            geoms.append(lines)
    if not geoms:
        return mean_l2_error
    print(f"[visualize] opening visualiser for {title} …  (press Q to close)")
    o3d.visualization.draw_geometries(
        geoms, window_name=f'HW1 Reconstruction - {title}',
        zoom=0.5, front=[0, -1, 0], lookat=[0, 0, 0], up=[0, 0, 1])
    return mean_l2_error

def save_reconstruction_image(reconstructed_pcd, predicted_cam_poses, data_root,
                              save_path, frames=None, title="reconstruction"):
    """Render reconstructed point cloud and camera trajectories to a PNG file."""
    if save_path is None:
        return None
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    gt_poses = None
    if data_root is not None:
        gt_path = os.path.join(data_root, 'GT_pose.npy')
        if os.path.exists(gt_path):
            gt = np.load(gt_path)
            if frames is None:
                gt_poses = gt
            else:
                rgb_dir = os.path.join(data_root, 'rgb')
                if os.path.exists(rgb_dir):
                    ordered_stems = sorted(
                        int(os.path.splitext(f)[0])
                        for f in os.listdir(rgb_dir)
                        if f.endswith('.png'))
                    rows = [ordered_stems.index(int(stem)) for stem in frames
                            if int(stem) in ordered_stems
                            and ordered_stems.index(int(stem)) < len(gt)]
                    gt_poses = gt[rows]
                else:
                    gt_poses = gt[:len(frames)]

    pred_disp = None
    gt_disp = None
    if predicted_cam_poses is not None and len(predicted_cam_poses) > 0:
        pred_disp = np.asarray(predicted_cam_poses, dtype=np.float64) @ CAM_TO_GT_AXES
    if gt_poses is not None and len(gt_poses) > 0:
        gt = np.asarray(gt_poses, dtype=np.float64)
        t = gt[:, :3]
        qw, qx, qy, qz = gt[0, 3:7]
        R0 = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
        gt_disp = (t - t[0]) @ R0

    geoms = []
    if reconstructed_pcd is not None and len(reconstructed_pcd.points) > 0:
        scene_no_ceil = o3d.geometry.PointCloud()
        scene_no_ceil.points = o3d.utility.Vector3dVector(np.asarray(reconstructed_pcd.points).copy())
        if reconstructed_pcd.has_colors():
            scene_no_ceil.colors = o3d.utility.Vector3dVector(
                np.asarray(reconstructed_pcd.colors).copy())
        to_gt_axes = np.eye(4)
        to_gt_axes[:3, :3] = CAM_TO_GT_AXES
        scene_no_ceil.transform(to_gt_axes)
        geoms.append(scene_no_ceil)

    if pred_disp is not None and gt_disp is not None:
        n_min = min(len(pred_disp), len(gt_disp))
        if n_min > 1:
            for traj, color in ((pred_disp[:n_min], [1.0, 0.0, 0.0]),
                                (gt_disp[:n_min], [0.0, 0.0, 0.0])):
                edges = [[i, i + 1] for i in range(len(traj) - 1)]
                lineset = o3d.geometry.LineSet()
                lineset.points = o3d.utility.Vector3dVector(np.asarray(traj))
                lineset.lines = o3d.utility.Vector2iVector(edges)
                lineset.colors = o3d.utility.Vector3dVector([color] * len(edges))
                geoms.append(lineset)
    elif pred_disp is not None and len(pred_disp) > 1:
        edges = [[i, i + 1] for i in range(len(pred_disp) - 1)]
        lineset = o3d.geometry.LineSet()
        lineset.points = o3d.utility.Vector3dVector(np.asarray(pred_disp))
        lineset.lines = o3d.utility.Vector2iVector(edges)
        lineset.colors = o3d.utility.Vector3dVector([[1.0, 0.0, 0.0]] * len(edges))
        geoms.append(lineset)

    if not os.environ.get("DISPLAY"):
        if os.path.exists("/tmp/.X11-unix/X1"):
            os.environ["DISPLAY"] = ":1"
        elif os.path.exists("/tmp/.X11-unix/X0"):
            os.environ["DISPLAY"] = ":0"

    rendered = False
    if geoms and os.environ.get("DISPLAY"):
        try:
            vis = o3d.visualization.Visualizer()
            if vis.create_window(visible=False, width=1920, height=1080):
                for g in geoms:
                    vis.add_geometry(g)
                opt = vis.get_render_option()
                if opt is not None:
                    opt.background_color = np.asarray([1.0, 1.0, 1.0])
                    if hasattr(opt, "line_width"):
                        opt.line_width = 3.0
                ctr = vis.get_view_control()
                if ctr is not None:
                    ctr.set_zoom(0.5)
                    ctr.set_front([0, -1, 0])
                    ctr.set_lookat([0, 0, 0])
                    ctr.set_up([0, 0, 1])
                vis.poll_events()
                vis.update_renderer()
                vis.capture_screen_image(save_path, do_render=True)
                vis.destroy_window()
                rendered = os.path.isfile(save_path) and os.path.getsize(save_path) > 0
        except Exception:
            rendered = False

    if not rendered:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection="3d")
            if reconstructed_pcd is not None and len(reconstructed_pcd.points) > 0:
                pts = np.asarray(reconstructed_pcd.points)
                if len(pts) > 5000:
                    pts = pts[::len(pts) // 5000]
                pts_gt = pts @ CAM_TO_GT_AXES
                ax.scatter(pts_gt[:, 0], pts_gt[:, 1], pts_gt[:, 2], s=0.5, c="gray", alpha=0.3)
            if pred_disp is not None and len(pred_disp) > 0:
                ax.plot(pred_disp[:, 0], pred_disp[:, 1], pred_disp[:, 2], "r-", label="Predicted")
            if gt_disp is not None and len(gt_disp) > 0:
                ax.plot(gt_disp[:, 0], gt_disp[:, 1], gt_disp[:, 2], "k-", label="Ground Truth")
            ax.set_title(title)
            ax.legend()
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            rendered = os.path.isfile(save_path) and os.path.getsize(save_path) > 0
        except Exception as exc:
            print(f"[reconstruct] warning: failed to save reconstruction image {save_path}: {exc}")
    return save_path if rendered else None
