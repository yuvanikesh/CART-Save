"""
CartGuard AI — Combined Real + Synthetic Training Pipeline
Blends real session data (from 2019-Oct.csv, processed) with synthetic
sessions (to cover payment-failure / friction patterns absent from the
real file) before training the EnsembleRiskModel.

FIX (validation leakage): the previous version validated on a random split
of the BLENDED data, so the held-out set still contained synthetic sessions
whose 6 archetypes are easy to separate — that's why AUC hit 1.0000 even
after de-leaking individual features. This version holds out a REAL-ONLY
test set before any synthetic data is added, trains on
(real_train + synthetic), and reports the honest metric on real_test only.

Usage (from backend/):
    python scripts/train_combined_model.py --n_synthetic 8000
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.ensemble_model import EnsembleRiskModel, engineer_features, FEATURE_COLUMNS
from utils.synthetic_data import generate_synthetic_sessions


def load_real_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run scripts/build_dataset_oct.py first."
        )
    df = pd.read_parquet(path)
    df["session_type"] = "real_2019oct"
    print(f"Loaded {len(df):,} real sessions from {path}")
    print(f"  Real abandonment rate: {df['abandoned'].mean():.2%}")
    return df


def load_synthetic_data(n_samples: int) -> pd.DataFrame:
    sessions = generate_synthetic_sessions(n_samples)
    df = pd.DataFrame(sessions)
    df["source_dataset"] = "synthetic"
    print(f"Generated {len(df):,} synthetic sessions")
    print(f"  Synthetic abandonment rate: {df['abandoned'].mean():.2%}")
    return df


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    df["payment_failure_rate"] = df["payment_failures"] / df["payment_attempts"].clip(lower=1)
    df["view_to_cart_ratio"] = df["product_views"] / df["cart_adds"].clip(lower=1)
    df["cart_value_log"] = np.log1p(df["cart_value"].fillna(0))
    df["checkout_completion_rate"] = df["checkout_steps_completed"] / 5.0
    df["session_productivity"] = df["cart_adds"] / (df["session_duration"] / 60.0).clip(lower=0.1)
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--real_path", default="data/processed/dataset1_clean.parquet")
    parser.add_argument("--n_synthetic", type=int, default=8000,
                         help="Number of synthetic sessions to blend in")
    parser.add_argument("--real_test_size", type=float, default=0.2,
                         help="Fraction of REAL data held out (never used for training)")
    parser.add_argument("--eval_cart_adds_only", action="store_true",
                         help="Report real-holdout metrics only on sessions with cart_adds > 0 "
                              "(the genuine 'cart abandonment' cases, not trivial browse-only sessions)")
    parser.add_argument("--output_dir", default="models")
    parser.add_argument("--save_combined", default="data/training/merged_training_data.parquet")
    args = parser.parse_args()

    real_df = load_real_data(args.real_path)

    # Hold out real data BEFORE touching synthetic data or feature engineering,
    # so nothing about the real test set ever influences training.
    real_train, real_test = train_test_split(
        real_df, test_size=args.real_test_size, stratify=real_df["abandoned"],
        random_state=42,
    )
    print(f"\nReal holdout split: {len(real_train):,} train / {len(real_test):,} test (real-only)")

    synthetic_df = load_synthetic_data(args.n_synthetic)
    synthetic_df["source_dataset"] = "synthetic"

    train_combined = pd.concat([real_train, synthetic_df], ignore_index=True, sort=False)
    print(f"\nTraining pool: {len(train_combined):,} sessions "
          f"({len(real_train):,} real + {len(synthetic_df):,} synthetic)")
    print(train_combined["source_dataset"].value_counts())
    print(f"Training pool abandonment rate: {train_combined['abandoned'].mean():.2%}")

    os.makedirs(os.path.dirname(args.save_combined), exist_ok=True)
    train_combined.to_parquet(args.save_combined, index=False)
    print(f"Saved training pool to {args.save_combined}")

    print("\nEngineering features (train pool)...")
    train_combined = engineer_features(train_combined)
    train_combined = add_interaction_features(train_combined)

    X_train_pool = train_combined[FEATURE_COLUMNS].fillna(0)
    y_train_pool = train_combined["abandoned"].astype(int)

    print(f"\nTraining data shape: {X_train_pool.shape}")
    print(f"Overall abandonment rate (train pool): {y_train_pool.mean():.2%}")

    model = EnsembleRiskModel()
    model.fit(X_train_pool, y_train_pool)

    # --- Honest evaluation: REAL-ONLY holdout, never seen in any form ---
    print("\nEngineering features (real-only holdout)...")
    real_test = real_test.copy()
    real_test = engineer_features(real_test)
    real_test = add_interaction_features(real_test)

    if args.eval_cart_adds_only:
        before = len(real_test)
        real_test = real_test[real_test["cart_adds"] > 0].copy()
        print(f"\n--eval_cart_adds_only: filtered real holdout {before:,} -> {len(real_test):,} "
              f"sessions (cart_adds > 0 only)")

    X_real_test = real_test[FEATURE_COLUMNS].fillna(0)
    y_real_test = real_test["abandoned"].astype(int)
    X_real_test_scaled = model.scaler.transform(X_real_test)

    real_proba = model._ensemble_predict_proba(X_real_test, X_real_test_scaled)
    real_preds = (real_proba >= 0.5).astype(int)

    print("\n--- REAL-ONLY holdout performance (the number that matters) ---")
    print(f"Real holdout size: {len(y_real_test):,}")
    try:
        print(f"Real AUC:       {roc_auc_score(y_real_test, real_proba):.4f}")
    except ValueError as e:
        print(f"Real AUC:       could not compute ({e})")
    print(f"Real Precision: {precision_score(y_real_test, real_preds, zero_division=0):.4f}")
    print(f"Real Recall:    {recall_score(y_real_test, real_preds, zero_division=0):.4f}")
    print(f"Real F1:        {f1_score(y_real_test, real_preds, zero_division=0):.4f}")

    model.save(args.output_dir)
    print(f"\nModel saved to {args.output_dir}/")
    print("NOTE: report the REAL-ONLY holdout numbers above in your writeup/demo, "
          "not the blended-validation AUC — the blended set includes synthetic "
          "archetypes that are much easier to separate than real behavior.")


if __name__ == "__main__":
    main()