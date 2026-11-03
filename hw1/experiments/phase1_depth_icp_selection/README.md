# 深度與 ICP 因子聯合篩選實驗

這是 3.2.4 的獨立結果快照，保留一次未改善的 frame-selection 實驗。
原本未篩選的實驗位於 `../phase1_baseline/`，不會被這個目錄的分析腳本修改。

| 結果 | Frame 數 | Mean L2 |
|---|---:|---:|
| baseline 參照 | 191 | 5.88 cm |
| depth + ICP selection | 179 | 30.50 cm |

主要檔案：

- `reconstruction_selected.png`：這次篩選後的重建圖。
- `reconstruction_baseline.png`：未篩選重建圖的參照副本。
- `analysis/intervention_comparison.png`：兩種軌跡與逐幀誤差比較。
- `analysis/intervention_findings.md`：中文結果與討論。
- `analysis/intervention_protocol.md`：規則、門檻、固定設定與重現方法。
- `queries/conservative_depth_icp.rq`：此策略的 SPARQL 查詢。
- `phase1_baseline/plots/`：`api.py explore` 依原 sealed identity 產生的本次圖表。
- `phase1_baseline.ttl`：原 sealed 實驗加上此 selected run 的完整快照。

## 為何 Turtle 仍叫 phase1_baseline.ttl？

這是既有實驗的結果快照，不是假裝重新宣告或重新量測的新實驗。
Turtle 內的 experiment IRI、檔案 stem 與 sealed 宣告必須相符；
直接改檔名或改 IRI 會破壞既有驗證。因此外層目錄用策略命名，
內層 Turtle 保留原始名稱，查詢中的 experiment IRI 也維持不變。
讀取時必須指定完整 Turtle 路徑，不能僅傳入外層目錄。

從 `hw1` 執行：

```bash
pixi run -e habitat python api.py explore \
  experiments/phase1_depth_icp_selection/phase1_baseline.ttl

pixi run -e habitat python api.py query \
  experiments/phase1_depth_icp_selection/phase1_baseline.ttl \
  --query-file experiments/phase1_depth_icp_selection/queries/conservative_depth_icp.rq
```

分析腳本會以自身所在目錄定位結果；偵測到既有結果時會拒絕重跑覆寫。
未來測試新策略應使用新的目錄／宣告，而非覆蓋這次結果。
