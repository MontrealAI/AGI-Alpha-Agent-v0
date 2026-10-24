# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Ellipse

out=Path(__file__).resolve().parents[1]/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','pdf.fonttype':42})
fig,ax=plt.subplots(figsize=(12.4,6.4));fig.patch.set_facecolor('#100B26');ax.set_facecolor('#100B26')
ax.set_xlim(0,12.4);ax.set_ylim(0,6.4);ax.axis('off')
rng=np.random.default_rng(20261023)
ax.scatter(rng.uniform(.2,12.2,95),rng.uniform(.2,6.2,95),s=rng.uniform(.3,2.4,95),c='#BCA4FF',alpha=.34,zorder=0)
ax.text(.5,5.87,'THE ABUNDANCE MAP',color='#D2BAFF',fontsize=11,weight='bold',ha='left')
ax.text(.5,5.34,'A useful seed can outlive its exclusivity.',color='white',fontsize=20,weight='bold')
def box(x,y,w,h,title,body,color):
 p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.13',facecolor='#21153C',edgecolor=color,linewidth=1.2);ax.add_patch(p)
 ax.text(x+.2,y+h-.32,title,color=color,fontsize=11,weight='bold',va='top')
 ax.text(x+.2,y+h-.78,body,color='#EEE8FA',fontsize=10,va='top',linespacing=1.65)
def arrow(a,b,color='#BA9BED',style='-'):
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=13,color=color,lw=1.5,connectionstyle='arc3,rad=0.0',linestyle=style))
box(.5,2.45,3.1,2.05,'COPYABLE KNOWLEDGE','Algorithm + source + inputs\nCalibration rules + checker\nEqual rebuilding rights','#BCA4FF')
box(4.62,2.45,3.1,2.05,'BOUNDED OPERATIONS','Instrument ticks + validity\nCurrent mission + authority\nFresh execution evidence','#F0C983')
box(8.73,2.45,3.17,2.05,'CHECKED OUTCOMES','Useful work + failures\nCost + latency + resource use\nBenefit and capture separate','#8CE4CE')
arrow((3.65,3.45),(4.55,3.45));arrow((7.77,3.45),(8.66,3.45))
ax.add_patch(Ellipse((4.1,3.46),.36,.6,angle=-25,facecolor='#E4D5FF',edgecolor='#FFF5CE',lw=1.0,zorder=4))
ax.text(4.12,2.98,'seed',color='#D2BAFF',fontsize=9,ha='center')
box(2.37,.7,3.35,1.12,'INCUMBENT','Same disclosed capability','#D2BAFF')
box(6.67,.7,3.35,1.12,'COMPLETE REPLICA','Fresh run; same resources','#8CE4CE')
arrow((2.2,2.4),(3.35,1.87),style='--');arrow((3.1,2.4),(7.3,1.87),style='--')
ax.text(6.2,1.18,'compare',color='#E6DCF8',fontsize=10,ha='center')
ax.text(.5,.2,'CONCEPTUAL DIAGRAM  •  Resource limits are modelled; computational measurements are reported separately.',color='#AEA3C5',fontsize=8.2)
fig.subplots_adjust(0,0,1,1)
for suffix in ('pdf','svg','png'):fig.savefig(out/f'abundance-map.{suffix}',dpi=170,facecolor=fig.get_facecolor())
plt.close(fig)
