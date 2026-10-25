import hashlib,json,time
from pathlib import Path
import numpy as np
import scipy
from scipy.sparse import coo_matrix,csc_matrix,diags
from scipy.sparse.linalg import splu,cg,LinearOperator,spsolve_triangular

DEPENDENCIES={'numpy':np.__version__,'scipy':scipy.__version__}
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def measure(fn):
    c,w=time.process_time_ns(),time.perf_counter_ns(); value=fn()
    return value,{'cpu_ms':(time.process_time_ns()-c)/1e6,'wall_ms':(time.perf_counter_ns()-w)/1e6}
def make_task(seed,side=48,ground=.1):
    rng=np.random.default_rng(seed); n=side*side; edges=[]
    for u in range(n):
        if u%side+1<side:edges.append([u,u+1,float(rng.uniform(.5,2))])
        if u+side<n:edges.append([u,u+side,float(rng.uniform(.5,2))])
    return {'n':n,'side':side,'edges':edges,'ground':[float(ground)]*n,'rhs':rng.normal(0,1,n).tolist(),'synthetic':True}
def with_load(task,seed):
    rng=np.random.default_rng(seed)
    return {**task,'rhs':rng.normal(0,1,task['n']).tolist()}
def operator_id(task):return digest({k:task[k] for k in ['n','edges','ground']})
def matrix(task):
    n=task['n'];diag=np.asarray(task['ground']).copy();rows=[];cols=[];vals=[]
    for u,v,w in task['edges']:
        rows.extend((u,v));cols.extend((v,u));vals.extend((-w,-w));diag[u]+=w;diag[v]+=w
    rows.extend(range(n));cols.extend(range(n));vals.extend(diag)
    return coo_matrix((vals,(rows,cols)),shape=(n,n)).tocsc()
class Factor:
    def __init__(self,A,oid,ordering='MMD_AT_PLUS_A'):
        self.factor=splu(A,permc_spec=ordering);self.oid=oid;self.ordering=ordering;self.calls=0;self.native=True
        self.L=self.factor.L;self.U=self.factor.U;self.pr=self.factor.perm_r;self.pc=self.factor.perm_c
        self.identity=digest({'operator':oid,'ordering':ordering,'dependencies':DEPENDENCIES,'kind':'sparse-factor/v1'})
    def solve(self,b):
        self.calls+=1
        if self.native:return self.factor.solve(np.asarray(b))
        y=spsolve_triangular(self.L,np.asarray(b)[np.argsort(self.pr)],lower=True,unit_diagonal=True)
        z=spsolve_triangular(self.U,y,lower=False)
        return z[self.pc]
    def save(self,path):
        path=Path(path)
        np.savez(path,Ldata=self.L.data,Lindices=self.L.indices,Lindptr=self.L.indptr,Udata=self.U.data,Uindices=self.U.indices,Uindptr=self.U.indptr,pr=self.pr,pc=self.pc,n=np.array(self.L.shape[0]),meta=np.array(json.dumps({'oid':self.oid,'ordering':self.ordering,'identity':self.identity,'dependencies':DEPENDENCIES})))
        return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    @classmethod
    def load(cls,path,receipt,expected_oid):
        path=Path(path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:raise ValueError('FACTOR_BYTES_CHANGED')
        with np.load(path,allow_pickle=False) as z:
            meta=json.loads(str(z['meta']));n=int(z['n'])
            if meta['dependencies']!=DEPENDENCIES:raise ValueError('DEPENDENCY_CHANGED')
            if meta['oid']!=expected_oid:raise ValueError('STALE_OPERATOR')
            obj=cls.__new__(cls);obj.L=csc_matrix((z['Ldata'],z['Lindices'],z['Lindptr']),shape=(n,n));obj.U=csc_matrix((z['Udata'],z['Uindices'],z['Uindptr']),shape=(n,n));obj.pr=z['pr'];obj.pc=z['pc'];obj.oid=meta['oid'];obj.ordering=meta['ordering'];obj.identity=meta['identity'];obj.native=False;obj.calls=0
        return obj

def direct(task,method='direct',x0=None):
    A=matrix(task);b=np.asarray(task['rhs'])
    if method=='cg':
        diag=A.diagonal(); x,info=cg(A,b,x0=x0,rtol=1e-11,atol=0,maxiter=4000,M=LinearOperator(A.shape,matvec=lambda v:v/diag))
        if info:raise ValueError('CG_DID_NOT_CONVERGE')
        return x,None
    f=Factor(A,operator_id(task),ordering='COLAMD' if method=='colamd' else 'MMD_AT_PLUS_A')
    return f.solve(b),f

def choose_changes(task,x,k):
    scored=sorted(enumerate(task['edges']),key=lambda r:(-abs(r[1][2]*(x[r[1][0]]-x[r[1][1]])),r[0]))[:k]
    return [[index,float(edge[2])*.5] for index,edge in scored]
def change_task(task,changes):
    edges=[e[:] for e in task['edges']]
    for i,delta in changes:
        if not isinstance(i,int) or i<0 or i>=len(edges) or not np.isfinite(delta) or delta<=0:raise ValueError('UPDATE_SCOPE')
        edges[i][2]+=delta
    return {**task,'edges':edges}
class Update:
    def __init__(self,parent,task,changes,preceding_receipt):
        if parent.oid!=operator_id(task):raise ValueError('STALE_PARENT')
        self.parent=parent;self.changes=changes;self.base_oid=parent.oid;self.preceding_receipt=preceding_receipt
        n=task['n']; k=len(changes);U=np.zeros((n,k))
        for j,(i,delta) in enumerate(changes):
            u,v,_=task['edges'][i];U[u,j]=delta**.5;U[v,j]=-delta**.5
        before=parent.calls;self.W=parent.solve(U);self.construction_parent_calls=parent.calls-before
        self.U=U;self.S=np.eye(k)+U.T@self.W;self.oid=operator_id(change_task(task,changes));self.calls=0
        self.identity=digest({'kind':'low-rank-response/v1','parent':parent.identity,'operator':self.oid,'preceding_accepted_receipt':preceding_receipt,'changes':changes})
    def solve(self,b):
        self.calls+=1;y=self.parent.solve(np.asarray(b));return y-self.W@np.linalg.solve(self.S,self.U.T@y)
    def save(self,path):
        np.savez(path,U=self.U,W=self.W,S=self.S,meta=np.array(json.dumps({'identity':self.identity,'parent':self.parent.identity,'operator':self.oid,'base_operator':self.base_oid,'changes':self.changes,'preceding_accepted_receipt':self.preceding_receipt,'dependencies':DEPENDENCIES})))
        path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    @classmethod
    def load(cls,path,receipt,parent):
        path=Path(path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:raise ValueError('UPDATE_BYTES_CHANGED')
        with np.load(path,allow_pickle=False) as z:
            m=json.loads(str(z['meta']))
            if m['dependencies']!=DEPENDENCIES or m['parent']!=parent.identity:raise ValueError('STALE_UPDATE_DEPENDENCY')
            o=cls.__new__(cls);o.parent=parent;o.U=z['U'];o.W=z['W'];o.S=z['S'];o.identity=m['identity'];o.oid=m['operator'];o.base_oid=m['base_operator'];o.changes=m['changes'];o.preceding_receipt=m['preceding_accepted_receipt'];o.calls=0;o.construction_parent_calls=0
        return o
