import numpy as np
t=(np.arange(10000)+.5)/1000
s1=np.where((t>=2)&(t<4),2.,0.)
g1=np.ones_like(t)
phi=np.where(t<1,2*t,np.where(t<5,2+.5*(t-1),4+1.2*(t-5)))
g2=np.where(t<1,2.,np.where(t<5,.5,1.2))
s2=np.where((phi>=2)&(phi<4),2.,0.)
print(g1.sum()/1000,g2.sum()/1000,(g1*s1).sum()/1000,(g2*s2).sum()/1000)
rng=np.random.default_rng(2710)
H=rng.uniform(.1,1.,size=(64,192));H/=H.sum(axis=1,keepdims=True)
_,s,vt=np.linalg.svd(H,full_matrices=True)
v=vt[64];v*=.4/np.max(np.abs(v))
x=np.ones(192);xx=x+v
print(np.linalg.matrix_rank(H),np.linalg.norm(xx-x)/np.linalg.norm(x),np.max(np.abs(H@x-H@xx)),xx.min())
