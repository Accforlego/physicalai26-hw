# 僅加回 frame 104 的對照實驗

## 問題與事前決定

上一輪 179 張的選擇移除了 frame 104，103→105 的新配準使估計位置
產生約 71 cm 的跳動，儘管 GT 在這兩張之間沒有平移。
本次只把 frame 104 加回，檢驗中間視角是否有助於維持轉向時的銜接。
這是根據上一輪 GT 評估與誤差診斷提出的事後對照，
不是事先獨立選定的規則，也不是已驗證的泛用資料品質策略。
GT 不作為重建演算法的輸入。

## 唯一處理差異

- 完整 baseline：191 張。
- 上一輪篩選：179 張。
- 本輪：上一輪保留集合加上 104，共 180 張，保留率 94.24%。
- 仍排除：71、83、94、95、100、106、107、112、113、115、124。
- 保留原深度缺失／ICP 門檻及每第 3 張作橋接的規則，僅對 104 加例外。
- 缺口由 9 個降至 8 個，最大連續缺口仍為 2 張。
- 固定 Open3D、voxel size 0.05 m、RANSAC seed 0、原始 RGB-D 與 intrinsics。

同樣 seed 不代表所有後續配對具有相同的隨機抽樣過程：加回一張會多做
一次 RANSAC，改變後續亂數序列。因此單次結果可以評估這個加回策略，
但不能排除後續 RANSAC 抽樣差異的影響，亦不能證明 frame 104 不可替代。
本次額外保存實際配對的配準診斷，以檢查 103→104→105 的情形。

## 比較與評估

同時呈現三組各自的 Mean L2、frame 數與保留率；另外在共同的原 179 張
上計算三組軌跡誤差，避免多評估 frame 104 本身造成平均值差異。
所有估計軌跡與 GT 都以 frame 1 為參考，不做額外軌跡擬合。
baseline 逐幀數值沿用先前已重現紀錄精度的診斷結果。

本輪記錄相同範圍的重建與總時間；總時間包含重建、評估、NPZ 與圖表，
不包含查詢、TTL 寫入與 dashboard 更新。baseline 原始時間仍為未保存。

## 保存與重現

此目錄是既有 sealed experiment 的獨立結果快照，Turtle 保留
`phase1_baseline.ttl` 與原 identity。原 baseline 及 179 張版本不修改。
先試跑、檢查結果，再寫入此目錄的 selected run。
已有結果時腳本會拒絕重新覆寫。

從 hw1 執行：

```bash
pixi run -e habitat python api.py query \
  experiments/phase1_depth_icp_add104/phase1_baseline.ttl \
  --query-file experiments/phase1_depth_icp_add104/queries/conservative_depth_icp_add104.rq

pixi run -e habitat python experiments/phase1_depth_icp_add104/analysis/run_selection.py

# 檢查已產生的結果後，僅寫入 run，不再重建
pixi run -e habitat python experiments/phase1_depth_icp_add104/analysis/run_selection.py --record

pixi run -e habitat python api.py explore \
  experiments/phase1_depth_icp_add104/phase1_baseline.ttl
```
