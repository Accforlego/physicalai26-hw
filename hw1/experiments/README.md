# HW1 實驗索引

| 目錄 | 用途 | 結果 |
|---|---|---|
| `phase1_baseline/` | 3.2.3：未篩選的原始 baseline 與分析 | 191 frames；Mean L2 5.88 cm |
| `phase1_depth_icp_selection/` | 3.2.4：深度缺失與 ICP 因子聯合篩選的結果快照 | 179 frames；Mean L2 30.50 cm；未改善 |
| `phase1_depth_icp_add104/` | 只在上一輪加回 frame 104 的事後對照快照 | 180 frames；Mean L2 12.58 cm；優於 179 張版，仍不如 baseline |
| `phase1_voxel_003/` | 全部保留，voxel size 改為 0.03 m 並沿用連動尺度 | 191 frames；Mean L2 2.965 m；明顯劣於 0.05 m baseline |
| `phase1_depth_sor/` | 全部保留，逐張深度點雲做 SOR（20 neighbors、3σ），固定 voxel 0.05 m | 191 frames；Mean L2 33.84 cm；未改善 |
| `phase1_my_icp/` | 原始資料完整保留，切換既有自製 point-to-plane ICP | 191 frames；Mean L2 2.174 m；重建 167.19 s |
| `phase1_open3d_reference/` | 為自製 ICP 補跑的相同環境 Open3D 計時參照 | 191 frames；Mean L2 29.11 cm；重建 152.23 s；未重現舊 baseline 分數 |
| `phase2_baseline/` | API 自動導航採集，沿用 0.05 m 原設定、完整保留影格 | 281 frames；Mean L2 5.882 m；存在明顯配準失敗 |
| `phase2_manual_baseline/` | 手動採集，沿用 0.05 m 原設定、完整保留影格 | 351 frames；Mean L2 24.07 cm；未涵蓋 severe 區域 |
| `phase2_manual_depth_icp_selection/` | 手動資料保守排除 311、313、350，固定 0.05 m | 348 frames；Mean L2 23.61 cm；共同影格僅改善約 2.8 mm |

兩個篩選結果目錄中的 `phase1_baseline.ttl` 保留原 sealed identity，請以明確
Turtle 檔案路徑操作。詳見該目錄 README，避免把快照目錄名稱當作
Turtle 檔名。各實驗目錄分開保存圖表、分析及重建結果。
`phase1_voxel_003` 為重新宣告與重新量測的新實驗，可直接使用其目錄操作。
