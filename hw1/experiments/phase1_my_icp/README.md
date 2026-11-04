# Phase 1 自製 ICP 對照

使用原始 `eval/first_floor` 全 191 張，沒有刪幀、深度濾波或修改 utils.py。
voxel 0.05 m、seed 0、FPFH／法向量尺度與配準距離門檻保持原設定。
將既有 `my_local_icp_algorithm` 作為 backend，另補跑 Open3D 計時參照。

| 版本 | Frames | Mean L2 | 最大 L2 | 重建時間 | 含量測、評估及 PNG/NPZ 輸出 |
|---|---:|---:|---:|---:|---:|
| 舊 Open3D baseline（保留） | 191 | 0.058835 m | 0.116941 m | 未記錄 | 未記錄 |
| 本次 Open3D 參照 | 191 | 0.291071 m | 0.649890 m | 152.23 s | 154.13 s |
| 本次 my_icp | 191 | 2.174410 m | 7.342940 m | 167.19 s | 169.78 s |

自製版在這次完整流程執行中誤差較大，重建時間約為新 Open3D 參照的 1.098 倍。
重建時間包含反投影、預處理、RANSAC、ICP 及點雲合併，不是獨立 ICP 計時。
兩次依序執行，OMP_NUM_THREADS=8，沒有同時重建或挑種子。

**比較限制：** seed 相同並未保證實際 RANSAC 初始變換相同，190 對中有
188 對的初始變換在 1e-10 容差下不同，最大矩陣元素差約 0.853。
本次 Open3D 也未重現舊 baseline 的分數，因此不是固定每對初始變換後的
純 ICP 控制比較，不能將全部差距歸因於 ICP，也不宣稱速度差具有統計顯著性。
RANSAC／平行執行的非確定性可能相關，但尚未控制變因驗證差異來源。
原始資料與舊 baseline 全部檔案的雜湊均未改動。

自製版 104→105 相對旋轉誤差約 89.66°，之後軌跡大幅偏離。
同一對的新 Open3D 結果約 0.20°，但兩者實際初始變換不同。
GT 僅用於重建後的分數、軌跡與相對姿態診斷，未用於求解或篩選。
完整說明見 `analysis/implementation_notes.md` 與 `analysis/findings.md`。

主要檔案：

- `phase1_my_icp.ttl`：明確宣告 my_icp、新量測的 1522 筆因子及結果，已封存。
- `analysis/results.json`、`baseline_results.csv`：本次自製版評估與耗時。
- `analysis/backend_comparison.csv`、`backend_comparison.png`：三組數據及兩組新軌跡。
- `analysis/comparison_and_integrity.json`：資料、GT、分數、有效旋轉及 seal 驗證。
- `analysis/trajectory.npz`、`pair_diagnostics.json`：完整估計變換與配準診斷。
- `analysis/posthoc_relative_pose_errors.json`：以 GT 做的事後相對姿態誤差。
- `analysis/paired_registration_diagnosis.json`：兩組初始變換差異及關鍵配對。
- `analysis/run_environment.json`：套件版本、utils 雜湊及執行設定。
- `reconstruction_baseline.png`：此新宣告的完整資料重建，不是舊 Open3D baseline。
- `plots/`：自製版新實驗的因子圖表。

Open3D 新參照位於 `../phase1_open3d_reference/`；舊 baseline 未被覆寫。
兩個新實驗各自重新量測全部因子，沒有沿用舊實驗的數值。

從 hw1 執行入口如下。已有結果／已封存時，runner 拒絕覆寫；
新設定需另行宣告新名稱，重建前填寫預測與 backend 設定。

```bash
OMP_NUM_THREADS=8 .pixi/envs/habitat/bin/python experiments/phase1_my_icp/analysis/run_baseline.py
# 檢視結果後只封存既有量測
.pixi/envs/habitat/bin/python experiments/phase1_my_icp/analysis/run_baseline.py --record
.pixi/envs/habitat/bin/python experiments/phase1_my_icp/analysis/compare_backends.py
.pixi/envs/habitat/bin/python api.py explore experiments/phase1_my_icp
```
