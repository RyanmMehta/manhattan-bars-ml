"""Synthetic data generators for mixed-type tabular data.

All generators share the interface  gen = Gen(seed).fit(df);  gen.sample(n)

  IndependentSynth   each column resampled on its own (baseline: no correlations)
  GaussianCopulaSynth  marginals + a Gaussian copula for the dependence structure
  CARTSynth          sequential CART synthesis (as in R's synthpop): each column
                     is drawn from the leaf of a tree fitted on the earlier columns
"""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


def split_types(df):
    cats = [c for c in df.columns
            if not pd.api.types.is_numeric_dtype(df[c]) or df[c].nunique() <= 2]
    nums = [c for c in df.columns if c not in cats]
    return cats, nums


class _Base:
    def __init__(self, seed=0):
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def fit(self, df):
        self.columns = list(df.columns)
        self.dtypes = df.dtypes
        self.cats, self.nums = split_types(df)
        self.int_cols = [c for c in self.nums if np.allclose(df[c].dropna() % 1, 0)]
        self.bounds = {c: (df[c].min(), df[c].max()) for c in self.nums}
        self._fit(df)
        return self

    def _finish(self, out):
        for c in self.nums:
            lo, hi = self.bounds[c]
            out[c] = out[c].clip(lo, hi)
            if c in self.int_cols:
                out[c] = out[c].round()
        return out[self.columns].astype(self.dtypes.to_dict())

    def sample(self, n, where=None, max_rounds=50):
        """Draw n rows. `where` is an optional pandas query string; rows that
        fail it are rejected and redrawn (conditional / scenario sampling)."""
        if where is None:
            return self._finish(self._sample(n)).reset_index(drop=True)
        parts, have = [], 0
        for _ in range(max_rounds):
            batch = self._finish(self._sample(max(n, 1000))).query(where)
            parts.append(batch)
            have += len(batch)
            if have >= n:
                break
        if have == 0:
            raise ValueError(f"no synthetic rows satisfy: {where}")
        return pd.concat(parts).head(n).reset_index(drop=True)


class IndependentSynth(_Base):
    def _fit(self, df):
        self.values = {c: df[c].to_numpy() for c in df.columns}

    def _sample(self, n):
        return pd.DataFrame({c: self.rng.choice(v, n) for c, v in self.values.items()})


class GaussianCopulaSynth(_Base):
    def _fit(self, df):
        n = len(df)
        z = np.empty((n, len(self.columns)))
        self.cat_levels, self.cat_cum, self.num_sorted = {}, {}, {}
        for j, c in enumerate(self.columns):
            if c in self.cats:
                freq = df[c].value_counts(normalize=True)
                cum = np.r_[0, freq.cumsum().to_numpy()]
                cum[-1] = 1.0
                self.cat_levels[c], self.cat_cum[c] = freq.index.to_numpy(), cum
                k = pd.Categorical(df[c], categories=freq.index).codes
                u = cum[k] + self.rng.uniform(size=n) * (cum[k + 1] - cum[k])
            else:
                self.num_sorted[c] = np.sort(df[c].to_numpy(dtype=float))
                ranks = stats.rankdata(df[c].to_numpy() + self.rng.uniform(0, 1e-9, n))
                u = ranks / (n + 1)
            z[:, j] = stats.norm.ppf(np.clip(u, 1e-6, 1 - 1e-6))
        corr = np.corrcoef(z, rowvar=False)
        w, v = np.linalg.eigh(corr)                     # nearest positive-definite
        self.corr = (v * np.clip(w, 1e-6, None)) @ v.T

    def _sample(self, n):
        z = self.rng.multivariate_normal(np.zeros(len(self.columns)), self.corr, size=n)
        u = stats.norm.cdf(z)
        out = {}
        for j, c in enumerate(self.columns):
            if c in self.cats:
                k = np.searchsorted(self.cat_cum[c], u[:, j], side="right") - 1
                out[c] = self.cat_levels[c][np.clip(k, 0, len(self.cat_levels[c]) - 1)]
            else:
                s = self.num_sorted[c]
                out[c] = np.interp(u[:, j] * (len(s) - 1), np.arange(len(s)), s)
        return pd.DataFrame(out)


class CARTSynth(_Base):
    def __init__(self, seed=0, min_samples_leaf=5):
        super().__init__(seed)
        self.min_samples_leaf = min_samples_leaf

    def _encode(self, df, cols):
        X = np.empty((len(df), len(cols)))
        for j, c in enumerate(cols):
            if c in self.cats:
                X[:, j] = pd.Categorical(df[c], categories=self.cat_levels[c]).codes
            else:
                X[:, j] = df[c].to_numpy(dtype=float)
        return X

    def _fit(self, df):
        df = df.reset_index(drop=True)
        self.cat_levels = {c: sorted(df[c].unique()) for c in self.cats}
        self.first = df[self.columns[0]].to_numpy()
        self.trees = []
        for j, c in enumerate(self.columns[1:], start=1):
            X = self._encode(df, self.columns[:j])
            y = df[c].to_numpy()
            Tree = DecisionTreeClassifier if c in self.cats else DecisionTreeRegressor
            yy = pd.Categorical(y, categories=self.cat_levels[c]).codes if c in self.cats else y
            tree = Tree(min_samples_leaf=self.min_samples_leaf, random_state=self.seed).fit(X, yy)
            leaves = tree.apply(X)
            donors = pd.Series(np.arange(len(y))).groupby(leaves).apply(np.array).to_dict()
            self.trees.append((c, tree, donors, y))

    def _sample(self, n):
        out = pd.DataFrame({self.columns[0]: self.rng.choice(self.first, n)})
        for j, (c, tree, donors, y) in enumerate(self.trees, start=1):
            leaves = tree.apply(self._encode(out, self.columns[:j]))
            pick = np.empty(n, dtype=int)
            for leaf in np.unique(leaves):
                mask = leaves == leaf
                pick[mask] = self.rng.choice(donors[leaf], mask.sum())
            out[c] = y[pick]
        return out


GENERATORS = {"independent": IndependentSynth, "copula": GaussianCopulaSynth, "cart": CARTSynth}
