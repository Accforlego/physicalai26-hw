# HW1: 3D Scene Reconstruction
Student ID: 115062519 | 4 November 2026

## 3D Scene Reconstruction

Reconstruct apartment_0 from RGB-D, inspect pipeline factors, and evaluate interventions. Phase 1 uses 191 provided frames; Phase 2 uses 351 manually captured frames. The main finding is that removing observations or points does not reliably improve alignment. Historical baselines achieve Mean L2 of 0.0588 m and 0.2407 m; reruns reveal sensitivity to execution conditions.

1. Pipeline and evaluation

Read each capture's intrinsics.json; convert uint16 depth from millimeters to meters and discard invalid depth. Implement pinhole unprojection directly, without Open3D's projection helper: f = W/[2 tan(HFOV/2)], c = (W/2,H/2), X = (u-cx)z/f, Y = (v-cy)z/f, Z = z. Downsample, estimate normals, compute FPFH, initialize current-to-previous alignment with RANSAC, and refine with point-to-plane ICP [2,3]. Chain transforms and merge clouds; no loop closure is used.

| Shared setting | Value |
| --- | --- |
| Camera / voxel / normal / FPFH | 512 x 512, HFOV 90 degrees / 0.05 / 0.10 / 0.25 m |
| Normal / FPFH neighbors | max_nn = 30 / 100 |
| RANSAC | Mutual matching; 3-point samples; edge ratio 0.9; 0.075 m gate; max 100,000; confidence 0.999 |
| ICP / seed | 0.075 m gate; max 100 iterations (Open3D); seed 0 |

Mean L2 = (1/N) sum ||p_est,i - p_GT,i||. Anchor GT at the first sensor pose and map image-camera axes with diag(1,-1,-1); do not fit an extra alignment. Evaluate the same retained frame IDs and preserve frame 1. Remove a 1 m ceiling band only from the merged display cloud. For RGB-D capture, skip semantic-mesh loading unless requested and initialize Habitat before pygame to avoid asset/GL conflicts.

2. Pipeline-grounded evidence

Record RawPointCount and VoxelizedPointYield per frame; record RANSAC and ICP fitness, inlier RMSE (m), and correspondence count per pair. Fitness is an inlier fraction, not a pose-accuracy guarantee [1-3]. This gives 2N + 6(N-1) occurrences: 1,522 for Phase 1 and 2,802 for the manual Phase 2 baseline. Declarations, sealed records and saved trajectories keep experiments separate.

![Figure 1. Phase 1 baseline factors. Shading: frames 50-60, 70-99, 100-114 and 115-130. Pair values at i describe i-1 to i. Raw counts match positive-depth pixels in all 191 images.](assets/phase1_factors.png)

Figure 1. Phase 1 baseline factors. Shading: frames 50-60, 70-99, 100-114 and 115-130. Pair values at i describe i-1 to i. Raw counts match positive-depth pixels in all 191 images.

Frames 100-114 have mean raw support 215,269, ICP fitness 0.851 and RMSE 0.0249 m; the saved diagnostic trajectory reproduces the historical score and shows increased offset there. Yet frame 120 has 16.31% missing depth and fitness 0.9983. Missing depth, turns and visible structure must be considered together; coincidence does not prove causation.

## Results: Phase 1

| Run | N / kept | Voxel m | Mean L2 m | Total s |
| --- | --- | --- | --- | --- |
| Historical full baseline | 191 / 100% | 0.05 | 0.058835 | NR |
| Depth + ICP selection | 179 / 93.72% | 0.05 | 0.305000 | 280.44 |
| Selection, add frame 104 | 180 / 94.24% | 0.05 | 0.125820 | 280.07 |
| Finer voxel + linked scales | 191 / 100% | 0.03 | 2.965126 | 1524.47 |
| Depth SOR (20 neighbors, 3 SD) | 191 / 100% | 0.05 | 0.338406 | 160.11* |

NR = not recorded. Total includes reconstruction, diagnostics, evaluation and PNG/NPZ output, not declaration/sealing/dashboard. *SOR includes 23.16 s preprocessing. Historical runtime environments were not fully matched; differences are descriptive. Voxel 0.03 also changes normal/FPFH radii to 0.06/0.15 m and matching gates to 0.045 m.

![reconstruction_baseline](../experiments/phase1_open3d_reference/reconstruction_baseline.png)

![reconstruction_baseline](../experiments/phase2_manual_baseline/reconstruction_baseline.png)

Figure 2. Ceiling-cropped maps, red estimated / black GT. Left: fresh Phase 1 Open3D reference, 0.291071 m (not the historical 0.058835 m run). Right: manual Phase 2 baseline, 0.240687 m. Several connected rooms are visible; complete floor coverage is not quantitatively verified.

What the interventions tested

Selection: exclude a candidate only when RawPointCount < 222,822.4 (85% of pixels) AND [ICP fitness < 0.90 OR RMSE > 0.025 m]. Keep frame 1 and every third frame as bridges. This exploratory rule uses no GT, but its 179-frame result is worse. Restoring frame 104 reduces common-179-frame error to 0.1250 m, still above baseline 0.0579 m. This rescue was motivated by post-hoc GT diagnosis, not an independent generalizable rule.

Point filtering: per-frame statistical outlier removal (SOR) [4] zeros removed depth pixels while preserving all frames and retained depth values. Mean removal is 1.48% (max 3.48%). Error grows from 3.35 to 21.98 cm over 103-104, then to 76.18 cm at 105. Masks also remove distant real surfaces, so lost geometric support is a plausible, unproven cause. Neither this setting nor finer voxels improves the saved baseline; original data and artifacts remain unchanged.

