# 3.2.4 資料介入結果與討論

本次聯合 RawPointCount 與 ICP 因子的 frame selection **沒有改善重建**。
保留 179/191 張（93.72%）後，Mean L2 從 0.058835 m 增加至 0.305000 m。
因此保留原 baseline 作為目前較好的結果；selected run 是一次已完成的
假設驗證，不代表推薦的最終重建。

## 比較

| 執行／評估方式 | Frame 數 | Mean L2 | 重建時間 | 總時間 |
|---|---:|---:|---:|---:|
| 原 baseline | 191 | 5.883 cm | 未保存 | 未保存 |
| baseline 軌跡僅評估相同保留影格 | 179 | 5.790 cm | 未再次重建 | 未再次重建 |
| selected 重建 | 179 | 30.500 cm | 278.56 s | 280.44 s |

兩次重建皆使用 Open3D、voxel size 0.05 m、seed 0。
baseline 的逐幀誤差來自 3.2.3 診斷重跑，其平均值與 sealed baseline
的記錄精度一致。相同 179 張的 baseline 評估只是重新計算平均值，
不是拿這 179 張重跑 baseline，也沒有填補 selected 未重建的影格位置。
selected 在相同評估影格上的誤差約為 baseline 的 5.27 倍。
總時間的明確範圍見 intervention_protocol.md；兩者無可比較的原始
runtime 紀錄，因此不能聲稱這次實驗證明了加速。

## 篩選與配準銜接

規則：深度缺失 > 15%，且 fitness < 0.90 或 inlier RMSE > 0.025 m，
另保留第 1 張及每第 3 張影像作銜接。排除 12 張：
71、83、94、95、100、104、106、107、112、113、115、124。
共有 9 個缺口，最大缺口長度為 2 張。

逐幀位置顯示：

- frame 103 的 selected 位置誤差約 3.22 cm。
- 刪除 frame 104 之後，frame 105 直接對齊到 frame 103。
- GT 在 103 與 105 之間沒有位置變化，但估計相機中心移動了約 71.03 cm。
- frame 105 的位置誤差升至 71.71 cm，也是此次最大值。
- 後續保留影格仍帶著這個累積偏移；最終 Mean L2 約 30.50 cm。

這些結果支持新的配對 103→105 發生明顯對齊錯誤的解釋。
刪除資料改變了實際配準的 source/target；原始因子只描述原始相鄰
frame，並不能保證新的銜接 pair 好配準。就算最大只刪除連續 2 張，
轉向區段的可見幾何改變仍可能造成錯誤。
執行時也出現 mutual-filter correspondence 不足而 fallback 的警告；
原 baseline 診斷重跑亦曾有同類警告，因此警告本身不是失敗的充分條件，
此次 log 未逐一標記警告屬於哪個原始 frame，不能據此指定某個警告的因果。

## 地圖視覺檢查與限制

reconstruction_selected.png 顯示仍有多個房間與連通空間的點雲，
沒有因排除整個大區段而只剩一小部分樓層；但紅色估計軌跡在轉向後
與黑色 GT 明顯偏離，也可見部分牆緣的多層輪廓。
這張圖採用去天花板後的點雲俯視圖，軌跡畫在點雲上方以避免遮擋。
baseline 舊圖的視角不同且上緣被裁切，因此不將兩張圖的可見面積
當作量化的 coverage/completeness 比較。本次沒有 GT mesh completeness 指標。

## 可以放進報告的結論

低 RawPointCount 與弱 ICP 因子可用來定位值得調查的觀測，卻不足以
直接制定有效的刪除規則。本次保守聯合篩選保留 93.72% 的影格，
但新銜接 pair 在轉向區段產生明顯位置錯誤，使 Mean L2 惡化。
因此假設「刪除低品質觀測能改善重建」在本規則下未獲支持。
後續可另外宣告實驗，保留轉向區段的密集觀測，或檢查新銜接 pair
的配準品質後再決定是否跳過影格；本次不事後調整門檻以覆蓋負面結果。

## 產物

- queries/conservative_depth_icp.rq：可重現的篩選查詢。
- analysis/selection_plan.json、selected_frames.csv：查詢與缺口預覽。
- analysis/intervention_protocol.md：實驗假設、規則、固定設定與指令。
- analysis/intervention_results.json、intervention_comparison.csv：數值、時間。
- analysis/selected_trajectory.npz：179 張的估計位置、GT 與逐幀誤差。
- analysis/intervention_comparison.png：baseline／selected 軌跡與誤差。
- reconstruction_selected.png：selected 重建俯視圖。
- analysis/intervention_run.log：重建輸出；原始 baseline run 與因子不變。
