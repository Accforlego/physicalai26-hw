from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from rdflib import Graph, Namespace
root=Path('/home/wmnet/Documents/GitHub/physicalai26-hw/hw1')
out=Path(__file__).resolve().parent
g=Graph().parse(root/'experiments/phase1_baseline/phase1_baseline.ttl'); h=Namespace('http://taica.course/hw1/ontology#')
data={}
for name in ['RawPointCount','VoxelizedPointYield','ICPInlierFitness','ICPInlierRMSE']:
 data[name]={int(str(g.value(o,h.hasCurrentFrame)).rsplit('/',1)[-1]):float(g.value(o,h.value)) for o in g.subjects(h.hasDefinition,h[name])}
fig,axs=plt.subplots(4,1,figsize=(12,9),sharex=True)
for ax,(name,d) in zip(axs,data.items()):
 x=sorted(d);ax.plot(x,[d[i] for i in x],lw=1.3)
 for lo,hi,c in [(50,60,'gold'),(70,99,'skyblue'),(100,114,'salmon'),(115,130,'lightgreen')]:ax.axvspan(lo,hi,color=c,alpha=.25)
 ax.set_ylabel(name,fontsize=9);ax.grid(alpha=.25)
 if name=='RawPointCount':ax.axhline(262144,ls='--',color='gray',lw=1)
axs[-1].set_xlabel('Current frame index (pair metrics refer to previous -> current frame)')
fig.suptitle('Recorded baseline factors | yellow 50-60 / blue 70-99 / red 100-114 / green 115-130')
fig.tight_layout();fig.savefig(out/'factor_comparison.png',dpi=150);plt.close(fig)
frames=[49,55,65,80,104,114,120,135]
fig,axs=plt.subplots(3,len(frames),figsize=(20,8))
cmap=plt.get_cmap('viridis').copy();cmap.set_bad('magenta')
for col,i in enumerate(frames):
 rgb=np.asarray(Image.open(root/f'eval/first_floor/rgb/{i}.png'))
 dep=np.asarray(Image.open(root/f'eval/first_floor/depth/{i}.png'));invalid=dep==0
 count=int(np.count_nonzero(dep));assert count==data['RawPointCount'][i]
 axs[0,col].imshow(rgb);axs[0,col].set_title(f'Frame {i}\nvalid {100*(~invalid).mean():.1f}%')
 axs[1,col].imshow(np.ma.masked_equal(dep.astype(float)/1000,0),vmin=0,vmax=8,cmap=cmap,interpolation='nearest')
 axs[2,col].imshow(invalid,cmap='gray',vmin=0,vmax=1,interpolation='nearest')
 print(f'frame {i}: invalid={invalid.mean()*100:.2f}% raw={count} voxel={data["VoxelizedPointYield"][i]:.0f} fitness={data["ICPInlierFitness"].get(i,0):.5f} rmse={data["ICPInlierRMSE"].get(i,0):.5f}')
 for ax in axs[:,col]:ax.set_xticks([]);ax.set_yticks([])
for ax,label in zip(axs[:,0],['RGB','Depth (0-8 m)\nmagenta = invalid','Invalid mask\nwhite = zero depth']):ax.set_ylabel(label)
fig.tight_layout();fig.savefig(out/'rgb_depth_comparison.png',dpi=140);plt.close(fig)
# Full-sequence check: sealed RawPointCount values must equal positive depth-pixel counts.
for i,v in data['RawPointCount'].items():
 dep=np.asarray(Image.open(root/f'eval/first_floor/depth/{i}.png'))
 assert np.count_nonzero(dep)==v,(i,v)
print('All 191 depth images match recorded RawPointCount.')
# Associate flagged frames with the capture route, without estimating a new trajectory.
gt=np.load(root/'eval/first_floor/GT_pose.npy')
fig,ax=plt.subplots(figsize=(8,7));ax.plot(gt[:,0],gt[:,2],c='.65',lw=2,label='GT capture route')
for lo,hi,c in [(50,60,'goldenrod'),(70,99,'steelblue'),(100,114,'firebrick'),(115,130,'forestgreen')]:
 ax.plot(gt[lo-1:hi,0],gt[lo-1:hi,2],lw=3,c=c,label=f'Frames {lo}-{hi}')
for i in frames:
 ax.scatter(gt[i-1,0],gt[i-1,2],c='black',s=12)
 ax.annotate(str(i),(gt[i-1,0],gt[i-1,2]),xytext=((-30,-15) if i==104 else (5,6)),textcoords='offset points',fontsize=9)
ax.set_aspect('equal');ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.legend();ax.grid(alpha=.2)
ax.set_title('Flagged frame locations on GT route (evaluation reference only)')
fig.tight_layout();fig.savefig(out/'flagged_gt_route.png',dpi=150);plt.close(fig)
