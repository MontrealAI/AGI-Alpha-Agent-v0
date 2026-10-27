# SPDX-License-Identifier: Apache-2.0
import numpy as np

def check(case, ns):
    rows=[]
    def add(name, observed, expected):
        rows.append({'name':name,'pass':bool(np.allclose(observed,expected,rtol=1e-10,atol=1e-10)),'observed':np.asarray(observed).tolist(),'expected':np.asarray(expected).tolist()})
    if 'Feature' in case:
        add('mean_imputation_column_0',ns['X2'][:,0],[4.5,3,3,4,8])
        add('mean_imputation_column_1',ns['X2'][:,1],[0,7,5,5,8])
        add('complete_polynomial_fit',ns['model'].predict(ns['X']),ns['y'])
        add('observed_column_preserved',ns['X2'][:,2],[3,9,2,6,1])
    elif 'Concat' in case:
        import pandas as pd
        add('horizontal_concat_shape',pd.concat([ns['df3'],ns['df4']],axis=1).shape,[2,4])
        add('left_projection_shape',pd.concat([ns['df5'],ns['df6']]).reindex(columns=ns['df5'].columns).shape,[4,3])
        add('append_retains_labels',pd.concat([ns['df1'],ns['df2']]).index,[1,2,3,4])
        add('projection_missingness',pd.concat([ns['df5'],ns['df6']]).reindex(columns=ns['df5'].columns).isna().sum(),[2,0,0])
    return rows
