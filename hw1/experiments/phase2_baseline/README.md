# Phase 2 二樓 baseline：API 自動導航採集

正式資料目錄：`eval/_data/second_floor/115062519_api/`。
本次經使用者選擇，以 Habitat API 實際導航採集，不是手動鍵盤採集，
也不是逐幀 teleport replay。共 281 張 RGB-D、463 個導航動作，7 個
目標點皆成功到達。舊的空白手動採集目錄沒有覆寫。

重建採完整保留影格的原設定：voxel size 0.05 m、Open3D、seed 0。

**本次 Mean L2 = 5.8823 m，重建品質不佳，保留作為 first-pass evidence。**
近距離牆面主導的視角出現配準歧義；詳見 `analysis/findings.md` 與
`analysis/failure_views.png`。採集動作與資料保存已驗證正常。

## 正式資料與驗證

| 項目 | 實測 |
|---|---:|
| RGB／depth／GT | 各 281 筆、一一對應 |
| 解析度／HFOV | 512 × 512／90° |
| depth 格式 | uint16，毫米 |
| 相鄰拍攝最大平移 | 0.2185 m |
| 相鄰拍攝最大轉角 | 12.00° |
| benign／moderate／severe／outside | 30／52／16／183 張 |

`capture_metadata.json` 與 `action_trace.json` 保存在 capture 目錄。
導航使用 NavMesh 與 greedy follower，目標包含三個品質區域，以及
同一可行走連通區中四個分散的覆蓋目標。只在起始時將 agent 放到
設定位置附近的可行走點，之後用原本 0.2 m 移動、6° 轉向的動作逐步導航。
相機與深度設定、uncertainty zones 皆沿用 second_floor.yaml。
每次前進、每兩次轉向及到達目標時保存觀測；使用 action_index/30
的確定性模擬時鐘，不假稱為人工操作的實際牆鐘時間。

正式重建不使用導航目標或 GT 作為配準輸入。GT 僅用於事後評估。

主要檔案：

- `analysis/capture_validation.json`：採集完整性、深度格式、影格連續性。
- `analysis/capture_overview.png`、`analysis/capture_route.png`：輸入影像與路線。
- `phase2_baseline.ttl`：新宣告、完整 pipeline 量測與 baseline run。
- `analysis/results.json`、`analysis/baseline_results.csv`：評估與時間。
- `analysis/trajectory.npz`：估計位置、GT、逐幀誤差與完整估計變換矩陣。
- `analysis/pair_diagnostics.json`：實際相鄰配準的診斷與相對變換。
- `reconstruction_baseline.png`：去天花板俯視圖，估計紅線、GT 黑線。

## 重現 API 採集

從 hw1 使用新的輸出路徑，避免覆寫正式資料：

```bash
pixi run -e habitat python collect_api.py \
  --config configs/second_floor.yaml \
  --output-root eval/_data/second_floor/115062519_api_new
```

程式拒絕覆寫既有資料夾，逐張保存 GT 並記錄實際動作。

## 手動採集的備用方法

從 hw1 啟動，沿用原始 second_floor.yaml 的感測器與 uncertainty 設定：

```bash
pixi run -e habitat python load.py \
  --config configs/second_floor.yaml \
  --output-root eval/_data/second_floor/115062519
```

- W/S：前後移動；A/D：轉向。
- C 或空白鍵：保存 RGB-D 影格。
- Q 或 Escape：正常結束並保存 GT_pose.npy。
- 路線涵蓋主要房間、走道與角落，相鄰視角保持重疊，轉彎時分段拍攝。
- 記錄路線與採集影格數；不直接強制終止程式，以免缺少最終 GT 檔案。
- collector 預設會清理輸出目錄；已有採集資料後，不直接重新啟動覆寫。

## 重建設定

完整保留二樓採集影格，Open3D、voxel size 0.05 m、seed 0。
法向量半徑 0.10 m、FPFH 半徑 0.25 m、RANSAC／ICP 門檻 0.075 m。
相機 intrinsics 使用本次 capture 的 intrinsics.json，不沿用一樓參數假設。
GT 僅用於評估，不輸入重建。

本次已確認資料完整並建立事前宣告；若要重新做新實驗，請換新名稱。
對新資料宣告與執行的一般流程為：

```bash
pixi run -e habitat python api.py declare \
  --name phase2_baseline \
  --data-dir eval/_data/second_floor/115062519_api --floor 2

# 首次重建前先填寫宣告的 label 與 PREDICTION；不在量測後補寫假設。
pixi run -e habitat python reconstruct.py \
  --experiment experiments/phase2_baseline \
  --voxel-size 0.05 --seed 0 --version open3d --no-vis

pixi run -e habitat python api.py explore experiments/phase2_baseline
```

原一樓的四組實驗保持獨立，不會被這個二樓實驗覆蓋。

本次分析腳本會另存軌跡與配準診斷：

```bash
pixi run -e habitat python experiments/phase2_baseline/analysis/run_baseline.py
# 檢視結果後只封存既有量測，不再次重建
pixi run -e habitat python experiments/phase2_baseline/analysis/run_baseline.py --record
```

已有結果或 sealed 實驗時會拒絕重跑覆寫。
