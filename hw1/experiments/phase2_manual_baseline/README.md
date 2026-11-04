# Phase 2 手動採集 baseline

使用者以鍵盤操作採集，資料位於 `eval/_data/second_floor/115062519_manual_20261104_082753/`。
完整保留 351 張 RGB-D；與 API 採集的 `phase2_baseline` 分開保存。

| 項目 | 結果 |
|---|---:|
| Mean L2 | 0.240687 m（24.07 cm） |
| 最大 L2 | 0.481583 m（frame 312） |
| 重建時間 | 106.88 秒 |
| 含量測、評估及 PNG/NPZ 輸出的時間 | 108.50 秒 |
| pipeline 因子 | 2802 筆，全部量測 |

設定沿用原 baseline：Open3D point-to-plane ICP、voxel 0.05 m、seed 0，
法向量半徑 0.10 m、FPFH 半徑 0.25 m、配準門檻 0.075 m。
使用本次資料的 intrinsics；GT 僅在重建完成後用於評估，未用於配準或軌跡校正。

RGB、uint16 毫米 depth、GT 各 351 筆，編號連續且所有 PNG 可解碼。
相鄰最大平移 0.4715 m、最大轉角 6.00°；平均有效 depth 比例 99.53%。
依目前 `configs/second_floor.yaml` 的區域設定統計：benign 4、moderate 11、
severe 0、outside 336。這批資料未涵蓋 severe，不能視為三種干擾的完整測試。

估計軌跡跟隨 GT 主要路線，仍有累積偏移。API 版本的 Mean L2 為 5.8823 m，
但兩批資料的路線、影格數、區域涵蓋與拍攝時機不同，分數差異不能單獨歸因於操作方式。
詳見 `analysis/findings.md`。

主要產物：

- `reconstruction_baseline.png`：點雲俯視與估計／GT 軌跡。
- `analysis/trajectory_diagnostic.png`：軌跡對照與逐幀誤差。
- `analysis/capture_route.png`、`capture_overview.png`：GT 路線及輸入影像。
- `analysis/results.json`、`baseline_results.csv`：評估數據與實測耗時。
- `analysis/trajectory.npz`、`pair_diagnostics.json`：完整估計變換與配準診斷。
- `analysis/capture_validation.json`、`integrity_verification.json`：資料及結果驗證。
- `plots/dashboard.html`、`timelines.html`、`distributions.html`、`tradeoff.html`：因子圖表。
- `phase2_manual_baseline.ttl`：事前預測、正式量測及 baseline 評估，已封存。

執行入口（從 hw1；已有結果或已封存時會拒絕重新覆寫）：

```bash
OMP_NUM_THREADS=8 .pixi/envs/habitat/bin/python experiments/phase2_manual_baseline/analysis/run_baseline.py
# 檢視結果後封存既有量測，不再次重建
.pixi/envs/habitat/bin/python experiments/phase2_manual_baseline/analysis/run_baseline.py --record
.pixi/envs/habitat/bin/python api.py explore experiments/phase2_manual_baseline
```

新實驗需另行宣告名稱及資料來源，在重建前填寫預測。
