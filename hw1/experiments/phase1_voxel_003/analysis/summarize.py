"""Summarize the completed voxel treatment without rerunning reconstruction."""
from pathlib import Path
import json
import sys
import re

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import api
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

out = Path(__file__).resolve().parent
results = json.loads((out / "results.json").read_text())
records = json.loads((out / "pipeline_measurements.json").read_text())
new = {}
for key, value in records["frame"] + records["pair"]:
    new.setdefault(key[0], {})[int(key[-1])] = value["value"]
ref = api.read_experiment(str(ROOT / "experiments/phase1_baseline/phase1_baseline.ttl"))
g = ref["graph"]; h = api.HW1
old = {}
for name in new:
    old[name] = {int(str(g.value(o, h.hasCurrentFrame)).rsplit("/", 1)[-1]):
                 float(g.value(o, h.value)) for o in g.subjects(h.hasDefinition, h[name])}
assert new["RawPointCount"] == old["RawPointCount"]
z = np.load(out / "trajectory.npz")
reference = np.load(ROOT / "experiments/phase1_baseline/analysis/trajectory_diagnostic.npz")
increment = np.diff(z["error"])
jump_row = int(increment.argmax()) + 1
relative = results["mean_l2_m"] / results["reference_mean_l2_m"] - 1
summary = {
    "raw_point_counts_identical": True,
    "relative_mean_l2_change": relative,
    "voxelized_point_count_ratio": results["mean_voxelized_points"] / results["reference_mean_voxelized_points"],
    "largest_error_increase_frame": int(z["frames"][jump_row]),
    "largest_error_increase_m": float(increment.max()),
    "zero_ransac_correspondence_pairs": [i for i,v in new["CoarseRANSACCorrespondences"].items() if v==0],
    "zero_icp_correspondence_pairs": [i for i,v in new["ICPInlierCorrespondences"].items() if v==0],
}
(out / "factor_summary.json").write_text(json.dumps(summary, indent=2)+"\n")

names = ["VoxelizedPointYield", "CoarseRANSACFitness", "ICPInlierFitness", "ICPInlierRMSE"]
fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
for ax, name in zip(axes, names):
    for values, color, label in [(old[name], "steelblue", "0.05 m"),
                                  (new[name], "red", "0.03 m")]:
        x = sorted(values)
        ax.plot(x, [values[i] for i in x], color=color, lw=1, label=label)
    ax.set_ylabel(name, fontsize=9); ax.grid(alpha=0.2)
axes[0].legend()
axes[-1].set_xlabel("Current original frame index (pair factors describe previous -> current)")
fig.suptitle("Fresh pipeline factors | distance gates differ: 0.075 m vs 0.045 m\nLower inlier RMSE or different fitness alone does not establish better camera poses")
fig.tight_layout(); fig.savefig(out / "factor_comparison.png", dpi=150); plt.close(fig)

change = f"降低 {abs(relative)*100:.2f}%" if relative < 0 else f"增加 {relative*100:.2f}%"
text = f"""# Voxel size 0.03 m：結果與討論

本次完整保留原始 191 張，將 voxel size 由 0.05 m 改為 0.03 m，
沿用程式既有的尺度連動方式，Open3D backend 與 seed 0 保持一致。
完整資料的 Mean L2 {change}。

| 項目 | 原 baseline | 本輪 |
|---|---:|---:|
| 觀測數 | 191 | 191 |
| Mean L2 | {results['reference_mean_l2_m']*100:.3f} cm | {results['mean_l2_m']*100:.3f} cm |
| Voxel size | 0.05 m | 0.03 m |
| 平均 VoxelizedPointYield | {results['reference_mean_voxelized_points']:.1f} | {results['mean_voxelized_points']:.1f} |
| 法向量搜尋半徑 | 0.10 m | 0.06 m |
| FPFH 搜尋半徑 | 0.25 m | 0.15 m |
| RANSAC／ICP 距離門檻 | 0.075 m | 0.045 m |
| 本次重建時間 | 原始紀錄未保存 | {results['reconstruction_seconds']:.2f} s |
| 本次總時間 | 原始紀錄未保存 | {results['total_seconds']:.2f} s |

兩者評估相同的 191 張，沒有選擇性排除難評估影格，也沒有額外做軌跡擬合。
所有 RawPointCount 與原始紀錄逐幀一致。平均 voxel 點數為原本的
{summary['voxelized_point_count_ratio']:.2f} 倍；較多點數不保證姿態估計更準。
本次完整量測 382 筆 frame 因子及 1140 筆 pair 因子，共 1522 筆新證據。

## 軌跡與因子

最大位置誤差為 {results['max_l2_m']*100:.3f} cm，出現在 frame {results['max_error_frame']}。
逐幀位置誤差最大增幅出現在 frame {summary['largest_error_increase_frame']}，
增幅約 {summary['largest_error_increase_m']*100:.3f} cm；這是定位調查區段的線索，
不是單憑該數值就能判定唯一原因。

| 區段 | 原 baseline 平均位置誤差 | 0.03 m 平均位置誤差 |
|---|---:|---:|
"""
for lo, hi in [(1,49), (50,60), (61,69), (70,99), (100,114), (115,130), (131,191)]:
    a = reference["error"][lo-1:hi].mean()*100
    b = z["error"][lo-1:hi].mean()*100
    text += f"| {lo}–{hi} | {a:.3f} cm | {b:.3f} cm |\n"
