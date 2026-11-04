# Phase 2 API 採集與原設定 baseline

## 採集結果

經使用者選擇，透過 Habitat API 自動導航，執行 463 個離散動作，
採集 281 組 RGB-D 與 281 筆相機 GT。7 個目標皆成功到達，無導航失敗。
此為實際 action stepping，不是人工鍵盤採集，也不是逐幀 teleport replay。
起始點先貼合原設定附近的可行走 NavMesh；之後沒有以跳轉代替導航。

正式資料：eval/_data/second_floor/115062519_api。
RGB、depth 與 GT 已一一核對；影像 512×512、HFOV 90°、depth 為 uint16 毫米。
相鄰拍攝最大平移 0.2185 m、最大轉角
12.0000°。benign／moderate／severe／outside
分別為 30／52／16／183 張。感測器與品質區域配置沿用 second_floor.yaml。
觀測使用 action_index/30 的確定性時鐘，與人工拍攝的牆鐘時間不同。

導航使用現成 NavMesh 規劃路線；重建不讀取 NavMesh、導航目標或 GT。
GT 只用於重建後的軌跡評估與失敗診斷。路線的隨機 NavMesh 採樣支撐比例
只是導航路線的範圍參考，不是重建 map completeness 或作業評分指標。

## 原設定重建結果

| 項目 | 結果 |
|---|---:|
| Frame 數／保留率 | 281／100% |
| Voxel size | 0.05 m |
| ICP／RANSAC seed | Open3D point-to-plane／0 |
| 法向量／FPFH 半徑 | 0.10／0.25 m |
| RANSAC／ICP 配對門檻 | 0.075 m |
| Mean L2 | 5.882325 m |
| 最大位置誤差 | 12.497798 m，frame 187 |
| 重建時間 | 211.93 s |
| 總時間 | 215.06 s |

總時間包含重建、因子、配準診斷、評估與圖像／NPZ 輸出，不含採集、宣告、
TTL 寫入及 dashboard 更新。本次量測 562 筆 frame 因子、1680 筆 pair 因子，
共 2242 筆。課程 evaluator 與自行計算的逐幀 Mean L2 一致。

重建圖中的紅色估計軌跡明顯偏離黑色 GT，多個房間輪廓發生錯位。
因此這個 baseline 是品質不佳的真實測試結果，不能當作成功地圖。
與一樓的觀測、路線及拍攝方式不同，不把兩個分數直接當作單一參數比較。

## 第一個值得檢查的問題：近距離平面影像

- frame 35 位置誤差首次超過 0.1 m，約 0.333 m；voxel 點數僅 729。
- 38→39 的相對旋轉誤差接近 180°，但 ICP fitness 仍達 0.981。
- frame 39 的 voxel 點數僅 783；frame 42 僅 800。
- 原始 RGB-D 圖顯示這幾張幾乎只看到近距離牆面，幾何結構缺乏變化。
- 96→97 也出現接近 180° 的相對旋轉誤差，且該區段有品質區域擾動。

`failure_views.png` 與 `failure_diagnosis.json` 支持「部分自動目標點太貼近
牆面，使平面主導的點雲產生配準歧義」的假設；不將全部誤差只歸因於
單一因子。fitness 高或 inlier RMSE 低都不是相機姿態正確的充分條件。

後續可把本次當作二樓的 first-pass evidence，另建資料採集介入，讓
轉向位置遠離牆面、盡量看到轉角或家具，保留足夠視角重疊，再比較結果。
本次不事後改動原 baseline、不把失敗影格刪掉後假稱同一次執行成功。

## 可重現與保存

- collect_api.py：自動導航採集，拒絕覆寫既有目錄，逐張保存 GT。
- capture_metadata.json／action_trace.json：正式資料目錄內的配置、路線與動作。
- analysis/run_baseline.py：完整 0.05 m baseline，另存因子、估計矩陣與分數。
- analysis/trajectory.npz／pair_diagnostics.json：逐幀與逐配對診斷。
- phase2_baseline.ttl：本次獨立 experiment identity 與封存量測。
- reconstruction_baseline.png：去天花板俯視圖。

前四組一樓實驗保持不變。
