"""
CartGuard AI - ML Model Training Pipeline
Trains CatBoost + XGBoost ensemble for abandonment risk scoring.
"""
import numpy as np
import pandas as pd
import pickle
import json
import os
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (
        roc_auc_score, precision_score, recall_score, f1_score,
        classification_report, confusion_matrix
    )
    from sklearn.ensemble import GradientBoostingClassifier
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False
    class DummyScaler:
        def transform(self, X): return X
        def fit_transform(self, X): return X
        def fit(self, X, y=None): return self
    StandardScaler = DummyScaler
    GradientBoostingClassifier = object

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except Exception:
    HAS_CATBOOST = False

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except Exception:
    HAS_XGBOOST = False

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.signal_generator import BehavioralSignalGenerator
from utils.synthetic_data import generate_synthetic_sessions


FEATURE_COLUMNS = [
    "session_duration",
    "product_views",
    "cart_adds",
    "cart_removes",
    "cart_changes",
    "cart_value",
    "category_switches",
    "tab_switches",
    "page_revisits",
    "checkout_steps_completed",
    "checkout_time",
    "payment_attempts",
    "payment_failures",
    "time_on_payment_page",
    "payment_method_switches",
    "form_field_errors",
    "back_navigations",
    "is_returning_visitor",
    "session_recency_minutes",
    # Derived signals
    "hesitation_score",
    "price_sensitivity",
    "funnel_friction",
    "comparison_intent",
    "urgency_score",
    "payment_risk",
    "behavioral_risk_index",
    "engagement_score",
    # Interaction features
    "payment_failure_rate",
    "view_to_cart_ratio",
    "cart_value_log",
    "checkout_completion_rate",
    "session_productivity",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply feature engineering to raw session data."""
    gen = BehavioralSignalGenerator()
    
    # Ensure default numeric columns exist
    defaults = {
        "payment_failures": 0, "payment_attempts": 0, "product_views": 0,
        "cart_adds": 0, "cart_value": 0.0, "checkout_steps_completed": 0,
        "session_duration": 0.0
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    
    # Generate behavioral signals
    for idx, row in df.iterrows():
        signals = gen.generate_all_signals(row.to_dict())
        for k, v in signals.items():
            df.at[idx, k] = v
    
    # Interaction features
    df["payment_failure_rate"] = df["payment_failures"] / df["payment_attempts"].clip(lower=1)
    df["view_to_cart_ratio"] = df["product_views"] / df["cart_adds"].clip(lower=1)
    df["cart_value_log"] = np.log1p(df["cart_value"])
    df["checkout_completion_rate"] = df["checkout_steps_completed"] / 5.0
    df["session_productivity"] = df["cart_adds"] / (df["session_duration"] / 60.0).clip(lower=0.1)
    
    return df


class EnsembleRiskModel:
    """
    Weighted ensemble: CatBoost (fast) + XGBoost (robust) + GBT (fallback).
    """

    def __init__(self):
        self.catboost = None
        self.xgboost = None
        self.gbt = None
        self.scaler = StandardScaler()
        self.feature_columns = FEATURE_COLUMNS
        self.weights = {"catboost": 0.50, "xgboost": 0.35, "gbt": 0.15}
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        results = {}

        # CatBoost
        if HAS_CATBOOST:
            print("Training CatBoost...")
            self.catboost = CatBoostClassifier(
                iterations=300,
                learning_rate=0.05,
                depth=6,
                loss_function="Logloss",
                eval_metric="AUC",
                random_seed=42,
                verbose=50,
            )
            self.catboost.fit(X_train, y_train, eval_set=(X_val, y_val), early_stopping_rounds=30)
            cb_preds = self.catboost.predict_proba(X_val)[:, 1]
            results["catboost"] = roc_auc_score(y_val, cb_preds)
            print(f"CatBoost AUC: {results['catboost']:.4f}")

        # XGBoost
        if HAS_XGBOOST:
            print("Training XGBoost...")
            scale_pos = (y_train == 0).sum() / (y_train == 1).sum()
            self.xgboost = xgb.XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                scale_pos_weight=scale_pos,
                eval_metric="auc",
                random_state=42,
                verbosity=1,
            )
            self.xgboost.fit(
                X_train_scaled, y_train,
                eval_set=[(X_val_scaled, y_val)],
                verbose=50,
            )
            xgb_preds = self.xgboost.predict_proba(X_val_scaled)[:, 1]
            results["xgboost"] = roc_auc_score(y_val, xgb_preds)
            print(f"XGBoost AUC: {results['xgboost']:.4f}")

        # GBT fallback
        print("Training Gradient Boosting (fallback)...")
        self.gbt = GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42
        )
        self.gbt.fit(X_train_scaled, y_train)
        gbt_preds = self.gbt.predict_proba(X_val_scaled)[:, 1]
        results["gbt"] = roc_auc_score(y_val, gbt_preds)
        print(f"GBT AUC: {results['gbt']:.4f}")

        # Ensemble evaluation
        ensemble_preds = self._ensemble_predict_proba(X_val, X_val_scaled)
        results["ensemble"] = roc_auc_score(y_val, ensemble_preds)

        y_pred_binary = (ensemble_preds > 0.5).astype(int)
        print(f"\nEnsemble AUC: {results['ensemble']:.4f}")
        print(f"Precision: {precision_score(y_val, y_pred_binary):.4f}")
        print(f"Recall: {recall_score(y_val, y_pred_binary):.4f}")
        print(f"F1: {f1_score(y_val, y_pred_binary):.4f}")
        print("\nClassification Report:")
        print(classification_report(y_val, y_pred_binary))

        self.is_fitted = True
        self.val_auc = results.get("ensemble", 0)
        return results

    def _ensemble_predict_proba(self, X_raw, X_scaled):
        probs = np.zeros(len(X_raw))
        total_weight = 0

        if self.catboost and HAS_CATBOOST:
            probs += self.weights["catboost"] * self.catboost.predict_proba(X_raw)[:, 1]
            total_weight += self.weights["catboost"]

        if self.xgboost and HAS_XGBOOST:
            probs += self.weights["xgboost"] * self.xgboost.predict_proba(X_scaled)[:, 1]
            total_weight += self.weights["xgboost"]

        if self.gbt:
            probs += self.weights["gbt"] * self.gbt.predict_proba(X_scaled)[:, 1]
            total_weight += self.weights["gbt"]

        return probs / total_weight

    def predict_proba(self, session_data: dict) -> dict:
        """Predict abandonment risk for a single session."""
        df = pd.DataFrame([session_data])
        df = engineer_features(df)
        
        # Ensure all features exist
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0.0
        
        X = df[self.feature_columns].fillna(0)
        X_scaled = self.scaler.transform(X)

        probs = {}
        if self.catboost and HAS_CATBOOST:
            probs["catboost"] = float(self.catboost.predict_proba(X)[:, 1][0])
        if self.xgboost and HAS_XGBOOST:
            probs["xgboost"] = float(self.xgboost.predict_proba(X_scaled)[:, 1][0])
        if self.gbt:
            probs["gbt"] = float(self.gbt.predict_proba(X_scaled)[:, 1][0])

        ensemble = self._ensemble_predict_proba(X, X_scaled)[0]
        if np.isnan(ensemble):
            gen = BehavioralSignalGenerator()
            ensemble = gen.generate_all_signals(session_data).get("behavioral_risk_index", 0.5)
        probs["ensemble"] = float(ensemble)

        # Feature importances
        feature_importance = {}
        if self.catboost and HAS_CATBOOST:
            importances = self.catboost.get_feature_importance()
            feature_importance = {
                self.feature_columns[i]: float(importances[i])
                for i in range(min(10, len(importances)))
            }

        return {
            "risk_score": probs["ensemble"],
            "model_scores": probs,
            "top_features": feature_importance,
            "signals": {col: float(X[col].iloc[0]) for col in [
                "hesitation_score", "price_sensitivity", "funnel_friction",
                "comparison_intent", "urgency_score", "payment_risk"
            ] if col in X.columns},
        }

    def save(self, model_dir: str = "models"):
        os.makedirs(model_dir, exist_ok=True)
        if self.catboost and HAS_CATBOOST:
            self.catboost.save_model(f"{model_dir}/catboost_model.cbm")
        if self.xgboost and HAS_XGBOOST:
            self.xgboost.save_model(f"{model_dir}/xgboost_model.json")
        with open(f"{model_dir}/gbt_model.pkl", "wb") as f:
            pickle.dump(self.gbt, f)
        with open(f"{model_dir}/scaler.pkl", "wb") as f:
            pickle.dump(self.scaler, f)
        with open(f"{model_dir}/model_metadata.json", "w") as f:
            json.dump({
                "feature_columns": self.feature_columns,
                "weights": self.weights,
                "val_auc": getattr(self, "val_auc", 0),
            }, f, indent=2)
        print(f"Models saved to {model_dir}/")

    def load(self, model_dir: str = "models"):
        try:
            with open(f"{model_dir}/model_metadata.json") as f:
                meta = json.load(f)
            self.feature_columns = meta.get("feature_columns", self.feature_columns)
            self.weights = meta.get("weights", self.weights)
        except Exception as e:
            print(f"Warning loading metadata: {e}")

        if HAS_CATBOOST and os.path.exists(f"{model_dir}/catboost_model.cbm"):
            try:
                self.catboost = CatBoostClassifier()
                self.catboost.load_model(f"{model_dir}/catboost_model.cbm")
            except Exception as e:
                print(f"Notice: CatBoost model load skipped ({e})")

        if HAS_XGBOOST and os.path.exists(f"{model_dir}/xgboost_model.json"):
            try:
                self.xgboost = xgb.XGBClassifier()
                self.xgboost.load_model(f"{model_dir}/xgboost_model.json")
            except Exception as e:
                print(f"Notice: XGBoost model load skipped ({e})")

        if os.path.exists(f"{model_dir}/gbt_model.pkl"):
            try:
                with open(f"{model_dir}/gbt_model.pkl", "rb") as f:
                    self.gbt = pickle.load(f)
            except Exception as e:
                print(f"Notice: GBT pickle load skipped ({e})")

        if os.path.exists(f"{model_dir}/scaler.pkl"):
            try:
                with open(f"{model_dir}/scaler.pkl", "rb") as f:
                    self.scaler = pickle.load(f)
            except Exception as e:
                print(f"Notice: Scaler pickle load skipped ({e})")

        self.is_fitted = True
        print("ML Ensemble Model initialized & ready.")


# Global model instance
_model_instance = None


def get_model() -> EnsembleRiskModel:
    global _model_instance
    if _model_instance is None:
        _model_instance = EnsembleRiskModel()
        model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
        if os.path.exists(f"{model_dir}/model_metadata.json"):
            _model_instance.load(model_dir)
        else:
            print("WARNING: No trained model found. Training on synthetic data...")
            train_and_save_model()
    return _model_instance


def train_and_save_model(n_samples: int = 5000):
    """Train model on synthetic data if real data not available."""
    print(f"Generating {n_samples} synthetic sessions for training...")
    sessions = generate_synthetic_sessions(n_samples)
    df = pd.DataFrame(sessions)
    
    df = engineer_features(df)
    
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
    
    X = df[FEATURE_COLUMNS].fillna(0)
    y = df["abandoned"].astype(int)
    
    print(f"Training data shape: {X.shape}, Abandonment rate: {y.mean():.2%}")
    
    model = EnsembleRiskModel()
    model.fit(X, y)
    
    model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    model.save(model_dir)
    
    global _model_instance
    _model_instance = model
    return model


if __name__ == "__main__":
    print("Training CartGuard AI ensemble model...")
    model = train_and_save_model(n_samples=10000)
    print("Training complete!")
