# Phase 1：完整資料的 voxel size 介入

## 實驗前假設

前兩輪篩選顯示，刪除觀測可能破壞轉向區段的配準銜接。
本輪完整保留原始 191 張 RGB-D，測試 voxel size 由 0.05 m 縮小為
0.03 m 後，更細的幾何表示是否能改善軌跡。
較細的 voxel 也可能保留更多雜訊、增加計算量或降低局部幾何支撐，
因此不預設介入一定成功，不依觀測到的 GT 誤差事後改動參數。

## 固定與連動設定

| 項目 | 原 baseline | 本輪 |
|---|---:|---:|
| RGB-D 觀測數 | 191 | 191 |
| Voxel size | 0.05 m | 0.03 m |
| 法向量搜尋半徑（2 × voxel） | 0.10 m | 0.06 m |
| FPFH 搜尋半徑（5 × voxel） | 0.25 m | 0.15 m |
| RANSAC／ICP 配對距離門檻（1.5 × voxel） | 0.075 m | 0.045 m |
| RANSAC seed | 0 | 0 |
| ICP backend | Open3D point-to-plane | 相同 |
| 法向量／FPFH max_nn | 30／100 | 相同 |
| RANSAC max iterations／confidence | 100000／0.999 | 相同 |
| ICP max iterations | 100 | 相同 |

本次是「voxel size 與既有程式中連動尺度」的比較，不是把所有搜尋
半徑與門檻固定不動、只改點雲數量的實驗。較小門檻下的 inlier RMSE
與 fitness 不應直接跨設定判定優劣；不同設定可能接受不同的對應點。
點數保留較多也不等於新的資訊較多或姿態一定比較準確。

## 證據與評估

本次建立新宣告 phase1_voxel_003，事前預期與實際 CLI 設定註記在宣告
中，在重建前完成。現有 ontology 沒有 voxelSize 設定欄位，因此不加入
未定義的 RDF 設定；實際尺度另保存於 sealed 宣告註解、腳本與 results.json。

使用相同 utils.reconstruct 和 api 的 measurement callback，重新量測
191 張的 382 筆 frame 因子與 190 組相鄰影格的 1140 筆 pair 因子，
共 1522 筆。這些數值不複製自 0.05 m 的原實驗。
原始 RawPointCount 應相同；VoxelizedPointYield 預期增加。

重建完成後才載入 GT，將 GT 和估計相機位置轉到共同第一張參考系，
不做額外軌跡 fitting。逐幀誤差的自行計算須與作業 evaluator 一致。
以相同 191 張比較 Mean L2，另檢查重建圖是否有明顯錯位或重影。
本次沒有 mesh-based completeness 指標，不用不同視角的圖面積當作覆蓋率。

記錄本次重建時間與總時間；總時間包含新因子量測、重建、評估、NPZ
與圖表輸出，排除宣告、TTL 封存與 dashboard 更新。原 baseline 時間
未保存，不能由此聲稱速度提升或精確的 runtime 差異。

## 保存與重現

本輪使用新的實驗 identity 與目錄，不更動前三組實驗。
檢查結果後，以 api.seal_experiment 封存新的量測並寫入 full-batch
baseline run；此處的 baseline 是新 voxel 設定下的完整資料 run，
不會覆寫 phase1_baseline，也不會假造一個未篩選卻叫 selected 的 run。

從 hw1 執行：

```bash
# 先試跑並產生新量測、軌跡、圖表與數值
pixi run -e habitat python experiments/phase1_voxel_003/analysis/run_voxel_experiment.py

# 檢查後封存已保存的實際量測，不再次重建
pixi run -e habitat python experiments/phase1_voxel_003/analysis/run_voxel_experiment.py --record

pixi run -e habitat python api.py explore experiments/phase1_voxel_003
```

相同重建處理也可使用作業 CLI 的 --voxel-size 0.03 --seed 0 執行；
請以新名稱建立宣告，避免重跑覆寫既有結果。