## Results: Phase 2

Manually collect 351 frames using second_floor.yaml into eval/_data/second_floor/115062519_manual_20261104_082753. RGB/depth/GT entries match and decode. Maximum adjacent motion is 0.4715 m and 6.00 degrees; mean valid depth is 99.53%. The route traverses connecting spaces and room-facing views; complete floor coverage remains unverified.

Using current zone settings, benign/moderate/severe/outside counts are 4/11/0/336; no capture-time configuration snapshot exists. Therefore, this sequence does not test severe-zone performance. The earlier API capture has 281 frames and Mean L2 5.8823 m (215.06 s total); different routes, viewpoints and zone exposure prevent a controlled manual/API comparison.

| Evaluation | Frames | Mean L2 m | Total s |
| --- | --- | --- | --- |
| Full manual baseline | 351 | 0.240687 | 108.50 |
| Baseline on retained frames | 348 | 0.238854 | Not rerun |
| Selected reconstruction | 348 (99.15%) | 0.236077 | 104.35 |

Reuse the Phase 1 rule unchanged. Candidates are 294, 311, 313, 350; keep bridge frame 294 and exclude only 311, 313, 350. Reconstruct from scratch at voxel 0.05 m, Open3D, seed 0. No GT is used to choose frames; original images are not deleted.

![Figure 3. Manual baseline factor timelines. Red lines mark excluded frames: fewer than 85% valid points and RMSE above 0.025 m. Actual new splice diagnostics are saved separately.](assets/phase2_factors.png)

Figure 3. Manual baseline factor timelines. Red lines mark excluded frames: fewer than 85% valid points and RMSE above 0.025 m. Actual new splice diagnostics are saved separately.

![Figure 4. Baseline versus selected trajectories/errors (GT black). Curves use their own frame sets; the table also compares the common 348 frames.](assets/phase2_selection_comparison.png)

Figure 4. Baseline versus selected trajectories/errors (GT black). Curves use their own frame sets; the table also compares the common 348 frames.

The gain is only 2.78 mm (1.16%) on common frames. Reruns differ by up to 1.32 mm in a coordinate before selection changes; stable improvement is unproven. New splice pairs complete successfully. Full factor measurement versus pair-diagnostic work also differs, so the timing difference cannot be assigned solely to deletion.

## Custom ICP and discussion

Implementation. my_local_icp_algorithm uses SciPy cKDTree nearest neighbors, a 0.075 m gate and point-to-plane residual r = n dot (p-q). Solve J delta = -r with J = [p cross n, n], then left-compose rotation/translation. Stop at 60 iterations, fewer than 10 pairs, or residual-change/step norm below 1e-6. It does not call Open3D ICP; no robust loss, damping or degeneracy checks were added.

| Same 191 original frames | Mean L2 m | Recon. s | Total s |
| --- | --- | --- | --- |
| Fresh Open3D reference | 0.291071 | 152.23 | 154.13 |
| Custom ICP | 2.174410 | 167.19 | 169.78 |

Custom ICP has about 89.66 degrees of relative-rotation error at 104-105 and is 9.8% slower end-to-end in this trial. Both runs use OMP_NUM_THREADS=8 sequentially, with the shared settings on page 1; native iteration caps differ (60/100). However, 188/190 RANSAC initial transforms differ despite seed 0, and the fresh Open3D score does not reproduce the historical baseline. Thus, this is not a pure local-solver benchmark; timing includes features, RANSAC and map merging. Matched initial transforms and repeated trials are needed for stronger conclusions.

Q1. What happens without RANSAC?

ICP is local: nearest-neighbor assignments depend on initialization [2,3]. Without a good initial pose, turns or repeated/flat geometry can lead to wrong correspondences and a local minimum. Very small inter-frame motion may still converge. No no-RANSAC ablation was run; this is a method-based expectation.

Q2. What affects ICP stability?

Balance voxel resolution, normal/FPFH support and matching gates, then use global initialization. More points did not guarantee better results: voxel 0.03 also tightened linked scales and worsened this run. Robust losses and damped updates are possible extensions, not tested improvements. High inlier fitness alone does not guarantee correct pose.

Q3. How do data quality and collection affect error?

Depth loss reduces potential support, but overlap and visible geometry determine whether useful constraints survive. Deleting frames or distant points can remove those constraints. Phase 2 selection barely changes common-frame error; the manual/API score difference is confounded by route and coverage. Preserve negative results and report associations rather than causal claims.

Limits: single trials, unmatched historical timing conditions, missing old runtimes, rerun sensitivity, qualitative map completeness and absent manual severe-zone coverage. GT is used only after reconstruction for evaluation/diagnosis. New records have complete factors and valid seals; source data, historical artifacts and scores pass saved integrity checks.

References and evidence

[1] Course handout, HW1: 3D Scene Reconstruction, sections 2.2.2, 3.2-3.5, 4-5; implementation: utils.py, reconstruct.py, api.py, ontology/hw1.ttl. [2] Open3D [ICP registration](https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html). [3] [Global registration](https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html). [4] [Outlier removal](https://www.open3d.org/docs/release/tutorial/geometry/pointcloud_outlier_removal.html). Experiments use Open3D 0.18.0, Python 3.9.23, NumPy 1.26.4 and SciPy 1.13.1.

Full evidence remains under experiments/; report/sources.json records input hashes. No new reconstruction was run for this report. Package report.pdf with the required code, ontology and README at the ZIP root; exclude captures, diagnostic outputs, experiment Turtle files and Replica assets [1].

