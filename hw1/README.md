# PhysicalAI26 HW1

This repository contains the HW1 capture simulator and a reconstruction and
experiment workflow. Python dependencies are managed by [Pixi](https://pixi.sh/)
using the checked-in `pixi.lock` file.

## Setup

1. Install Pixi using the instructions at [pixi.sh](https://pixi.sh/).
2. From this directory, create the `habitat` environment:

   ```bash
   pixi install -e habitat
   ```

   The environment provides Python 3.9, Habitat-Sim 0.3.3 with Bullet,
   Habitat-Lab, and the project dependencies. The first install can take a few
   minutes.
3. Check that Habitat-Sim and Habitat-Lab import correctly:

   ```bash
   pixi run -e habitat smoke
   ```

4. Download and extract the Replica apartment scene used by the default
   configuration:

   ```bash
   pixi run -e habitat fetch-replica
   ```

   This creates `replica_v1/apartment_0/`. Keep the scene at that path for the
   default `configs/second_floor.yaml` configuration.

## Capture data

Start the interactive Habitat-Sim collector:

```bash
pixi run -e habitat python load.py
```

The default configuration is `configs/second_floor.yaml`. Captures are written
under `eval/_data/second_floor/` and include RGB and depth PNGs, camera
intrinsics, and a ground-truth pose trajectory. Use `--config` to select a
different configuration or `--output-root` to change the output directory. See
[`docs/load.md`](docs/load.md) for controls, replay mode, and capture details.

## Reconstruction and experiments

Run commands from this repository directory with `pixi run -e habitat`. The
experiment workflow starts by declaring an experiment over a capture, then
reconstructing it:

```bash
pixi run -e habitat python api.py declare \
  --name <experiment-name> \
  --data-dir <capture-directory> \
  --floor 2

pixi run -e habitat python reconstruct.py \
  --experiment experiments/<experiment-name> \
  --no-vis

pixi run -e habitat python api.py explore experiments/<experiment-name>
```

`declare` creates an experiment directory, the first reconstruction measures
pipeline factors and records a baseline, and `explore` displays the results and
writes interactive plots. For the full workflow, SPARQL frame selection, and
query examples, see [`docs/e2e-workflow.md`](docs/e2e-workflow.md).

## Optional bonus: custom ICP

The custom implementation is `my_local_icp_algorithm` in
[`utils.py`](utils.py). It performs point-to-plane ICP using SciPy `cKDTree`
nearest-neighbor search, distance-gated correspondences, and NumPy least-squares
rotation/translation updates. It does not call Open3D's `registration_icp`.
The required Open3D backend remains available and is the default.

To run the custom backend on the full Phase 1 capture, start a new experiment
from this directory (use a different name if this one already exists):

```bash
pixi run -e habitat python api.py declare \
  --name phase1_bonus_my_icp \
  --data-dir eval/first_floor \
  --floor 1
```

Before reconstruction, edit
`experiments/phase1_bonus_my_icp/phase1_bonus_my_icp.ttl`: fill in the label
and prediction, change the Experiment node's final `hw1:onBatch` terminator
from `.` to `;`, and append this setting to that node:

```turtle
    hw1:hasFactorSetting [
        a hw1:FactorSetting ;
        hw1:settingParameter hw1:icpBackend ;
        hw1:settingRole hw1:ReconstructionSetting ;
        hw1:settingForFactor hw1:ReconstructionRun ;
        hw1:settingValue "my_icp"^^xsd:string
    ] .
```

Then run and inspect the experiment:

```bash
pixi run -e habitat python reconstruct.py \
  --experiment experiments/phase1_bonus_my_icp \
  --version my_icp --voxel-size 0.05 --seed 0 --no-vis

pixi run -e habitat python api.py explore experiments/phase1_bonus_my_icp
```

The first reconstruction records measurements and seals the declaration.
The `--version` flag must agree with the declared `icpBackend`; changing
backends requires a separate experiment. Compare with a separate Open3D run
using the same capture, voxel size, seed, and execution environment. The custom
backend uses up to 60 iterations and Open3D up to 100; their stopping rules
differ, and a shared seed does not guarantee identical RANSAC initial poses.
Report these limitations when comparing trajectory error and runtime.

## More documentation

- [`docs/pixi.md`](docs/pixi.md): environment details and Pixi commands
- [`docs/load.md`](docs/load.md): capture settings, controls, and outputs
- [`docs/reconstruct.md`](docs/reconstruct.md): reconstruction options
- [`docs/api.md`](docs/api.md): experiment and inspection commands
- [`docs/e2e-workflow.md`](docs/e2e-workflow.md): end-to-end walkthrough
