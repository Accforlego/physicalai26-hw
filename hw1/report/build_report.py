"""Build the English HW1 report from saved experiment records and figures.

Use the bundled PDF Python runtime (ReportLab, Pillow). Run prepare_figures.py
with the habitat environment first. This script never runs reconstruction.
"""
import csv
import html
import json
import os
import re
from pathlib import Path

from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
OUTPUT=ROOT/'output/pdf/report.pdf'
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
ASSETS=HERE/'assets'
FONT=Path('/usr/share/fonts/truetype/dejavu')
for name,file in [('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Italic','DejaVuSans-Oblique.ttf')]:
    font_path=FONT/file
    if not font_path.exists():
        font_path=ROOT/'.pixi/envs/habitat/lib/python3.9/site-packages/matplotlib/mpl-data/fonts/ttf'/file
    pdfmetrics.registerFont(TTFont(name,str(font_path)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')
W,H=A4; M=48; CW=W-2*M
NAVY=colors.HexColor('#193d56'); TEAL=colors.HexColor('#217987'); GRAY=colors.HexColor('#53616b')
body=ParagraphStyle('body',fontName='Body',fontSize=9.65,leading=13.8,textColor=colors.HexColor('#202c34'),spaceAfter=6)
small=ParagraphStyle('small',parent=body,fontSize=8.1,leading=11.1,textColor=GRAY)
caption=ParagraphStyle('caption',parent=small,fontSize=8,leading=10.7)
sub=ParagraphStyle('sub',parent=body,fontName='Bold',fontSize=11,leading=15,textColor=NAVY)
cell=ParagraphStyle('cell',parent=small,fontSize=8.1,leading=11,textColor=colors.HexColor('#202c34'))
headcell=ParagraphStyle('headcell',parent=cell,fontName='Bold',textColor=colors.white)
c=canvas.Canvas(str(OUTPUT),pagesize=A4)
c.setTitle('HW1 - 3D Scene Reconstruction | 115062519')
c.setAuthor('115062519')
c.setSubject('Evidence-driven RGB-D reconstruction, data interventions, and custom ICP comparison')
md=['# HW1: 3D Scene Reconstruction','Student ID: 115062519 | 4 November 2026','']
y=0; page_num=0


def plain(s):
    s=re.sub(r'<link href="([^"]+)"[^>]*>(.*?)</link>',r'[\2](\1)',s)
    return html.unescape(re.sub('<[^>]+>','',s))


def paragraph(text,style=body,gap=6):
    global y
    p=Paragraph(text,style);_,h=p.wrap(CW,1000)
    if y-h<57:raise RuntimeError(f'Page {page_num} overflow before: {plain(text)[:70]} (y={y:.1f}, h={h:.1f})')
    p.drawOn(c,M,y-h);y-=h+gap
    md.extend([plain(text),''])


def page(title,kicker):
    global y,page_num
    if page_num:
        if y<45:raise RuntimeError('Overflow')
        c.showPage()
    page_num+=1
    c.setStrokeColor(TEAL);c.setLineWidth(2);c.line(M,H-42,W-M,H-42)
    c.setFont('Bold',8);c.setFillColor(GRAY);c.drawString(M,H-29,'PHYSICAL AI / HW1')
    c.setFont('Body',8);c.drawRightString(W-M,H-29,'115062519')
    c.setFont('Bold',19);c.setFillColor(NAVY);c.drawString(M,H-76,title)
    c.setFont('Body',8.6);c.setFillColor(TEAL);c.drawString(M,H-94,kicker)
    c.setStrokeColor(colors.HexColor('#d8e1e7'));c.setLineWidth(.5);c.line(M,44,W-M,44)
    c.setFillColor(GRAY);c.setFont('Body',7.5);c.drawString(M,31,'3D Scene Reconstruction | 4 November 2026')
    c.drawRightString(W-M,31,f'{page_num} / 4')
    c.bookmarkPage(f'page{page_num}');c.addOutlineEntry(title,f'page{page_num}',0)
    y=H-115
    md.extend([f'## {title}',kicker,''])


def heading(text):paragraph(text,sub,gap=5)


def table(headers,rows,widths):
    global y
    data=[[Paragraph(str(x),headcell) for x in headers]]+[[Paragraph(str(x),cell) for x in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eef3f6'),colors.white]),
        ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#b7c6cf'))]))
    _,h=t.wrap(CW,1000)
    if y-h<57:raise RuntimeError(f'Table overflow page {page_num}')
    t.drawOn(c,M,y-h);y-=h+9
    md.extend(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |'])
    md.extend('| '+' | '.join(plain(str(x)) for x in row)+' |' for row in rows);md.append('')


def image(path,width=CW,maxheight=1000,cap=None):
    global y
    path=Path(path);iw,ih=PILImage.open(path).size;scale=min(width/iw,maxheight/ih);ww,hh=iw*scale,ih*scale
    if y-hh<57:raise RuntimeError(f'Image overflow page {page_num}: {path.name}')
    c.drawImage(str(path),M+(CW-ww)/2,y-hh,width=ww,height=hh,mask='auto');y-=hh+5
    md.extend([f'![{cap or path.stem}]({os.path.relpath(path,HERE)})',''])
    if cap:paragraph(cap,caption,gap=7)


def pair(left,right,cap):
    global y
    ww=(CW-12)/2;hh=ww
    if y-hh<57:raise RuntimeError(f'Pair overflow page {page_num}')
    for j,p in enumerate([left,right]):
        iw,ih=PILImage.open(p).size;s=min(ww/iw,hh/ih)
        c.drawImage(str(p),M+j*(ww+12)+(ww-iw*s)/2,y-ih*s,width=iw*s,height=ih*s,mask='auto')
        md.extend([f'![{Path(p).stem}]({os.path.relpath(p,HERE)})',''])
    y-=hh+5;paragraph(cap,caption,gap=7)


def j(name):return json.loads((ROOT/'experiments'/name/'analysis/results.json').read_text())


# Page 1
page('3D Scene Reconstruction','METHODS / DATA VERIFICATION')
paragraph('Reconstruct apartment_0 from RGB-D, inspect pipeline factors, and evaluate interventions. Phase 1 uses 191 provided frames; Phase 2 uses 351 manually captured frames. The main finding is that removing observations or points does not reliably improve alignment. Historical baselines achieve Mean L2 of 0.0588 m and 0.2407 m; reruns reveal sensitivity to execution conditions.')
heading('1. Pipeline and evaluation')
paragraph('Read each capture\'s intrinsics.json; convert uint16 depth from millimeters to meters and discard invalid depth. Implement pinhole unprojection directly, without Open3D\'s projection helper: f = W/[2 tan(HFOV/2)], c = (W/2,H/2), X = (u-cx)z/f, Y = (v-cy)z/f, Z = z. Downsample, estimate normals, compute FPFH, initialize current-to-previous alignment with RANSAC, and refine with point-to-plane ICP [2,3]. Chain transforms and merge clouds; no loop closure is used.')
table(['Shared setting','Value'],[
    ['Camera / voxel / normal / FPFH','512 x 512, HFOV 90 degrees / 0.05 / 0.10 / 0.25 m'],
    ['Normal / FPFH neighbors','max_nn = 30 / 100'],
    ['RANSAC','Mutual matching; 3-point samples; edge ratio 0.9; 0.075 m gate; max 100,000; confidence 0.999'],
    ['ICP / seed','0.075 m gate; max 100 iterations (Open3D); seed 0']
],[155,CW-155])
paragraph('Mean L2 = (1/N) sum ||p_est,i - p_GT,i||. Anchor GT at the first sensor pose and map image-camera axes with diag(1,-1,-1); do not fit an extra alignment. Evaluate the same retained frame IDs and preserve frame 1. Remove a 1 m ceiling band only from the merged display cloud. For RGB-D capture, skip semantic-mesh loading unless requested and initialize Habitat before pygame to avoid asset/GL conflicts.')
heading('2. Pipeline-grounded evidence')
paragraph('Record RawPointCount and VoxelizedPointYield per frame; record RANSAC and ICP fitness, inlier RMSE (m), and correspondence count per pair. Fitness is an inlier fraction, not a pose-accuracy guarantee [1-3]. This gives 2N + 6(N-1) occurrences: 1,522 for Phase 1 and 2,802 for the manual Phase 2 baseline. Declarations, sealed records and saved trajectories keep experiments separate.')
image(ASSETS/'phase1_factors.png',maxheight=160,cap='Figure 1. Phase 1 baseline factors. Shading: frames 50-60, 70-99, 100-114 and 115-130. Pair values at i describe i-1 to i. Raw counts match positive-depth pixels in all 191 images.')
paragraph('Frames 100-114 have mean raw support 215,269, ICP fitness 0.851 and RMSE 0.0249 m; the saved diagnostic trajectory reproduces the historical score and shows increased offset there. Yet frame 120 has 16.31% missing depth and fitness 0.9983. Missing depth, turns and visible structure must be considered together; coincidence does not prove causation.',small)

# Page 2
page('Results: Phase 1','FIRST-FLOOR INTERVENTIONS / MAPS FROM BOTH PHASES')
table(['Run','N / kept','Voxel m','Mean L2 m','Total s'],[
    ['Historical full baseline','191 / 100%','0.05','0.058835','NR'],
    ['Depth + ICP selection','179 / 93.72%','0.05','0.305000','280.44'],
    ['Selection, add frame 104','180 / 94.24%','0.05','0.125820','280.07'],
    ['Finer voxel + linked scales','191 / 100%','0.03','2.965126','1524.47'],
    ['Depth SOR (20 neighbors, 3 SD)','191 / 100%','0.05','0.338406','160.11*']
],[196,91,57,83,CW-427])
paragraph('NR = not recorded. Total includes reconstruction, diagnostics, evaluation and PNG/NPZ output, not declaration/sealing/dashboard. *SOR includes 23.16 s preprocessing. Historical runtime environments were not fully matched; differences are descriptive. Voxel 0.03 also changes normal/FPFH radii to 0.06/0.15 m and matching gates to 0.045 m.',small)
pair(ROOT/'experiments/phase1_open3d_reference/reconstruction_baseline.png',ROOT/'experiments/phase2_manual_baseline/reconstruction_baseline.png','Figure 2. Ceiling-cropped maps, red estimated / black GT. Left: fresh Phase 1 Open3D reference, 0.291071 m (not the historical 0.058835 m run). Right: manual Phase 2 baseline, 0.240687 m. Several connected rooms are visible; complete floor coverage is not quantitatively verified.')
heading('What the interventions tested')
paragraph('<b>Selection:</b> exclude a candidate only when RawPointCount &lt; 222,822.4 (85% of pixels) AND [ICP fitness &lt; 0.90 OR RMSE &gt; 0.025 m]. Keep frame 1 and every third frame as bridges. This exploratory rule uses no GT, but its 179-frame result is worse. Restoring frame 104 reduces common-179-frame error to 0.1250 m, still above baseline 0.0579 m. This rescue was motivated by post-hoc GT diagnosis, not an independent generalizable rule.')
paragraph('<b>Point filtering:</b> per-frame statistical outlier removal (SOR) [4] zeros removed depth pixels while preserving all frames and retained depth values. Mean removal is 1.48% (max 3.48%). Error grows from 3.35 to 21.98 cm over 103-104, then to 76.18 cm at 105. Masks also remove distant real surfaces, so lost geometric support is a plausible, unproven cause. Neither this setting nor finer voxels improves the saved baseline; original data and artifacts remain unchanged.')

# Page 3
page('Results: Phase 2','MANUAL COLLECTION / CONSERVATIVE SELECTION')
paragraph('Manually collect 351 frames using second_floor.yaml into eval/_data/second_floor/115062519_manual_20261104_082753. RGB/depth/GT entries match and decode. Maximum adjacent motion is 0.4715 m and 6.00 degrees; mean valid depth is 99.53%. The route traverses connecting spaces and room-facing views; complete floor coverage remains unverified.')
paragraph('Using current zone settings, benign/moderate/severe/outside counts are 4/11/0/336; no capture-time configuration snapshot exists. Therefore, this sequence does not test severe-zone performance. The earlier API capture has 281 frames and Mean L2 5.8823 m (215.06 s total); different routes, viewpoints and zone exposure prevent a controlled manual/API comparison.',small)
table(['Evaluation','Frames','Mean L2 m','Total s'],[
    ['Full manual baseline','351','0.240687','108.50'],
    ['Baseline on retained frames','348','0.238854','Not rerun'],
    ['Selected reconstruction','348 (99.15%)','0.236077','104.35']
],[220,100,90,CW-410])
paragraph('Reuse the Phase 1 rule unchanged. Candidates are 294, 311, 313, 350; keep bridge frame 294 and exclude only 311, 313, 350. Reconstruct from scratch at voxel 0.05 m, Open3D, seed 0. No GT is used to choose frames; original images are not deleted.')
image(ASSETS/'phase2_factors.png',maxheight=155,cap='Figure 3. Manual baseline factor timelines. Red lines mark excluded frames: fewer than 85% valid points and RMSE above 0.025 m. Actual new splice diagnostics are saved separately.')
image(ASSETS/'phase2_selection_comparison.png',maxheight=155,cap='Figure 4. Baseline versus selected trajectories/errors (GT black). Curves use their own frame sets; the table also compares the common 348 frames.')
paragraph('The gain is only <b>2.78 mm (1.16%) on common frames</b>. Reruns differ by up to 1.32 mm in a coordinate before selection changes; stable improvement is unproven. New splice pairs complete successfully. Full factor measurement versus pair-diagnostic work also differs, so the timing difference cannot be assigned solely to deletion.',small)

# Page 4
page('Custom ICP and discussion','BONUS COMPARISON / REQUIRED QUESTIONS')
paragraph('<b>Implementation.</b> my_local_icp_algorithm uses SciPy cKDTree nearest neighbors, a 0.075 m gate and point-to-plane residual r = n dot (p-q). Solve J delta = -r with J = [p cross n, n], then left-compose rotation/translation. Stop at 60 iterations, fewer than 10 pairs, or residual-change/step norm below 1e-6. It does not call Open3D ICP; no robust loss, damping or degeneracy checks were added.')
table(['Same 191 original frames','Mean L2 m','Recon. s','Total s'],[
    ['Fresh Open3D reference','0.291071','152.23','154.13'],
    ['Custom ICP','2.174410','167.19','169.78']
],[230,100,85,CW-415])
paragraph('Custom ICP has about 89.66 degrees of relative-rotation error at 104-105 and is 9.8% slower end-to-end in this trial. Both runs use OMP_NUM_THREADS=8 sequentially, with the shared settings on page 1; native iteration caps differ (60/100). However, 188/190 RANSAC initial transforms differ despite seed 0, and the fresh Open3D score does not reproduce the historical baseline. Thus, this is not a pure local-solver benchmark; timing includes features, RANSAC and map merging. Matched initial transforms and repeated trials are needed for stronger conclusions.')
heading('Q1. What happens without RANSAC?')
paragraph('ICP is local: nearest-neighbor assignments depend on initialization [2,3]. Without a good initial pose, turns or repeated/flat geometry can lead to wrong correspondences and a local minimum. Very small inter-frame motion may still converge. No no-RANSAC ablation was run; this is a method-based expectation.')
heading('Q2. What affects ICP stability?')
paragraph('Balance voxel resolution, normal/FPFH support and matching gates, then use global initialization. More points did not guarantee better results: voxel 0.03 also tightened linked scales and worsened this run. Robust losses and damped updates are possible extensions, not tested improvements. High inlier fitness alone does not guarantee correct pose.')
heading('Q3. How do data quality and collection affect error?')
paragraph('Depth loss reduces potential support, but overlap and visible geometry determine whether useful constraints survive. Deleting frames or distant points can remove those constraints. Phase 2 selection barely changes common-frame error; the manual/API score difference is confounded by route and coverage. Preserve negative results and report associations rather than causal claims.')
paragraph('<b>Limits:</b> single trials, unmatched historical timing conditions, missing old runtimes, rerun sensitivity, qualitative map completeness and absent manual severe-zone coverage. GT is used only after reconstruction for evaluation/diagnosis. New records have complete factors and valid seals; source data, historical artifacts and scores pass saved integrity checks.',small)
heading('References and evidence')
paragraph('[1] Course handout, <i>HW1: 3D Scene Reconstruction</i>, sections 2.2.2, 3.2-3.5, 4-5; implementation: utils.py, reconstruct.py, api.py, ontology/hw1.ttl. [2] Open3D <link href="https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html" color="#217987">ICP registration</link>. [3] <link href="https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html" color="#217987">Global registration</link>. [4] <link href="https://www.open3d.org/docs/release/tutorial/geometry/pointcloud_outlier_removal.html" color="#217987">Outlier removal</link>. Experiments use Open3D 0.18.0, Python 3.9.23, NumPy 1.26.4 and SciPy 1.13.1.',small,gap=4)
paragraph('Full evidence remains under experiments/; report/sources.json records input hashes. No new reconstruction was run for this report. Package report.pdf with the required code, ontology and README at the ZIP root; exclude captures, diagnostic outputs, experiment Turtle files and Replica assets [1].',small,gap=0)

assert page_num==4
c.save()
(HERE/'report.md').write_text('\n'.join(md)+'\n')
print(f'Wrote {OUTPUT} ({page_num} pages) and editable report/report.md')
