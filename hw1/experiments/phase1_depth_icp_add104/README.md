# 僅加回 frame 104 的對照結果

這是獨立保存的事後對照快照：相對上一輪 179 張選擇，只加回 frame 104，
不改變其他排除影格或重建設定。原 baseline 與 179 張版保持不變。

| 版本 | Frames | 各自 Mean L2 | 共同 179 張 Mean L2 |
|---|---:|---:|---:|
| 完整 baseline | 191 | 5.88 cm | 5.79 cm |
| 上輪篩選 | 179 | 30.50 cm | 30.50 cm |
| 僅加回 104 | 180 | 12.58 cm | 12.50 cm |

共同影格上的誤差較上一輪降低約 59%，但 baseline 仍較好。
本次沒有再出現 103→105 的直接配準；103→104 仍有明顯錯估位移，
因此不能宣稱加回 104 已完全修復此段。此策略來自前次 GT 評估診斷，
不是可泛用的資料品質規則；GT 不輸入重建演算法。

主要檔案：

- `reconstruction_selected.png`：180 張版本的去天花板俯視重建圖。
- `analysis/intervention_comparison.png`：三組軌跡與逐幀誤差比較。
- `analysis/three_run_comparison.csv`：各自與共同影格的指標、實測時間。
- `analysis/intervention_findings.md`：中文結果、配對數值與討論。
- `analysis/intervention_protocol.md`：實驗假設、控制條件與指令。
- `analysis/selected_pair_diagnostics.json`：本次所有實際相鄰配對的診斷。
- `analysis/selected_trajectory.npz`：估計位置、GT 位置與逐幀誤差。
- `queries/conservative_depth_icp_add104.rq`：只額外保留 frame 104 的查詢。
- `phase1_baseline.ttl`：此結果的完整 sealed experiment 快照。
- `phase1_baseline/plots/`：探索工具產生的圖表。

Turtle 保留原始 sealed identity 與檔案 stem，讀取時需明確指定檔案：

```bash
# 從 hw1 執行
pixi run -e habitat python api.py explore \
  experiments/phase1_depth_icp_add104/phase1_baseline.ttl
```

已有結果時，分析腳本會拒絕重跑覆寫。未來策略應使用新的目錄與宣告。