text += f"""
RANSAC 零 correspondence 的 current frames：{summary['zero_ransac_correspondence_pairs']}。
ICP 零 correspondence 的 current frames：{summary['zero_icp_correspondence_pairs']}。

`factor_comparison.png` 顯示重新量測的因子時間軸。新的 correspondence
門檻較小，因此兩次的 fitness、correspondence 數與 inlier RMSE 是在不同
接受範圍內計算，不能直接將其中一項變小解釋為重建改善。
本輪同時改變點數、法向量／FPFH 搜尋尺度與配對門檻，單次結果無法將
全部差異唯一歸因於 voxel 數量或某個半徑。此結論也不代表所有其他
voxel 設定的結果；本輪沒有再依結果追加參數掃描。

## 圖像與保存

`reconstruction_voxel_003.png` 是去天花板後的俯視圖，紅色為估計軌跡，
黑色為 GT。圖形顯示時才使用 0.04 m 顯示下採樣，不影響重建或分數。
原 baseline 舊重建圖與本圖視角不同，無 GT mesh completeness 指標，
不把圖上的可見面積當作量化覆蓋率。

`voxel_comparison.png` 在相同座標系比較完整軌跡與逐幀誤差。
原三組實驗保持不變；新設定以獨立宣告與新量測封存為 full-batch run。
本輪的 full-batch run 在新實驗內稱 baseline，與原始 phase1_baseline
是不同 experiment identity，不代表已覆寫原始分數。
"""
text += "\n## 失敗區段的進一步核對\n\n"
text += "| Frame | 位置誤差 | 與前張的估計位移 | GT 位移 |\n|---|---:|---:|---:|\n"
for frame in [103, 104, 105, 106, 160]:
    row = frame-1
    step = np.linalg.norm(z["pred"][row]-z["pred"][row-1])
    gt_step = np.linalg.norm(z["gt"][row]-z["gt"][row-1])
    text += f"| {frame} | {z['error'][row]:.4f} m | {step:.4f} m | {gt_step:.4f} m |\n"
text += """
103→104 的 GT 平移為零，卻出現約 3.447 m 的估計平移。
104→105 又出現約 3.433 m 的估計平移，位置誤差部分回落，但後續
仍有明顯累積偏離。這顯示本次不只是一般小幅漂移，而是包含明顯配準錯誤。
frame 104 的 ICP fitness 約 0.620、inlier RMSE 約 0.0203 m；
inlier RMSE 比原設定低，不代表估計相機位置正確。
本次重建圖可見錯位的房間輪廓與明顯偏離 GT 的估計軌跡。

因此本輪假設未獲支持：更多 voxel 點數與較小匹配尺度未帶來更準的
整體軌跡。目前四組已完成實驗中仍以 0.05 m 的完整 baseline 表現最好。
這只否定本次 0.03 m 連動設定的改善效果，不代表所有 voxel 調整都無效。
"""
(out / "findings.md").write_text(text)
log = out / "run.log"
log.write_text(re.sub(r"\x1b\[[0-9;]*m", "", log.read_text()))
print(json.dumps(summary, indent=2))
