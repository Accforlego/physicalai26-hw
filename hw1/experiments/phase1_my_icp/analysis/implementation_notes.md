# 自製 ICP 的實作與本次控制條件

使用既有 `utils.my_local_icp_algorithm`，本次沒有修改演算法。

1. 以 RANSAC 的 4×4 變換作為初始姿態。
2. 建立目標點雲的 SciPy cKDTree；每次迭代將來源點轉換後找最近鄰。
3. 對應點距離需小於 voxel × 1.5 = 0.075 m，且目標法向量有限。
4. 對每對點建立 point-to-plane 殘差 n·(p−q)，Jacobian 為 [p×n, n]。
5. 使用 NumPy least squares 求出旋轉向量與平移增量，左乘更新變換。
6. 最多 60 次迭代；平均絕對殘差變化或增量範數小於 1e-6 時停止，
   少於 10 對可用對應點時停止。最後重新計算 fitness 與 Euclidean inlier RMSE。

它沒有呼叫 Open3D registration_icp，但仍使用 NumPy／SciPy 的矩陣求解、
最近鄰與旋轉運算。點雲下採樣、法向量、FPFH 與 RANSAC 繼續使用原流程。
預處理已提供半徑 0.10 m 的法向量，所以自製函式的缺少法向量 fallback
在本次正常路徑不會啟動。

Open3D 參照使用 point-to-plane ICP，最多 100 次迭代，其餘收斂條件維持
Open3D 預設。兩者皆使用原始 191 張、voxel 0.05 m、seed 0、FPFH 半徑
0.25 m、配準門檻 0.075 m。沒有篩選、深度遮罩或額外 GT 對齊。

這比較的是兩個現有 backend 的行為，並未強制統一迭代數與停止條件。
兩次完整流程依序執行，OMP_NUM_THREADS=8，避免同時重建互相競爭資源。
重建時間包含反投影、特徵、RANSAC、ICP 與合併點雲，不是獨立 ICP 函式耗時。
兩組均另量測 pipeline 因子，計時範圍一致。

每組單次量測，不用於估計統計變異，也未調整參數後挑選較佳結果。
GT 僅在重建結束後用於分數、軌跡及相對姿態診斷。
新 Open3D 參照另行保存，舊 baseline 結果及全部原始資料不變。
