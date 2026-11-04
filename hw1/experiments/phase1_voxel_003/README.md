# 完整 191 張：voxel size 0.03 m

這次以新的 experiment identity `phase1_voxel_003`，測試 voxel size
及程式內的連動尺度，完整保留原始 RGB-D 觀測，不做 frame selection。
原 baseline 與兩組篩選實驗分開保存。

**結果：本輪 Mean L2 為 2.965 m，明顯劣於原 baseline 的 0.0588 m。**
平均 voxel 點數由約 19,944 增至 49,067（2.46 倍），但軌跡與地圖發生
明顯錯位；本輪耗時約 25.4 分鐘。完整保留資料並不保證更細 voxel 更準，
目前仍以原本 0.05 m 的 baseline 作為較佳結果。

| 設定 | 原 baseline | 本輪 |
|---|---:|---:|
| Frame 數 | 191 | 191 |
| Voxel size | 0.05 m | 0.03 m |
| 法向量半徑 | 0.10 m | 0.06 m |
| FPFH 半徑 | 0.25 m | 0.15 m |
| RANSAC／ICP 距離門檻 | 0.075 m | 0.045 m |
| RANSAC seed | 0 | 0 |
| ICP backend | Open3D point-to-plane | 相同 |

本輪重新量測全部 1522 筆 pipeline 因子，不沿用原設定的數值。
較小距離門檻下的 inlier RMSE／fitness 不代表可直接跨設定比較的
姿態準確度；以相同 191 張的 Mean L2 與重建圖作主要結果比較。
GT 僅用於重建後的評估，不用作配準輸入。

主要檔案：

- `phase1_voxel_003.ttl`：本次新宣告、重新量測與 full-batch run。
- `analysis/protocol.md`：事前假設、固定與連動設定、評估及重現指令。
- `analysis/results.json`、`analysis/voxel_comparison.csv`：分數、參數、點數與時間。
- `analysis/pipeline_measurements.json`：本次實際 frame／pair 因子。
- `analysis/trajectory.npz`：估計位置、GT 位置與逐幀誤差。
- `analysis/voxel_comparison.png`：相同影格的軌跡與誤差比較。
- `analysis/factor_comparison.png`：原設定與本輪新因子的時間軸。
- `analysis/findings.md`：中文結果與討論。
- `reconstruction_voxel_003.png`：去天花板的重建俯視圖。
- `plots/`：`api.py explore` 產生的互動圖表。

從 hw1 執行：

```bash
pixi run -e habitat python api.py explore experiments/phase1_voxel_003
```

本次沒有刪除影格，因此 full-batch run 在新實驗內以 baseline 模式
記錄；這不會覆寫原始 phase1_baseline 的 baseline。
腳本對既有結果與 sealed 實驗皆有防覆寫檢查；測試新設定請另立宣告。
