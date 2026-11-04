# Phase 2 手動資料：保守深度與 ICP 聯合選幀（執行前記錄）

來源是 `phase2_manual_baseline` 的 351 張完整手動資料及 sealed 因子。
本次沿用 Phase 1 已試過的門檻，沒有依照 Phase 2 GT 最佳化門檻。

假設：排除深度點數減少且局部配準殘差偏高的少數觀測，可能減少後段
軌跡漂移；但跨過影格也可能降低重疊、放大錯誤，因此結果可能不改善。
baseline 已相當準確，這次是檢驗刪幀影響，不預設一定提升。

規則：RawPointCount < 0.85 × 512 × 512 = 222822.4，且
ICPInlierFitness < 0.90 或 ICPInlierRMSE > 0.025 m，才列為候選。
frame 1 及編號為 3 的倍數者強制保留，避免連續刪除超過兩張。
門檻是探索性選擇，不是課程提供的品質 Pass/Fail。

候選是 294、311、313、350；294 為強制保留的連接幀。
實際排除 311、313、350，保留 348/351（99.145%），最大編號間距為 2。
不刪磁碟上的 RGB-D 或 GT，不以 GT、逐幀位置誤差決定保留清單。

固定 Open3D、voxel 0.05 m、seed 0；相機 intrinsics、法向量／FPFH
尺度、RANSAC／ICP 門檻均沿用 baseline。重新配準實際保留影格，
不從 baseline 軌跡抽樣冒充新的重建。

評估會同時報告：baseline 全 351 張、baseline 在共同 348 張上的誤差、
selected 348 張的誤差，以及保留比例和耗時。
GT 僅在重建完成後載入評估。來源 baseline 的全部檔案以 SHA-256
記錄並在結束時驗證未改動。只執行這一組，不根據結果自動調門檻重試。

這是 sealed 實驗的獨立結果快照，內部仍保留 `phase2_manual_baseline`
identity 及檔名；外部目錄以策略命名，使用 API 時傳入明確 Turtle 路徑。
baseline 因子為選擇依據；新相鄰配對診斷另存 JSON，不覆蓋原因子。

從 hw1 執行：

```bash
OMP_NUM_THREADS=8 .pixi/envs/habitat/bin/python experiments/phase2_manual_depth_icp_selection/analysis/run_selection.py
# 檢視結果後只記錄既有量測
.pixi/envs/habitat/bin/python experiments/phase2_manual_depth_icp_selection/analysis/run_selection.py --record
.pixi/envs/habitat/bin/python api.py explore experiments/phase2_manual_depth_icp_selection/phase2_manual_baseline.ttl
```

時間比較的限制：baseline 另量測 pipeline 因子，selected 只另存配對診斷，
所以耗時可以描述各自實測成本，不能視為僅由刪除三張所造成的差異。
