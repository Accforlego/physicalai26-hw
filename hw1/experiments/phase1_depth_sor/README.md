# Phase 1 深度統計離群點移除（SOR）

完整保留 191 張，以每張原解析度點雲的 statistical outlier removal
（20 個鄰近點、std_ratio=3.0）建立深度遮罩；只把濾除點對應像素設為 0，
其餘深度值不變。原始資料與既有實驗皆保留，`utils.py` 未修改。

| 評估 | Frames | Mean L2 | 最大 L2 |
|---|---:|---:|---:|
| 原始 baseline | 191 | 5.88 cm | 11.69 cm |
| 深度 SOR | 191 | 33.84 cm | 78.04 cm |

**此次未改善。** 103→104 及 104→105 的位置誤差明顯增加，之後帶著偏移繼續重建。
統計濾波可能排除遠距、稀疏的真實表面，不保證保留配準所需的幾何支撐。
這次只測一組設定，沒有調門檻追求較好的分數。

Open3D point-to-plane ICP、voxel 0.05 m、seed 0、法向量半徑 0.10 m、
FPFH 半徑 0.25 m、RANSAC／ICP 距離門檻 0.075 m 均沿用 baseline。
RGB、GT、intrinsics 逐位元相同；GT 僅用於重建後評估。

平均每張移除 1.484% 的正深度點，最大 3.475%；總共移除 712,919／47,662,199 點。
前處理 23.16 秒，重建 135.14 秒；前處理加量測、評估及 PNG/NPZ 輸出合計
160.11 秒。原 baseline 缺少完整計時，不宣稱速度改善。

資料來源 `eval/first_floor`；衍生資料 `eval/first_floor_sor_nb20_std3`。
兩者分開保存，衍生 batch 以 prov:wasDerivedFrom 記錄來源。
衍生資料的 1522 筆 pipeline 因子全部重新量測，沒有沿用原 capture 的因子。
`RawPointCount` 在新實驗中代表濾除後的正深度點數，原數量另存前處理紀錄。

主要檔案：

- `analysis/intervention_protocol.md`：重建前固定的假設、設定及限制。
- `analysis/neighbor_inspection.json`：六張樣本的鄰近距離分布與濾除比例。
- `analysis/preprocessing.json`：全部 191 張的點數、移除比例及衍生深度雜湊。
- `analysis/depth_mask_examples.png`、`removed_point_fractions.png`：遮罩及移除比例。
- `analysis/intervention_comparison.png`、`intervention_comparison.csv`：baseline 對照。
- `analysis/comparison_and_integrity.json`：評估及原始資料／baseline 雜湊驗證。
- `analysis/largest_error_increases.json`：誤差增幅最大的配對。
- `analysis/results.json`、`trajectory.npz`、`pair_diagnostics.json`：本次重建結果。
- `analysis/intervention_findings.md`：結果分析與限制。
- `phase1_depth_sor.ttl`：新 identity、事前預測、完整實測及評估，已封存。
- `reconstruction_baseline.png`：衍生 capture 的完整重建；此名稱由共用分析腳本產生。
- `plots/`：新實驗的因子圖表。

從 hw1 重現的流程如下。準備資料及重建腳本會拒絕覆寫既有結果；
若重做不同設定，需改用新的資料與實驗名稱，並在重建前填寫預測。

```bash
OMP_NUM_THREADS=8 .pixi/envs/habitat/bin/python experiments/phase1_depth_sor/analysis/prepare_depth.py
.pixi/envs/habitat/bin/python api.py batch2ttl --data-dir eval/first_floor_sor_nb20_std3 --floor 1 --derived-from floor1_first_floor
.pixi/envs/habitat/bin/python api.py declare --name phase1_depth_sor --data-dir eval/first_floor_sor_nb20_std3 --floor 1
# 在首次重建前填妥 label 與 PREDICTION；本次已填寫並封存。
OMP_NUM_THREADS=8 .pixi/envs/habitat/bin/python experiments/phase1_depth_sor/analysis/run_baseline.py
# 檢視結果後記錄既有量測，不再次重建
.pixi/envs/habitat/bin/python experiments/phase1_depth_sor/analysis/run_baseline.py --record
.pixi/envs/habitat/bin/python experiments/phase1_depth_sor/analysis/compare_results.py
.pixi/envs/habitat/bin/python api.py explore experiments/phase1_depth_sor
```
