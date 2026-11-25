"""Supervised residual model trained on REAL roommate-satisfaction feedback (when available)."""
import joblib, numpy as np

class ResidualModel:
    def __init__(self, model, meta):
        self.model, self.meta = model, meta
    def predict_score(self, features):
        return float(np.clip(self.model.predict(np.array([features]))[0], 0, 100))
    def save(self, path): joblib.dump(self, path)
    @staticmethod
    def load(path): return joblib.load(path)
