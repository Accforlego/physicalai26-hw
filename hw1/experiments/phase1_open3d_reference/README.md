# Phase 1 Open3D 新計時參照

為比較 `phase1_my_icp` 的準確度與完整重建耗時，使用相同量測腳本
補跑原始 191 張的 Open3D；舊 `phase1_baseline` 沒有修改。

voxel 0.05 m、seed 0、法向量半徑 0.10 m、FPFH 半徑 0.25 m、
配準距離 0.075 m，OMP_NUM_THREADS=8。無刪幀或深度濾波。

- Mean L2：0.291071 m；最大 0.649890 m。
- 重建：152.23 s；含量測、診斷、評估與 PNG/NPZ 輸出：154.13 s。
- 191 張完整處理、1522 筆新 pipeline 因子，已封存。

本次沒有重現舊 baseline 0.058835 m，不能將這次計時掛在舊分數上。
與 my_icp 的實際 RANSAC 初始變換也有差異，所以比較是單次端到端流程，
不是固定所有輸入後的純 ICP benchmark。詳見
`../phase1_my_icp/README.md` 與該目錄的 `analysis/backend_comparison.csv`。

GT 僅用於事後評估。完整軌跡、診斷、量測、計時及環境紀錄均在 `analysis/`。
`phase1_open3d_reference.ttl` 使用新的 identity；圖表位於 `plots/`。
重建圖為 `reconstruction_baseline.png`。

從 hw1 執行 `experiments/phase1_open3d_reference/analysis/run_baseline.py`；
已有結果或已封存時會拒絕覆寫。新實驗必須另行宣告，重建前填寫預測。
