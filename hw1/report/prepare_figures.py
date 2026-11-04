"""Render report figures from saved measurements; never rerun reconstruction."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from rdflib import Graph, Namespace
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / 'assets'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 9, 'axes.labelsize': 9, 'legend.fontsize': 8})
H = Namespace('http://taica.course/hw1/ontology#')
sources = set()


def factors(path):
    sources.add(path)
    g = Graph().parse(path)
    result = {}
    for name in ['RawPointCount', 'VoxelizedPointYield', 'ICPInlierFitness', 'ICPInlierRMSE']:
        result[name] = {int(str(g.value(o, H.hasCurrentFrame)).rsplit('/', 1)[-1]): float(g.value(o, H.value))
                        for o in g.subjects(H.hasDefinition, H[name])}
    return result


def factor_plot(path, filename, phase2=False):
    values = factors(path)
    fig, axes = plt.subplots(4, 1, figsize=(8.2, 4.25), sharex=True)
    labels = ['Raw points', 'Voxel points', 'ICP fitness', 'ICP RMSE (m)']
    for ax, (name, data), label in zip(axes, values.items(), labels):
        x = sorted(data)
        ax.plot(x, [data[i] for i in x], color='#225d85', lw=1.0)
        if phase2:
            for frame in [311, 313, 350]: ax.axvline(frame, color='#bd413b', alpha=.6, lw=.8)
        else:
            for lo, hi, color in [(50,60,'#f4d786'),(70,99,'#bcd8eb'),(100,114,'#efbbb6'),(115,130,'#c7dfc2')]:
                ax.axvspan(lo, hi, color=color, alpha=.65)
        ax.set_ylabel(label); ax.grid(alpha=.18); ax.tick_params(labelsize=8)
        if 'points' in label: ax.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    axes[-1].set_xlabel('Current frame index (pair metrics: previous -> current)')
    fig.tight_layout(h_pad=.25); fig.savefig(OUT / filename, dpi=200); plt.close(fig)


factor_plot(ROOT/'experiments/phase1_baseline/phase1_baseline.ttl', 'phase1_factors.png')
factor_plot(ROOT/'experiments/phase2_manual_baseline/phase2_manual_baseline.ttl', 'phase2_factors.png', True)

fig, axes = plt.subplots(2,4,figsize=(8.2,3.65))
cmap = plt.get_cmap('viridis').copy(); cmap.set_bad('#d12d9c')
for col, i in enumerate([65,104,114,120]):
    rp=ROOT/f'eval/first_floor/rgb/{i}.png';dp=ROOT/f'eval/first_floor/depth/{i}.png'
    rgb=np.asarray(Image.open(rp));d=np.asarray(Image.open(dp));sources.update([rp,dp])
    axes[0,col].imshow(rgb);axes[0,col].set_title(f'Frame {i}',fontsize=9)
    axes[1,col].imshow(np.ma.masked_equal(d/1000,0),cmap=cmap,vmin=0,vmax=8)
    axes[1,col].set_title(f'Invalid: {100*np.mean(d==0):.2f}%',fontsize=8)
    for row in range(2):axes[row,col].axis('off')
fig.tight_layout(pad=.2,h_pad=.4);fig.savefig(OUT/'depth_evidence.png',dpi=200);plt.close(fig)

# Replot only saved positions/errors; no map regeneration or pose fitting.
for filename, paths, labels in [
    ('phase1_sor_comparison.png', ['phase1_baseline/analysis/trajectory_diagnostic.npz','phase1_depth_sor/analysis/trajectory.npz'], ['Original baseline','Depth SOR']),
    ('phase2_selection_comparison.png',['phase2_manual_baseline/analysis/trajectory.npz','phase2_manual_depth_icp_selection/analysis/selected_trajectory.npz'],['Full baseline','Selected']),
    ('icp_comparison.png',['phase1_open3d_reference/analysis/trajectory.npz','phase1_my_icp/analysis/trajectory.npz'],['Fresh Open3D','Custom ICP'])]:
    trajectories=[]
    for path in paths:
        p=ROOT/'experiments'/path;sources.add(p);trajectories.append(np.load(p))
    fig, axes=plt.subplots(1,2,figsize=(8.2,3.25),gridspec_kw={'width_ratios':[1,1.6]})
    gt=trajectories[0]['gt'];axes[0].plot(gt[:,0],gt[:,2],color='black',lw=1.6,label='GT')
    for t,label,color in zip(trajectories,labels,['#225d85','#c63832']):
        axes[0].plot(t['pred'][:,0],t['pred'][:,2],color=color,lw=1,label=label)
        axes[1].plot(t['frames'],t['error']*100,color=color,lw=1,label=label)
    axes[0].set_aspect('equal');axes[0].set_xlabel('First-camera X (m)');axes[0].set_ylabel('First-camera Z (m)')
    axes[1].set_xlabel('Frame index');axes[1].set_ylabel('Position error (cm)')
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(OUT/filename,dpi=200);plt.close(fig)

for glob in ['experiments/**/analysis/results.json','experiments/**/analysis/*comparison.csv','experiments/**/analysis/*results.json']:
    sources.update(ROOT.glob(glob))
sources.update(ROOT.glob('experiments/**/reconstruction*.png'))
sources.update([ROOT/'experiments/phase2_manual_baseline/analysis/capture_route.png',
                ROOT/'experiments/phase2_manual_baseline/analysis/capture_validation.json',
                ROOT/'experiments/phase1_my_icp/analysis/paired_registration_diagnosis.json',
                ROOT/'experiments/phase1_my_icp/analysis/run_environment.json',
                ROOT/'HW1_3D Scene Reconstruction.pdf'])
sources.update([ROOT/'utils.py',ROOT/'reconstruct.py',ROOT/'api.py',ROOT/'ontology/hw1.ttl',ROOT/'configs/second_floor.yaml'])
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources) if p.is_file()}
(OUT.parent/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared six report figures and source hashes; no experiments modified.')
