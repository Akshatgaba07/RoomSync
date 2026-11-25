"""Unsupervised latent lifestyle model (no compatibility labels required).

Pipeline: raw features -> median imputation -> standardisation -> PCA -> Gaussian-kernel similarity.
Also fits KMeans lifestyle archetypes (k chosen by silhouette) for UI descriptions.
"""
from __future__ import annotations

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .preprocess import MedianImputer, feature_names, raw_feature_vector
from . import schema as S

N_LIFESTYLE = len(feature_names()) - len(S.PRIORITIES)  # drop priority one-hots from the embedding


class LatentModel:
    def __init__(self, var_target: float = 0.80, seed: int = 42, k_range=(3, 7)):
        self.var_target, self.seed, self.k_range = var_target, seed, k_range
        self.imputer = MedianImputer()
        self.scaler = StandardScaler()
        self.pca: PCA | None = None
        self.kmeans: KMeans | None = None
        self.sigma2: float = 1.0
        self.k_scores: dict[int, float] = {}
        self.names = feature_names()[:N_LIFESTYLE]

    def _raw(self, profiles) -> np.ndarray:
        return np.vstack([raw_feature_vector(p)[:N_LIFESTYLE] for p in profiles])

    def _z(self, X: np.ndarray) -> np.ndarray:
        return self.pca.transform(self.scaler.transform(self.imputer.transform(X)))

    def fit(self, profiles) -> "LatentModel":
        X = self._raw(profiles)
        Xi = self.imputer.fit(X).transform(X)
        Xs = self.scaler.fit_transform(Xi)
        full = PCA(random_state=self.seed).fit(Xs)
        n = int(np.searchsorted(np.cumsum(full.explained_variance_ratio_), self.var_target) + 1)
        self.pca = PCA(n_components=n, random_state=self.seed).fit(Xs)
        Z = self.pca.transform(Xs)
        d2 = ((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)
        iu = np.triu_indices(len(Z), 1)
        self.sigma2 = float(np.median(d2[iu])) or 1.0
        best_k, best_s = None, -1.0
        for k in range(self.k_range[0], min(self.k_range[1], len(Z) - 1) + 1):
            km = KMeans(n_clusters=k, n_init=10, random_state=self.seed).fit(Z)
            s = float(silhouette_score(Z, km.labels_))
            self.k_scores[k] = s
            if s > best_s:
                best_k, best_s, self.kmeans = k, s, km
        self.best_silhouette = best_s
        return self

    def embed(self, profile) -> np.ndarray:
        return self._z(self._raw([profile]))[0]

    def similarity(self, a, b) -> float:
        d2 = float(((self.embed(a) - self.embed(b)) ** 2).sum())
        return float(np.exp(-d2 / (2 * self.sigma2)))

    def archetype(self, profile) -> int:
        return int(self.kmeans.predict(self.embed(profile)[None, :])[0])

    def describe_archetypes(self, profiles, top: int = 3) -> dict[int, list[str]]:
        """Describe each cluster by its most over/under-represented raw features (z-scores)."""
        X = self.imputer.transform(self._raw(profiles))
        Xs = self.scaler.transform(X)
        labels = self.kmeans.predict(self.pca.transform(Xs))
        out = {}
        for c in sorted(set(labels)):
            m = Xs[labels == c].mean(0)
            idx = np.argsort(-np.abs(m))[:top]
            out[int(c)] = [f"{'high' if m[i] > 0 else 'low'} {self.names[i]} (z={m[i]:+.2f}, n={int((labels == c).sum())})"
                           for i in idx]
        return out

    def explained_variance(self) -> list[float]:
        return [float(x) for x in self.pca.explained_variance_ratio_]

    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path) -> "LatentModel":
        return joblib.load(path)
