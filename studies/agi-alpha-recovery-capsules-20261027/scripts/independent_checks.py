# SPDX-License-Identifier: Apache-2.0
import numpy as np

def check(case, ns):
    rows = []
    def add(name, ok, detail):
        rows.append({"name": name, "pass": bool(ok), "detail": detail})
    def equal(name, observed, expected):
        a, b = np.asarray(observed), np.asarray(expected)
        add(name, a.shape == b.shape and np.array_equal(a, b), {"observed": a.tolist(), "expected": b.tolist()})
    def close(name, observed, expected, atol=1e-8, rtol=1e-10):
        a, b = np.asarray(observed, dtype=float), np.asarray(expected, dtype=float)
        valid = a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
        error = float(np.max(np.abs(a - b))) if valid and a.size else None
        add(name, valid and np.allclose(a, b, atol=atol, rtol=rtol), {"shape": list(a.shape), "max_absolute_error": error, "atol": atol, "rtol": rtol})
    try:
        if case.startswith("03.02"):
            data = ns["data"]
            states = ["California", "Florida", "Illinois", "New York", "Texas"]
            area = np.array([423967, 170312, 149995, 141297, 695662])
            pop = np.array([38332521, 19552860, 12882135, 19651127, 26448193])
            equal("historical_sorted_row_order", data.index, states)
            equal("column_contract", data.columns, ["area", "pop", "density"])
            equal("areas_unchanged", data["area"], area)
            equal("populations_unchanged", data["pop"], pop)
            density = pop / area
            density[0] = 90
            close("density_with_explicit_california_update", data["density"], density)
            equal("mixed_selector_meaning", data.iloc[:3].loc[:, :"pop"].index, states[:3])
            equal("label_and_position_slice_agree", data["Florida":"Illinois"].index, ["Florida", "Illinois"])
            equal("density_decision_set", data.loc[data.density > 100].index, ["Florida", "New York"])
        elif case.startswith("03.05"):
            pop = ns["pop"]
            expected_pop = [33871648,37253956,18976457,19378102,20851820,25145561]
            expected_index = [("California",2000),("California",2010),("New York",2000),("New York",2010),("Texas",2000),("Texas",2010)]
            add("population_index_contract", list(pop.index) == expected_index, {"observed": list(pop.index), "expected": expected_index})
            equal("population_values", pop.values, expected_pop)
            close("under18_fractions", ns["f_u18"].values, np.array([9267089,9284094,4687374,4318033,5906301,6879014]) / expected_pop)
            equal("reshape_roundtrip", pop.unstack().stack().values, expected_pop)
            frame = ns["health_data"]
            add("health_table_axes", frame.shape == (4,6) and list(frame.index.names)==["year","visit"] and list(frame.columns.names)==["subject","type"], {"shape":list(frame.shape),"index_names":list(frame.index.names),"column_names":list(frame.columns.names)})
            values = frame.to_numpy()
            manual = np.stack([values[:2].sum(axis=0)/2, values[2:].sum(axis=0)/2])
            close("year_means_manual_reduction", ns["data_mean"].values, manual)
            equal("year_mean_labels", ns["data_mean"].index, [2013,2014])
            add("explicit_sorted_slice", list(ns["data"].loc["a":"b"].index)==[("a",1),("a",2),("b",1),("b",2)], {"observed":list(ns["data"].loc["a":"b"].index)})
            final = ns.get("_")
            if hasattr(final, "columns") and list(final.columns)==["HR","Temp"]:
                close("subject_type_means_manual_reduction", final.values, np.stack([manual[:,::2].sum(axis=1)/3,manual[:,1::2].sum(axis=1)/3],axis=1))
        elif case.startswith("05.02"):
            Xi = np.asarray(ns["X_iris"], dtype=float)
            add("iris_shape_and_labels", Xi.shape==(150,4) and len(set(ns["y_iris"]))==3, {"shape":list(Xi.shape),"classes":sorted(set(ns["y_iris"]))})
            centered = Xi - Xi.mean(axis=0)
            U, S, V = np.linalg.svd(centered, full_matrices=False)
            reference = U[:,:2] * S[:2]
            embedding = np.asarray(ns["X_2D"])
            close("pca_geometry_svd_reference", embedding@embedding.T, reference@reference.T, atol=1e-7)
            rng = np.random.RandomState(42)
            x = 10*rng.rand(50)
            y = 2*x - 1 + rng.randn(50)
            coeff = np.linalg.lstsq(np.column_stack([x,np.ones(50)]),y,rcond=None)[0]
            close("linear_regression_independent_lstsq", ns["yfit"], coeff[0]*ns["xfit"]+coeff[1])
            labels = np.asarray(ns["y_gmm"])
            add("mixture_complete_partition", labels.shape==(150,) and np.isfinite(labels).all() and set(labels)=={0,1,2}, {"shape":list(labels.shape),"labels":sorted(set(labels.tolist()))})
            digits = ns["digits"]
            add("digits_input_contract", digits.data.shape==(1797,64) and digits.images.shape==(1797,8,8), {"data_shape":list(digits.data.shape),"image_shape":list(digits.images.shape)})
            perm = np.random.RandomState(0).permutation(1797)
            close("unchanged_digit_test_partition", ns["Xtest"], digits.data[perm[:450]],atol=0,rtol=0)
            equal("unchanged_digit_test_labels", ns["ytest"], digits.target[perm[:450]])
            train = digits.data[perm[450:]]
            train_labels = digits.target[perm[450:]]
            test = np.asarray(ns["Xtest"])
            classes = np.unique(train_labels)
            epsilon = 1e-9 * train.var(axis=0).max()
            logprob = []
            for c in classes:
                sub = train[train_labels==c]
                mu, var = sub.mean(axis=0), sub.var(axis=0)+epsilon
                logprob.append(np.log(len(sub)/len(train))-.5*np.log(2*np.pi*var).sum()-.5*(((test-mu)**2)/var).sum(axis=1))
            predictions = classes[np.argmax(np.column_stack(logprob),axis=1)]
            equal("gaussian_naive_bayes_independent_formula", ns["y_model"], predictions)
            mat = np.zeros((10,10),dtype=int)
            np.add.at(mat,(np.asarray(ns["ytest"],dtype=int),predictions),1)
            equal("confusion_matrix_manual_histogram", ns["mat"], mat)
            projected=np.asarray(ns["data_projected"])
            add("isomap_finite_complete_embedding", projected.shape==(1797,2) and np.isfinite(projected).all(), {"shape":list(projected.shape)})
        elif case.startswith("05.03"):
            source_iris = ns["iris"]
            Xiris, yiris=np.asarray(source_iris.data),np.asarray(source_iris.target)
            d=((Xiris[:,None,:]-Xiris[None,:,:])**2).sum(axis=2)
            np.fill_diagonal(d,np.inf)
            loo=(yiris[np.argmin(d,axis=1)]==yiris).astype(float)
            equal("leave_one_out_direct_distance_reference", ns["scores"], loo)
            rng=np.random.RandomState(1)
            X=rng.rand(40,1)**2
            y=10-1/(X.ravel()+.1)+rng.randn(40)
            close("polynomial_training_inputs",ns["X"],X,atol=0,rtol=0)
            close("polynomial_training_targets",ns["y"],y,atol=0,rtol=0)
            train_score,val_score=np.asarray(ns["train_score"]),np.asarray(ns["val_score"])
            add("validation_curve_dimensions",train_score.shape==(21,7) and val_score.shape==(21,7),{"train":list(train_score.shape),"validation":list(val_score.shape)})
            folds=np.array_split(np.arange(40),7)
            r2=[]
            for test_indices in folds:
                training=np.setdiff1d(np.arange(40),test_indices)
                true=y[test_indices]
                prediction=np.repeat(y[training].mean(),len(test_indices))
                r2.append(1-((true-prediction)**2).sum()/((true-true.mean())**2).sum())
            close("degree_zero_validation_manual_folds",val_score[0],r2,atol=1e-10)
            grid=ns["grid"]
            params=grid.cv_results_["params"]
            add("full_grid_scope_and_folds",len(params)==84 and grid.n_splits_==7 and len({p["polynomialfeatures__degree"] for p in params})==21 and {p["linearregression__normalize"] for p in params}=={True,False},{"candidates":len(params),"folds":int(grid.n_splits_),"fit_count":len(params)*int(grid.n_splits_)})
            scores=np.asarray(grid.cv_results_["mean_test_score"])
            add("grid_selection_consistent",np.isfinite(scores).all() and int(grid.best_index_)==int(np.argmax(scores)) and grid.best_params_["polynomialfeatures__degree"]==4,{"best_params":grid.best_params_,"best_mean_score":float(grid.best_score_)})
            coefficients=np.linalg.lstsq(np.vander(X.ravel(),5,increasing=True),y,rcond=None)[0]
            expected=np.vander(np.asarray(ns["X_test"]).ravel(),5,increasing=True)@coefficients
            close("selected_polynomial_predictions_independent_lstsq",ns["y_test"],expected,atol=1e-6)
            regression_class=type(ns["model"].named_steps["linearregression"])
            x=np.linspace(-1,1,33)
            target=4+2*x-3*x*x+.5*x*x*x
            moderate=np.column_stack([x,2*x*x,3*x*x*x])
            for normalize in [False,True]:
                estimator=regression_class(fit_intercept=True,normalize=normalize)
                prediction=estimator.fit(moderate,target).predict(moderate)
                close("normalization_moderate_scale_"+str(normalize),prediction,target,atol=1e-8)
            separated=np.column_stack([x,1e-9*x*x,1e9*x*x*x])
            estimator=regression_class(fit_intercept=True,normalize=True)
            prediction=estimator.fit(separated,target).predict(separated)
            close("normalization_scale_separated_boundary",prediction,target,atol=1e-6)
        else:
            add("known_case",False,{"case":case})
    except Exception as error:
        add("independent_checker_completed",False,{"type":type(error).__name__,"message":str(error)})
    return rows
