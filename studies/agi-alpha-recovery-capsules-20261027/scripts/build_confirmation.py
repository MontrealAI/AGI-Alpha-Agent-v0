# SPDX-License-Identifier: Apache-2.0
import difflib, hashlib, json
from pathlib import Path
from build_capsules import ROOT, RULES

LEGACY_REGRESSION = """from sklearn.base import BaseEstimator, RegressorMixin
import numpy as np
from scipy import linalg

class LinearRegression(RegressorMixin, BaseEstimator):
    def __init__(self, fit_intercept=True, normalize=False):
        self.fit_intercept = fit_intercept
        self.normalize = normalize
    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        self.n_features_in_ = X.shape[1]
        self.x_offset_ = X.mean(axis=0) if self.fit_intercept else np.zeros(X.shape[1])
        self.y_offset_ = y.mean(axis=0) if self.fit_intercept else 0.0
        centered = X - self.x_offset_
        self.x_scale_ = np.sqrt((centered ** 2).sum(axis=0)) if self.normalize and self.fit_intercept else np.ones(X.shape[1])
        self.x_scale_[self.x_scale_ == 0] = 1.0
        coefficient, _, self.rank_, self.singular_ = linalg.lstsq(centered / self.x_scale_, y - self.y_offset_)
        self.coef_ = coefficient / self.x_scale_
        self.intercept_ = self.y_offset_ - self.x_offset_ @ self.coef_
        return self
    def predict(self, X):
        return np.asarray(X, dtype=float) @ self.coef_ + self.intercept_
"""


