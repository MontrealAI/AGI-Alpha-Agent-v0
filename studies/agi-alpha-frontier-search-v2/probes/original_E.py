import itertools,numpy as np
I=np.eye(2,dtype=complex)
P=[I,np.array([[0,1],[1,0]]),np.array([[0,-1j],[1j,0]]),np.diag([1,-1])]
phi=np.array([1,0,0,1])/np.sqrt(2)
for n in (2,3,4):
 L=[]
 for idx in itertools.product(range(4),repeat=n):
  a=0*I
  for s in range(n):
   b=I.copy()
   for k in list(range(n))[s:]+list(range(n))[:s]: b=P[idx[k]]@b/2
   a+=b/n
  L.append(a)
 out=sum(np.outer(k[:,0],k[:,0].conj()) for k in L)
 p=np.trace(out).real
 J=sum(np.outer(np.kron(k,I)@phi,(np.kron(k,I)@phi).conj()) for k in L)/p
 pt=J.reshape(2,2,2,2).transpose(0,3,2,1).reshape(4,4)
 print(n,p,out[0,0].real/p,np.linalg.eigvalsh(pt).min())
A=np.array([[1,2,1],[2,1,1]])
x=np.array([1,1,0]);z=np.array([0,0,3])
print(A@x,A@z,np.max(abs((A@x-A@z)[:,None]*np.linspace(.5,2,17))))
print(1e6*1e-6*.7*58.0967/18.9984/1000*100)

