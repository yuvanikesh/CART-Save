"""
CartGuard AI - Model Training Script
Run this to train the ML ensemble on synthetic data.
Usage: python scripts/train_model.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from models.ensemble_model import train_and_save_model

if __name__ == "__main__":
    print("=" * 60)
    print("CartGuard AI — Model Training Pipeline")
    print("=" * 60)
    
    n_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    print(f"Training on {n_samples} synthetic sessions...")
    
    model = train_and_save_model(n_samples=n_samples)
    
    print("\n" + "=" * 60)
    print("✅ Training complete! Model saved to backend/models/")
    print("=" * 60)
