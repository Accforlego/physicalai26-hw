import sys
from pathlib import Path
sys.path.insert(0,'/home/wmnet/Documents/GitHub/physicalai26-hw/hw1')
import utils
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('/home/wmnet/Documents/GitHub/physicalai26-hw/hw1'); out=Path(__file__).resolve().parent
if '--reuse' in sys.argv:
 z=np.load(out/'trajectory_diagnostic.npz');pred=z['pred'];gt=z['gt'];err=z['error'];n=z['frames']
else:
 _,pred=utils.reconstruct(str(root/'eval/first_floor'),build_cloud=False,verbose=False,voxel_size=.05,registration_seed=0)
 pred=pred@utils.CAM_TO_GT_AXES
 gt=np.load(root/'eval/first_floor/GT_pose.npy'); R=Rotation.from_quat(gt[0,[4,5,6,3]]).as_matrix(); gt=(gt[:,:3]-gt[0,:3])@R
 err=np.linalg.norm(pred-gt,axis=1); n=np.arange(1,len(err)+1)
 np.savez(out/'trajectory_diagnostic.npz',pred=pred,gt=gt,error=err,frames=n)
print('DIAGNOSTIC MeanL2',err.mean(),'max',err.max(),'max_frame',err.argmax()+1,flush=True)
fig,axs=plt.subplots(1,2,figsize=(14,6))
axs[0].plot(gt[:,0],gt[:,2],c='black',lw=2,label='GT');axs[0].plot(pred[:,0],pred[:,2],c='red',lw=1,label='Estimated (diagnostic rerun)')
for i in [55,80,104,114,120,151]:
 axs[0].scatter(pred[i-1,0],pred[i-1,2],s=15,c='red');axs[0].annotate(str(i),(pred[i-1,0],pred[i-1,2]),xytext=((-30,-16) if i==104 else (5,6)),textcoords='offset points')
axs[0].set_aspect('equal');axs[0].set_xlabel('First-camera X (m)');axs[0].set_ylabel('First-camera Z (m)');axs[0].legend(loc='lower left',fontsize=8);axs[0].grid(alpha=.2)
axs[1].plot(n,err*100,color='purple');axs[1].set_xlabel('Frame index');axs[1].set_ylabel('Position L2 error (cm)');axs[1].grid(alpha=.2)
for lo,hi,c in [(50,60,'gold'),(70,99,'skyblue'),(100,114,'salmon'),(115,130,'lightgreen')]:axs[1].axvspan(lo,hi,color=c,alpha=.25)
fig.suptitle(f'Diagnostic rerun: voxel=0.05 m, seed=0, Open3D | Mean L2={err.mean():.6f} m\nSeparate from sealed baseline; no pose fitting to GT')
fig.tight_layout();fig.savefig(out/'trajectory_diagnostic.png',dpi=150)
for lo,hi in [(1,49),(50,60),(61,69),(70,99),(100,114),(115,130),(131,191)]:
 e=err[lo-1:hi];print(f'{lo}-{hi}: mean_error={e.mean():.6f} max_error={e.max():.6f}',flush=True)
