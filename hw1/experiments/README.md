# HW1 實驗索引

| 目錄 | 用途 | 結果 |
|---|---|---|
| `phase1_baseline/` | 3.2.3：未篩選的原始 baseline 與分析 | 191 frames；Mean L2 5.88 cm |
| `phase1_depth_icp_selection/` | 3.2.4：深度缺失與 ICP 因子聯合篩選的結果快照 | 179 frames；Mean L2 30.50 cm；未改善 |

第二個目錄中的 `phase1_baseline.ttl` 保留原 sealed identity，請以明確
Turtle 檔案路徑操作。詳見該目錄 README，避免把快照目錄名稱當作
Turtle 檔名。兩個目錄分開保存圖表、分析及重建結果。
