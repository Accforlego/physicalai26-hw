# Phase 2 手動資料：深度與 ICP 聯合選幀

沿用第一階段保守規則，從手動 baseline 的 351 張排除 311、313、350，
保留 348 張（99.145%）。原始 RGB-D、GT 及 `phase2_manual_baseline` 均未修改。
Open3D、voxel 0.05 m、seed 0 固定不變。

| 評估 | 張數 | Mean L2 |
|---|---:|---:|
| baseline 全部影格 | 351 | 24.07 cm |
| baseline 在共同影格上 | 348 | 23.89 cm |
| 選幀後重新重建 | 348 | 23.61 cm |

共同影格上的差距約 2.8 mm（1.16%），單次結果略好，但幅度很小。
前 310 張尚未改變選擇的區段，兩次重跑仍存在最大約 1.32 mm 的座標分量差異，
因此不能把全部差距歸因於刪幀，亦不能宣稱已驗證穩定改善。
這裡的 1.32 mm 是前段座標差的觀察，不是全域誤差的統計信賴區間。

規則：RawPointCount < 總像素的 85%，且 ICP fitness < 0.90 或
ICP RMSE > 0.025 m 才列入候選；frame 1 及每第三張強制保留。
候選 294 因連接規則保留。選擇不使用 GT 或位置誤差，未調整門檻重試。
詳見執行前保存的 `analysis/intervention_protocol.md`。

時間：baseline 重建 106.88 秒、含量測與輸出 108.50 秒；
selected 重建 102.75 秒、含診斷與輸出 104.35 秒。
兩者的因子量測工作不同，不能將耗時差異全視為刪幀帶來的加速。

主要檔案：

- `queries/conservative_depth_icp.rq`：SPARQL 選擇規則。
- `analysis/selection_plan.json`、`intervention_protocol.md`：執行前固定的清單與假設。
- `analysis/intervention_results.json`、`intervention_comparison.csv`：評估及耗時。
- `analysis/intervention_comparison.png`：軌跡及逐幀誤差比較。
- `analysis/selection_input_evidence.png`：候選影格的 RGB-D。
- `analysis/selected_pair_diagnostics.json`、`selected_trajectory.npz`：新配準與完整保留軌跡。
- `analysis/intervention_findings.md`：結果與限制。
- `analysis/integrity_after.json`：來源 baseline 21 個檔案雜湊未變及結果驗證。
- `reconstruction_selected.png`：去天花板重建俯視。
- `reconstruction_baseline.png`：來源 baseline 的參照副本。

這是 sealed baseline 加上 selected run 的獨立快照，Turtle 檔名與內部 identity
維持 `phase2_manual_baseline`；來源 baseline 的 2802 筆因子維持原樣。
新配對的診斷另存 JSON，不冒充原始相鄰影格的因子。
API 必須使用明確檔案路徑，例如從 hw1：

```bash
.pixi/envs/habitat/bin/python api.py explore experiments/phase2_manual_depth_icp_selection/phase2_manual_baseline.ttl
```

圖表位於 `phase2_manual_baseline/plots/`，此子目錄由探索工具依 sealed identity 產生。
分析腳本已有結果時會拒絕覆寫；未來新策略另存新快照。
這批資料未涵蓋 severe 區域的限制與原 baseline 相同。
