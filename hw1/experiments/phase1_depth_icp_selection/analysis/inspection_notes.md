# Phase 1 baseline: inspection for section 3.2.3

The sealed baseline records 191 frames and Mean L2 = 0.05883481 m.
The inspection does not change the sealed experiment or perform frame selection.

## Recorded factor timelines

| Frames | Mean raw points | Mean ICP fitness | Mean ICP RMSE (m) |
|---|---:|---:|---:|
| 1-49 | 261657.51 | 0.92036 | 0.01974 |
| 50-60 | 249754.64 | 0.89820 | 0.02222 |
| 61-69 | 262144.00 | 0.95647 | 0.01939 |
| 70-99 | 231851.93 | 0.94338 | 0.02206 |
| 100-114 | 215269.27 | 0.85118 | 0.02488 |
| 115-130 | 229430.06 | 0.92604 | 0.02218 |
| 131-191 | 260309.93 | 0.93412 | 0.01982 |

Pair factors at index i describe registration of frame i to frame i-1;
the first frame has no pair metric. The broad low-point interval contains
intermittent recoveries and extends past frame 130. Frames 100-114 are the
strongest joint signal among the inspected intervals, but alignment weakness
also occurs outside low-raw-point intervals (e.g. frames 26 and 150-151).

## Direct depth-image inspection

All 191 depth images were checked: their positive-pixel counts match the
sealed RawPointCount values exactly. The image size is 512 x 512, so the
missing-depth fraction is 1 - RawPointCount / 262144.

| Frame | Zero-depth pixels | Voxel points | ICP fitness | ICP RMSE (m) |
|---|---:|---:|---:|---:|
| 49 | 8.91% | 14381 | 0.98832 | 0.02361 |
| 55 | 7.67% | 16575 | 0.84724 | 0.02342 |
| 65 | 0.00% | 29023 | 0.88995 | 0.01922 |
| 80 | 12.25% | 24699 | 0.88275 | 0.02226 |
| 104 | 19.74% | 10981 | 0.87378 | 0.02914 |
| 114 | 32.25% | 31132 | 0.94180 | 0.02589 |
| 120 | 16.31% | 34877 | 0.99834 | 0.01971 |
| 135 | ~0.00% (3 pixels) | 29140 | 0.98566 | 0.01907 |

The contact sheet shows scattered missing depth in the affected examples,
with an additional contiguous missing patch in frame 114. Frames 65 and 135
provide visually clearer depth references. RGB brightness also changes across
these samples; this does not establish that brightness causes the depth loss.
The geometric registration uses depth geometry and FPFH, so RGB brightness
alone does not establish a cause for registration failure.

Raw point loss does not imply poor registration: frame 120 retains an ICP
fitness near 1 despite missing depth, while frame 114 still has 31132 voxel
points and fitness 0.94180. Viewpoint and geometric structure also matter.
Fitness and inlier RMSE measure agreement of accepted correspondences; neither
alone guarantees an accurate camera pose.

## Existing reconstruction image

The saved reconstruction_baseline.png shows connected rooms and furniture,
with visibly speckled surfaces and holes in some regions. Its top is clipped,
and trajectory lines are partly occluded by scene geometry. This view does
not establish which frames produced the visible artifacts, nor does it allow
reliable frame-specific trajectory-error measurements. It does not show an
obvious wholesale separation of rooms in the visible portion.

factor_comparison.png aligns the four recorded factors; rgb_depth_comparison.png
shows RGB, metric depth (magenta = zero depth), and zero-depth masks (white =
invalid). flagged_gt_route.png locates inspected frames on the GT capture route
for evaluation context only; it is not an estimated-trajectory accuracy plot.

A separate diagnostic rerun uses Open3D, voxel size 0.05 m and seed 0 to save
estimated positions and per-frame errors without writing any experiment run.
Its output must be distinguished from the historical sealed baseline because
the original per-frame estimated positions were not saved.

The rerun completed with Mean L2 = 0.0588348071 m, matching the sealed
baseline to its stored precision. The maximum position error was 0.116941 m
at frame 148. The saved NPZ contains frames, predicted and GT camera positions
in the same first-camera reference system, and per-frame L2 errors.

| Frames | Mean position error (cm) |
|---|---:|
| 1-49 | 0.956 |
| 50-60 | 2.606 |
| 61-69 | 2.822 |
| 70-99 | 2.742 |
| 100-114 | 8.604 |
| 115-130 | 11.110 |
| 131-191 | 10.390 |

The strongest position-error increase occurs around frames 100-106, followed
by a persistent offset. The depth loss, worse local-registration measurements,
and increased trajectory error coincide in this region. This supports a
specific hypothesis to test, rather than proving that missing depth alone
caused the error. In contrast, depth loss over frames 70-99 does not cause a
comparable error increase. Recovery of valid depth after this region does
not automatically remove error already accumulated through pose composition.

GT also shows that frames 104 and 114 share the same camera position but
differ by about 100 degrees in orientation. Thus the affected region includes
turning and changed visible geometry, which are alternative or contributing
explanations. GT was used only for this evaluation and inspection.
