# Phase 1：3.2.4 資料介入實驗

## 實驗前假設與規則

3.2.3 的觀察顯示，有效深度點減少與配準品質下降有時同時發生，
但深度缺失本身不足以判斷某張影像應被刪除。本次測試聯合規則，
假設排除部分深度缺失且配準品質較弱的觀測，有機會降低累積軌跡誤差。
不使用 GT 位置、逐幀軌跡誤差或特定失敗區段的 frame 編號作為篩選條件。

排除候選必須同時符合：

1. RawPointCount < 222822.4，即 512 × 512 影像中超過 15% 像素沒有有效深度。
2. ICPInlierFitness < 0.90，或 ICPInlierRMSE > 0.025 m。

上述門檻來自本次因子分布的探索性分析，並非作業預定的 Pass/Fail 標準。
保留第 1 張及編號為 3 的倍數的影像作為銜接，因此最多連續排除 2 張。
此策略仍會改變實際配準的相鄰影像；原始 pair 因子只描述原始相鄰影像，
不能視為新銜接 pair 的量測值。

## 查詢預覽

查詢：`../queries/conservative_depth_icp.rq`。

- 原始 191 張，保留 179 張，保留率約 93.72%。
- 排除：71、83、94、95、100、104、106、107、112、113、115、124。
- 9 個銜接缺口，最大缺口長度 2 張；新配對的原始編號差最多為 3。
- 原始 17 張排除候選中，96、105、108、114、123 因銜接規則保留。
- 第 1 張與第 191 張均保留，評估參考座標系一致。

## 固定設定與比較方式

- 相同輸入 capture；Open3D FPFH/RANSAC + point-to-plane ICP。
- voxel size = 0.05 m，RANSAC seed = 0。
- 先試跑並檢視圖表，再透過 `api.write_run` 記錄 selected run。
- 不改動 baseline run、已 sealed 的宣告及原始因子量測。
- 除 191 張 baseline 的 Mean L2 外，也比較 baseline 在相同 179 張上的
  Mean L2，避免單純移除難評估影像造成平均值降低的誤解。
- baseline 逐幀數值使用 3.2.3 的診斷重跑，該重跑 Mean L2 與 sealed
  baseline 的記錄精度一致。這些數值不參與影像篩選。
- baseline 原始執行時間未保存，以缺值呈現，不以推估數字補入。
  selected 記錄重建時間與總執行時間；總時間範圍包含重建、評估、
  NPZ 及分析圖輸出，排除查詢和之後的 TTL 寫入、dashboard 更新。

## 重現

此目錄保存原實驗的篩選結果快照；Turtle 保留原始 sealed identity，
因此使用明確的 `phase1_baseline.ttl` 路徑，不以目錄名稱推導 Turtle 名稱。
現有結果不會被分析腳本重跑覆寫；測試新策略時請建立新的結果目錄。

從 `hw1` 目錄使用 Habitat 環境：

```bash
pixi run -e habitat python api.py query experiments/phase1_depth_icp_selection/phase1_baseline.ttl \
  --query-file experiments/phase1_depth_icp_selection/queries/conservative_depth_icp.rq

pixi run -e habitat python experiments/phase1_depth_icp_selection/analysis/run_selection.py

# 檢視結果後寫入相同 selected run，不再次重建
pixi run -e habitat python experiments/phase1_depth_icp_selection/analysis/run_selection.py --record

pixi run -e habitat python api.py explore experiments/phase1_depth_icp_selection/phase1_baseline.ttl
```

也可用作業 CLI 執行相同查詢與重建：

```bash
pixi run -e habitat python reconstruct.py \
  --experiment experiments/phase1_depth_icp_selection/phase1_baseline.ttl \
  --selection-query experiments/phase1_depth_icp_selection/queries/conservative_depth_icp.rq \
  --voxel-size 0.05 --seed 0 --no-vis --override-experiment
```

CLI 會更新 `reconstruction.png` 與 `reconstruction_selected.png`；
本次分析腳本只另存 selected 的俯視圖，原有 baseline 圖保持不變。
