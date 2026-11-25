"""Fit the unsupervised latent model on the profile corpus and save it to models/.
Run: python ml/build_dataset.py && python ml/train_embedding.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from paths import PROCESSED, MODELS, SEED
from roomsync_ml.embedding import LatentModel


def main():
    profiles = json.loads((PROCESSED / "profiles.json").read_text())
    m = LatentModel(seed=SEED).fit(profiles)
    MODELS.mkdir(exist_ok=True)
    m.save(MODELS / "latent_model.joblib")
    meta = {"n_profiles": len(profiles), "n_components": int(m.pca.n_components_),
            "explained_variance_cumulative": float(sum(m.explained_variance())),
            "sigma2": m.sigma2, "k_silhouette": {str(k): round(v, 4) for k, v in m.k_scores.items()},
            "chosen_k": int(m.kmeans.n_clusters), "archetypes": m.describe_archetypes(profiles),
            "trained_on": "synthetic demo profiles only (unsupervised; no labels)", "seed": SEED}
    (MODELS / "latent_model_meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))

if __name__ == "__main__":
    main()