def build(path):
    raw = path.read_bytes()
    doc = json.loads(raw)
    case = path.stem
    changes = []
    for i, cell in enumerate(doc["cells"]):
        before = "".join(cell["source"])
        code = before
        rules = list(RULES)
        rules.extend(
            [
                (
                    "from sklearn.cross_validation import",
                    "from sklearn.model_selection import",
                    "Preserve split parameters using the supported module.",
                ),
                (
                    "from sklearn.learning_curve import",
                    "from sklearn.model_selection import",
                    "Use supported validation/learning-curve namespace.",
                ),
                (
                    "from sklearn.grid_search import",
                    "from sklearn.model_selection import",
                    "Preserve the full grid and seven folds.",
                ),
                ("LeaveOneOut(len(X))", "LeaveOneOut()", "The modern splitter obtains sample count from data."),
                (
                    "'polynomialfeatures__degree', degree, cv=7",
                    "param_name='polynomialfeatures__degree', param_range=degree, cv=7",
                    "Preserve hyperparameter range with modern keyword-only signature.",
                ),
                (
                    "plt.plot(X_test.ravel(), y_test, hold=True)",
                    "plt.plot(X_test.ravel(), y_test)",
                    "Modern axes already retain prior artists; removed hold flag.",
                ),
            ]
        )
        if case.startswith("03.02"):
            rules.extend(
                [
                    (
                        "pd.DataFrame({'area':area, 'pop':pop})",
                        "pd.DataFrame({'area':area, 'pop':pop}).sort_index()",
                        "Preserve archived alphabetical row ordering instead of modern dict-insertion order.",
                    ),
                    (
                        "data.ix[:3, :'pop']",
                        "data.iloc[:3].loc[:, :'pop']",
                        "Explicit positional rows and label columns preserve the mixed-index operation.",
                    ),
                ]
            )
        if case.startswith("03.05"):
            rules.extend(
                [
                    (
                        "labels=[[0, 0, 1, 1], [0, 1, 0, 1]]",
                        "codes=[[0, 0, 1, 1], [0, 1, 0, 1]]",
                        "Renamed MultiIndex label-code constructor argument.",
                    ),
                    (
                        "health_data.mean(level='year')",
                        "health_data.groupby(level='year').mean()",
                        "Explicit grouped mean preserves year aggregation.",
                    ),
                    (
                        "data_mean.mean(axis=1, level='type')",
                        "data_mean.T.groupby(level='type').mean().T",
                        "Preserve column-level means without removed axis-level keyword.",
                    ),
                ]
            )
            if i == 31:
                code = (
                    "_demonstration_source = "
                    + repr(before)
                    + "\ntry:\n    compile(_demonstration_source, '<intentional-syntax-demonstration>', 'exec')\nexcept SyntaxError as expected_error:\n    print('Expected SyntaxError:', expected_error.msg)\nelse:\n    raise AssertionError('The original invalid slice must raise SyntaxError')"
                )
                cell["metadata"]["expected_demonstration"] = (
                    "SyntaxError in the archived invalid slice is explicitly preserved."
                )
                changes.append(
                    {
                        "cell": i,
                        "old": before,
                        "new": code,
                        "reason": "Account for the original intentional invalid-syntax example; catch only its specified SyntaxError.",
                    }
                )
        if case.startswith("05.02"):
            csv = (ROOT / "inputs/iris.csv").read_text()
            rules.extend(
                [
                    (
                        "iris = sns.load_dataset('iris')",
                        "import pandas as pd\nfrom io import StringIO\n_iris_source_csv = "
                        + repr(csv)
                        + "\niris = pd.read_csv(StringIO(_iris_source_csv))",
                        "Freeze the exact seaborn iris fixture for offline reruns; do not silently substitute sklearn data.",
                    ),
                    ("size=1.5", "height=1.5", "Renamed plot sizing keyword."),
                    (
                        'sns.lmplot("PCA1", "PCA2",',
                        'sns.lmplot(x="PCA1", y="PCA2",',
                        "Modern plotting uses keyword-only axis arguments.",
                    ),
                    (
                        "from sklearn.mixture import GMM",
                        "from sklearn.mixture import GaussianMixture as GMM",
                        "Use supported Gaussian mixture; algorithm/version changes are disclosed, cluster labels are not a historical equality claim.",
                    ),
                    (
                        "covariance_type='full')",
                        "covariance_type='full', random_state=0, max_iter=100, n_init=1)",
                        "Pin mixture reproducibility; do not claim equality with an unseeded legacy run.",
                    ),
                    (
                        "plt.cm.get_cmap('spectral', 10)",
                        "plt.get_cmap('Spectral', 10)",
                        "Use the registered colormap name.",
                    ),
                ]
            )
        if case.startswith("05.03"):
            rules.append(
                (
                    "from sklearn.linear_model import LinearRegression",
                    LEGACY_REGRESSION,
                    "Retain the historical normalize switch in every CV fit; centering and L2 scaling are fitted on training data only, and ignored if intercept is false. Current LAPACK results are checked, not asserted identical to old binaries.",
                )
            )
        for old, new, reason in rules:
            if old in code:
                code = code.replace(old, new)
                changes.append(
                    {
                        "cell": i,
                        "upstream_cell": cell["metadata"].get("upstream_cell_index"),
                        "old": old,
                        "new": new,
                        "reason": reason,
                    }
                )
        if i == 0:
            code = "import numpy as np\nnp.random.seed(20261027)\n" + code
            changes.append(
                {
                    "cell": i,
                    "old": "unseeded global randomness",
                    "new": "np.random.seed(20261027)",
                    "reason": "Fixed study seed for reproducible illustrative random inputs; not an assertion of equality to the archived random realization.",
                }
            )
        cell["source"] = code.splitlines(keepends=True)
        cell["outputs"] = []
        cell["execution_count"] = None
    out = ROOT / "deliveries" / case
    out.mkdir(parents=True, exist_ok=True)
    target = out / "recovered.ipynb"
    target.write_text(json.dumps(doc, indent=2) + "\n")
    (out / "changes.json").write_text(json.dumps(changes, indent=2) + "\n")
    old = ["".join(c["source"]) for c in json.loads(raw)["cells"]]
    new = ["".join(c["source"]) for c in doc["cells"]]
    (out / "migration.diff").write_text(
        "".join(
            difflib.unified_diff(
                "\n\n".join(old).splitlines(True),
                "\n\n".join(new).splitlines(True),
                fromfile="source code",
                tofile="recovered code",
            )
        )
    )
    identity = {
        "input": str(path.relative_to(ROOT)),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "output_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "code_cells": len(doc["cells"]),
        "phase": "confirmation",
        "source": doc.get("metadata", {}),
        "rules_revision": "case-specific expert repair v1 after development freeze",
    }
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(case, len(changes), "changes")


if __name__ == "__main__":
    for p in sorted((ROOT / "inputs/confirmation").glob("*.ipynb")):
        build(p)
