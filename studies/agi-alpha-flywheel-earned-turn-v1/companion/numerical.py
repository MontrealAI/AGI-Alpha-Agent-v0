import hashlib,json,time
from pathlib import Path
import numpy as np
import scipy
from scipy.sparse import coo_matrix,csc_matrix,diags
from scipy.sparse.linalg import splu,cg,LinearOperator,spsolve_triangular

DEPENDENCIES={'numpy':np.__version__,'scipy':scipy.__version__}
FACTOR_SCHEMA='sparse-factor-persistence/v1'
UPDATE_SCHEMA='low-rank-response-persistence/v1'
ORDERINGS={'NATURAL','MMD_ATA','MMD_AT_PLUS_A','COLAMD'}
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def _hash_string(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _factor_identity(oid,ordering):return digest({'operator':oid,'ordering':ordering,'dependencies':DEPENDENCIES,'kind':'sparse-factor/v1'})
def _receipt_bytes(path,receipt,reason):
    if not isinstance(receipt,dict) or not _hash_string(receipt.get('sha256')) or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:raise ValueError(reason)
def _validate_changes(changes,edge_count):
    if not isinstance(changes,list) or not changes or len(changes)>min(edge_count,1024):raise ValueError('UPDATE_SCOPE')
    seen=set()
    for item in changes:
        if not isinstance(item,list) or len(item)!=2:raise ValueError('UPDATE_SCOPE')
        i,delta=item
        if not isinstance(i,int) or isinstance(i,bool) or i<0 or i>=edge_count or i in seen:raise ValueError('UPDATE_SCOPE')
        if not isinstance(delta,(int,float)) or isinstance(delta,bool) or not np.isfinite(delta) or delta<=0:raise ValueError('UPDATE_SCOPE')
        seen.add(i)
def _float_array(value,shape):
    return value.shape==shape and value.dtype.kind=='f' and np.isfinite(value).all()
def _factor_arrays(z,n):
    for key in ['pr','pc']:
        a=z[key]
        if a.shape!=(n,) or a.dtype.kind not in 'iu' or not np.array_equal(np.sort(a),np.arange(n)):raise ValueError('FACTOR_PERMUTATION')
    out=[]
    for prefix,lower in [('L',True),('U',False)]:
        data,indices,indptr=(z[prefix+k] for k in ['data','indices','indptr'])
        if data.ndim!=1 or data.dtype.kind!='f' or not np.isfinite(data).all() or indices.shape!=data.shape or indices.dtype.kind not in 'iu':raise ValueError('FACTOR_ARRAY_SCHEMA')
        if indptr.shape!=(n+1,) or indptr.dtype.kind not in 'iu' or indptr[0]!=0 or indptr[-1]!=len(data) or np.any(np.diff(indptr)<0):raise ValueError('FACTOR_ARRAY_SCHEMA')
        if np.any(indices<0) or np.any(indices>=n):raise ValueError('FACTOR_ARRAY_SCHEMA')
        for col in range(n):
            a,b=int(indptr[col]),int(indptr[col+1]);rows=indices[a:b];values=data[a:b]
            if len(np.unique(rows))!=len(rows) or np.any(rows<col if lower else rows>col):raise ValueError('FACTOR_TRIANGULAR_SCHEMA')
            diagonal=values[rows==col]
            if len(diagonal)!=1 or (diagonal[0]!=1 if lower else diagonal[0]==0):raise ValueError('FACTOR_TRIANGULAR_SCHEMA')
        out.append(csc_matrix((data,indices,indptr),shape=(n,n)))
    return out
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
    n=task['n'];diag=np.asarray(task['ground'],dtype=float).copy();rows=[];cols=[];vals=[]
    for u,v,w in task['edges']:
        rows.extend((u,v));cols.extend((v,u));vals.extend((-w,-w));diag[u]+=w;diag[v]+=w
    rows.extend(range(n));cols.extend(range(n));vals.extend(diag)
    return coo_matrix((vals,(rows,cols)),shape=(n,n)).tocsc()
class Factor:
    def __init__(self,A,oid,ordering='MMD_AT_PLUS_A'):
        if not _hash_string(oid) or ordering not in ORDERINGS:raise ValueError('FACTOR_SCOPE')
        self.factor=splu(A,permc_spec=ordering);self.oid=oid;self.ordering=ordering;self.calls=0;self.native=True
        self.L=self.factor.L;self.U=self.factor.U;self.pr=self.factor.perm_r;self.pc=self.factor.perm_c
        self.identity=_factor_identity(oid,ordering)
    def solve(self,b):
        self.calls+=1
        if self.native:return self.factor.solve(np.asarray(b))
        y=spsolve_triangular(self.L,np.asarray(b)[np.argsort(self.pr)],lower=True,unit_diagonal=True)
        z=spsolve_triangular(self.U,y,lower=False)
        return z[self.pc]
    def save(self,path):
        path=Path(path)
        np.savez(path,Ldata=self.L.data,Lindices=self.L.indices,Lindptr=self.L.indptr,Udata=self.U.data,Uindices=self.U.indices,Uindptr=self.U.indptr,pr=self.pr,pc=self.pc,n=np.array(self.L.shape[0]),meta=np.array(json.dumps({'schema':FACTOR_SCHEMA,'oid':self.oid,'ordering':self.ordering,'identity':self.identity,'dependencies':DEPENDENCIES})))
        return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    @classmethod
    def load(cls,path,receipt,expected_oid):
        path=Path(path)
        _receipt_bytes(path,receipt,'FACTOR_BYTES_CHANGED')
        with np.load(path,allow_pickle=False) as z:
            if set(z.files)!={'Ldata','Lindices','Lindptr','Udata','Uindices','Uindptr','pr','pc','n','meta'} or z['meta'].shape!=() or z['n'].shape!=() or z['n'].dtype.kind not in 'iu':raise ValueError('FACTOR_ARRAY_SCHEMA')
            meta=json.loads(str(z['meta']));n=int(z['n'])
            if not isinstance(meta,dict) or set(meta)!={'schema','oid','ordering','identity','dependencies'} or meta['schema']!=FACTOR_SCHEMA or not 1<=n<=65536:raise ValueError('FACTOR_METADATA_SCHEMA')
            if meta['dependencies']!=DEPENDENCIES:raise ValueError('DEPENDENCY_CHANGED')
            if not _hash_string(expected_oid) or meta['oid']!=expected_oid:raise ValueError('STALE_OPERATOR')
            if meta['ordering'] not in ORDERINGS or meta['identity']!=_factor_identity(expected_oid,meta['ordering']):raise ValueError('FACTOR_IDENTITY_MISMATCH')
            L,U=_factor_arrays(z,n)
            obj=cls.__new__(cls);obj.L=L;obj.U=U;obj.pr=z['pr'];obj.pc=z['pc'];obj.oid=meta['oid'];obj.ordering=meta['ordering'];obj.identity=meta['identity'];obj.native=False;obj.calls=0
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
    _validate_changes(changes,len(task['edges']))
    edges=[e[:] for e in task['edges']]
    for i,delta in changes:
        if not np.isfinite(edges[i][2]+delta):raise ValueError('UPDATE_SCOPE')
        edges[i][2]+=delta
    return {**task,'edges':edges}
class Update:
    def __init__(self,parent,task,changes,preceding_receipt,*,validated_ids=None):
        if validated_ids is not None and (not isinstance(validated_ids,tuple) or len(validated_ids)!=2 or not all(_hash_string(v) for v in validated_ids)):raise ValueError('TRUSTED_ID_BINDING_SCOPE')
        base_oid=operator_id(task) if validated_ids is None else validated_ids[0]
        if parent.oid!=base_oid:raise ValueError('STALE_PARENT')
        _validate_changes(changes,len(task['edges']))
        if not _hash_string(preceding_receipt):raise ValueError('PRECEDING_RECEIPT_SCOPE')
        for i,delta in changes:
            if not np.isfinite(task['edges'][i][2]+delta):raise ValueError('UPDATE_SCOPE')
        updated_oid=operator_id(change_task(task,changes)) if validated_ids is None else validated_ids[1]
        if updated_oid==base_oid:raise ValueError('UNCHANGED_UPDATE_OPERATOR')
        self.id_binding='derived-in-builder' if validated_ids is None else 'fixed-orchestrator-prevalidated'
        self.parent=parent;self.changes=[c[:] for c in changes];self.base_oid=parent.oid;self.preceding_receipt=preceding_receipt;self.edge_count=len(task['edges'])
        n=task['n']; k=len(changes);U=np.zeros((n,k))
        for j,(i,delta) in enumerate(changes):
            u,v,_=task['edges'][i];U[u,j]=delta**.5;U[v,j]=-delta**.5
        before=parent.calls;self.W=parent.solve(U);self.construction_parent_calls=parent.calls-before
        self.U=U;self.S=np.eye(k)+U.T@self.W;self.oid=updated_oid;self.calls=0
        self.identity=digest({'kind':'low-rank-response/v1','parent':parent.identity,'operator':self.oid,'preceding_accepted_receipt':preceding_receipt,'changes':changes})
    def solve(self,b):
        self.calls+=1;y=self.parent.solve(np.asarray(b));return y-self.W@np.linalg.solve(self.S,self.U.T@y)
    def save(self,path):
        np.savez(path,U=self.U,W=self.W,S=self.S,meta=np.array(json.dumps({'schema':UPDATE_SCHEMA,'n':self.U.shape[0],'edge_count':self.edge_count,'id_binding':self.id_binding,'identity':self.identity,'parent':self.parent.identity,'operator':self.oid,'base_operator':self.base_oid,'changes':self.changes,'preceding_accepted_receipt':self.preceding_receipt,'dependencies':DEPENDENCIES})))
        path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    @classmethod
    def load(cls,path,receipt,parent,expected_oid=None):
        path=Path(path)
        _receipt_bytes(path,receipt,'UPDATE_BYTES_CHANGED')
        with np.load(path,allow_pickle=False) as z:
            if set(z.files)!={'U','W','S','meta'} or z['meta'].shape!=():raise ValueError('UPDATE_ARRAY_SCHEMA')
            m=json.loads(str(z['meta']))
            if not isinstance(m,dict) or set(m)!={'schema','n','edge_count','id_binding','identity','parent','operator','base_operator','changes','preceding_accepted_receipt','dependencies'} or m['schema']!=UPDATE_SCHEMA or m['id_binding'] not in ['derived-in-builder','fixed-orchestrator-prevalidated']:raise ValueError('UPDATE_METADATA_SCHEMA')
            if m['dependencies']!=DEPENDENCIES or m['parent']!=parent.identity:raise ValueError('STALE_UPDATE_DEPENDENCY')
            if m['base_operator']!=parent.oid or not _hash_string(m['operator']) or expected_oid is not None and m['operator']!=expected_oid:raise ValueError('STALE_UPDATE_OPERATOR')
            n=m['n'];edge_count=m['edge_count']
            if not isinstance(n,int) or isinstance(n,bool) or n!=parent.L.shape[0] or not isinstance(edge_count,int) or isinstance(edge_count,bool) or edge_count<1 or edge_count>1000000:raise ValueError('UPDATE_METADATA_SCHEMA')
            _validate_changes(m['changes'],edge_count);k=len(m['changes'])
            if not _hash_string(m['preceding_accepted_receipt']):raise ValueError('PRECEDING_RECEIPT_SCOPE')
            expected_identity=digest({'kind':'low-rank-response/v1','parent':parent.identity,'operator':m['operator'],'preceding_accepted_receipt':m['preceding_accepted_receipt'],'changes':m['changes']})
            if m['identity']!=expected_identity:raise ValueError('UPDATE_IDENTITY_MISMATCH')
            U,W,S=z['U'],z['W'],z['S']
            if not _float_array(U,(n,k)) or not _float_array(W,(n,k)) or not _float_array(S,(k,k)):raise ValueError('UPDATE_ARRAY_SCHEMA')
            for j,(_,delta) in enumerate(m['changes']):
                values=U[:,j][U[:,j]!=0]
                if len(values)!=2 or sorted(values.tolist())!=[-delta**.5,delta**.5]:raise ValueError('UPDATE_DIRECTION_SCHEMA')
            if not np.allclose(S,np.eye(k)+U.T@W,rtol=1e-12,atol=1e-12) or not np.allclose(S,S.T,rtol=1e-10,atol=1e-12):raise ValueError('UPDATE_SCHUR_SCHEMA')
            try:np.linalg.cholesky(S)
            except np.linalg.LinAlgError:raise ValueError('UPDATE_SCHUR_SCHEMA')
            o=cls.__new__(cls);o.parent=parent;o.U=U;o.W=W;o.S=S;o.identity=m['identity'];o.oid=m['operator'];o.base_oid=m['base_operator'];o.changes=m['changes'];o.preceding_receipt=m['preceding_accepted_receipt'];o.edge_count=edge_count;o.id_binding=m['id_binding'];o.calls=0;o.construction_parent_calls=0
        return o
