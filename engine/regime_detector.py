"""
Phase 4 — Regime Detection Neural Network
Classifies market into 8 regimes using 58 signal features.

Regimes:
0: Bull (Strong)      — strong uptrend, low vol, risk-on
1: Bull (Late Cycle)  — uptrend but defensive signals emerging
2: Stable/Sideways    — low vol, no clear direction
3: Volatile           — high uncertainty, choppy markets
4: Bear (Mild)        — moderate downtrend, elevated vol
5: Bear (Severe)      — strong downtrend, high vol
6: Crisis             — systemic stress, correlation spike
7: Recovery           — early cycle, coming out of bear/crisis
"""

import os
import sys
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

REGIME_NAMES = [
    "Bull (Strong)", "Bull (Late Cycle)", "Stable/Sideways",
    "Volatile", "Bear (Mild)", "Bear (Severe)", "Crisis", "Recovery"
]

CHECKPOINT_DIR = os.path.expanduser("~/tradingbot/engine/checkpoints")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)


# ── Model Architecture ─────────────────────────────────────────

class RegimeDetector(nn.Module):
    """
    Enhanced regime detection network with temporal attention.
    Input:  58 market signal features
    Output: 8 regime probabilities (soft classification)
    """
    def __init__(self, n_signals=58, n_regimes=8, dropout=0.2):
        super().__init__()

        # Signal encoder
        self.encoder = nn.Sequential(
            nn.Linear(n_signals, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.LayerNorm(32),
            nn.GELU(),
        )

        # Multi-head attention over signal groups
        self.attention = nn.MultiheadAttention(
            embed_dim=32, num_heads=4, dropout=dropout, batch_first=True)

        # Regime classifier
        self.classifier = nn.Sequential(
            nn.Linear(32, 32),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(32, n_regimes),
        )

        self.n_signals = n_signals
        self.n_regimes = n_regimes

    def forward(self, x):
        # x: (batch, n_signals)
        encoded = self.encoder(x)  # (batch, 32)

        # Attention over encoded features
        attn_input = encoded.unsqueeze(1)  # (batch, 1, 32)
        attn_out, _ = self.attention(attn_input, attn_input, attn_input)
        attn_out = attn_out.squeeze(1)  # (batch, 32)

        # Residual connection
        out = encoded + attn_out

        # Classify — return raw logits (CrossEntropyLoss applies softmax)
        return self.classifier(out)

    def predict_proba(self, x):
        """Return softmax probabilities for inference."""
        return torch.softmax(self.forward(x), dim=-1)


# ── Training Data Generation ───────────────────────────────────

def generate_training_data(n_samples=10000):
    """
    Generate synthetic training data by simulating different
    market regimes and their corresponding signal patterns.

    In production this would be replaced with historically labeled data.
    For now we use domain knowledge to create realistic signal patterns
    for each regime.
    """
    np.random.seed(42)

    # Signal patterns per regime (mean values for each of 58 features)
    # Features: [market(16), momentum(14), sentiment(12), macro(16)]
    regime_patterns = {
        0: {  # Bull Strong
            "vix_z": -1.0, "yield_curve": 0.5, "credit": 1.0,
            "dollar": 0.0, "commodity": 0.5, "momentum": 1.5,
            "sector_cyclical": 1.0, "factor_growth": 1.0,
            "news_sentiment": 0.8, "insider": 0.3,
            "unemployment": 0.5, "cpi": 0.0, "gdp": 1.0,
            "lei": 0.5, "consumer": 0.5,
        },
        1: {  # Bull Late Cycle
            "vix_z": 0.0, "yield_curve": 0.2, "credit": 0.5,
            "dollar": 0.3, "commodity": 0.8, "momentum": 0.5,
            "sector_cyclical": 0.3, "factor_growth": -0.3,
            "news_sentiment": 0.3, "insider": -0.5,
            "unemployment": 0.2, "cpi": 0.8, "gdp": 0.5,
            "lei": -0.2, "consumer": 0.0,
        },
        2: {  # Stable
            "vix_z": -0.5, "yield_curve": 0.3, "credit": 0.3,
            "dollar": 0.0, "commodity": 0.0, "momentum": 0.2,
            "sector_cyclical": 0.0, "factor_growth": 0.0,
            "news_sentiment": 0.1, "insider": 0.0,
            "unemployment": 0.0, "cpi": -0.2, "gdp": 0.3,
            "lei": 0.0, "consumer": 0.1,
        },
        3: {  # Volatile
            "vix_z": 1.5, "yield_curve": 0.0, "credit": -0.5,
            "dollar": 0.5, "commodity": -0.3, "momentum": -0.5,
            "sector_cyclical": -0.5, "factor_growth": -0.5,
            "news_sentiment": -0.5, "insider": -0.3,
            "unemployment": 0.3, "cpi": 0.5, "gdp": 0.0,
            "lei": -0.3, "consumer": -0.5,
        },
        4: {  # Bear Mild
            "vix_z": 1.0, "yield_curve": -0.3, "credit": -1.0,
            "dollar": 0.8, "commodity": -0.5, "momentum": -1.0,
            "sector_cyclical": -1.0, "factor_growth": -0.8,
            "news_sentiment": -0.8, "insider": -0.5,
            "unemployment": 0.5, "cpi": 0.3, "gdp": -0.5,
            "lei": -0.5, "consumer": -0.8,
        },
        5: {  # Bear Severe
            "vix_z": 2.0, "yield_curve": -0.8, "credit": -2.0,
            "dollar": 1.5, "commodity": -1.0, "momentum": -2.0,
            "sector_cyclical": -1.5, "factor_growth": -1.5,
            "news_sentiment": -1.5, "insider": -0.8,
            "unemployment": 1.0, "cpi": -0.5, "gdp": -1.5,
            "lei": -1.0, "consumer": -1.5,
        },
        6: {  # Crisis
            "vix_z": 3.0, "yield_curve": -1.5, "credit": -3.0,
            "dollar": 2.0, "commodity": -1.5, "momentum": -3.0,
            "sector_cyclical": -2.0, "factor_growth": -2.0,
            "news_sentiment": -2.0, "insider": -1.0,
            "unemployment": 2.0, "cpi": -1.0, "gdp": -3.0,
            "lei": -2.0, "consumer": -2.0,
        },
        7: {  # Recovery
            "vix_z": 0.5, "yield_curve": 0.0, "credit": 0.0,
            "dollar": -0.5, "commodity": 0.5, "momentum": 0.3,
            "sector_cyclical": 0.5, "factor_growth": 0.5,
            "news_sentiment": 0.2, "insider": 0.5,
            "unemployment": -0.3, "cpi": -0.5, "gdp": 0.5,
            "lei": 0.5, "consumer": 0.3,
        },
    }

    X = []
    y = []

    samples_per_regime = n_samples // 8

    for regime_id, pattern in regime_patterns.items():
        for _ in range(samples_per_regime):
            # Build 58-feature vector with LOW noise for clear separation
            noise = 0.15  # much lower noise
            features = np.zeros(58)

            # Market signals (16 features)
            features[0] = pattern["vix_z"] + np.random.normal(0, noise)
            features[1] = 1.0 if pattern["vix_z"] > 2 else 0.0
            features[2] = pattern["yield_curve"] + np.random.normal(0, noise)
            features[3] = 1.0 if pattern["yield_curve"] < -0.5 else 0.0
            features[4:8] = pattern["yield_curve"] + np.random.normal(0, noise, 4)
            features[8:10] = pattern["credit"] + np.random.normal(0, noise, 2)
            features[10:12] = pattern["dollar"] + np.random.normal(0, noise, 2)
            features[12:16] = pattern["commodity"] + np.random.normal(0, noise, 4)

            # Momentum signals (14 features)
            features[16:18] = pattern["momentum"] + np.random.normal(0, noise, 2)
            features[18:20] = pattern["sector_cyclical"] + np.random.normal(0, noise, 2)
            features[20:22] = pattern["factor_growth"] + np.random.normal(0, noise, 2)
            features[22:25] = pattern["momentum"] * 0.7 + np.random.normal(0, noise, 3)
            features[25:30] = pattern["momentum"] + np.random.normal(0, noise, 5)

            # Sentiment signals (12 features)
            features[30:32] = pattern["news_sentiment"] + np.random.normal(0, noise, 2)
            features[32:34] = pattern["insider"] + np.random.normal(0, noise, 2)
            features[34:36] = -pattern["vix_z"] * 0.5 + np.random.normal(0, noise, 2)
            features[36:38] = -pattern["momentum"] * 0.3 + np.random.normal(0, noise, 2)
            features[38:40] = pattern["momentum"] * 0.4 + np.random.normal(0, noise, 2)
            features[40:42] = pattern["gdp"] * 0.5 + np.random.normal(0, noise, 2)

            # Macro signals (16 features)
            features[42:44] = pattern["gdp"] + np.random.normal(0, noise, 2)
            features[44:46] = pattern["gdp"] + np.random.normal(0, noise, 2)
            features[46:48] = -pattern["unemployment"] + np.random.normal(0, noise, 2)
            features[48:50] = pattern["cpi"] + np.random.normal(0, noise, 2)
            features[50:52] = pattern["cpi"] * 0.7 + np.random.normal(0, noise, 2)
            features[52:54] = pattern["gdp"] + np.random.normal(0, noise, 2)
            features[54:56] = pattern["consumer"] + np.random.normal(0, noise, 2)
            features[56:58] = pattern["lei"] + np.random.normal(0, noise, 2)

            features = np.clip(features, -3, 3)
            X.append(features)
            y.append(regime_id)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


# ── Training ───────────────────────────────────────────────────

def train_regime_detector(n_epochs=200, n_samples=10000, lr=0.005):
    """Train the regime detection model."""
    print("=" * 55)
    print("TRAINING REGIME DETECTOR")
    print("=" * 55)
    print(f"Device: {device}")
    print(f"Epochs: {n_epochs}")
    print(f"Training samples: {n_samples}")

    # Generate training data
    print("\nGenerating training data...")
    X, y = generate_training_data(n_samples)
    print(f"Data shape: {X.shape} → {y.shape}")
    print(f"Regime distribution: {np.bincount(y)}")

    # Shuffle before splitting — data is generated in regime order
    perm = np.random.permutation(len(X))
    X, y = X[perm], y[perm]

    # Split train/val
    split = int(0.85 * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    X_train_t = torch.tensor(X_train).to(device)
    y_train_t = torch.tensor(y_train).to(device)
    X_val_t = torch.tensor(X_val).to(device)
    y_val_t = torch.tensor(y_val).to(device)

    train_ds = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True)

    # Model
    model = RegimeDetector(n_signals=58, n_regimes=8).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, n_epochs)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    print(f"\nModel parameters: {sum(p.numel() for p in model.parameters()):,}")
    print("\nTraining...")

    best_val_acc = 0
    best_epoch = 0
    train_start = time.time()

    for epoch in range(n_epochs):
        # Train
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            probs = model(X_batch)
            loss = criterion(probs, y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        # Validate
        if (epoch + 1) % 20 == 0 or epoch == 0:
            model.eval()
            with torch.no_grad():
                val_probs = model(X_val_t)
                val_loss = criterion(val_probs, y_val_t).item()
                val_preds = val_probs.argmax(dim=-1)
                val_acc = (val_preds == y_val_t).float().mean().item()

            avg_train_loss = train_loss / len(train_loader)
            elapsed = time.time() - train_start
            print(f"  Epoch {epoch+1:>3}/{n_epochs} | "
                  f"train_loss={avg_train_loss:.4f} | "
                  f"val_loss={val_loss:.4f} | "
                  f"val_acc={val_acc*100:.1f}% | "
                  f"time={elapsed:.0f}s")

            # Save best checkpoint
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_epoch = epoch + 1
                checkpoint_path = os.path.join(
                    CHECKPOINT_DIR, "regime_detector_best.pt")
                torch.save({
                    "epoch": epoch,
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "val_acc": val_acc,
                    "val_loss": val_loss,
                }, checkpoint_path)

    # Keep only best 3 checkpoints
    _cleanup_checkpoints()

    print(f"\n{'='*55}")
    print(f"Training complete!")
    print(f"Best val accuracy: {best_val_acc*100:.1f}% at epoch {best_epoch}")
    print(f"Total time: {time.time()-train_start:.0f}s")
    print(f"Checkpoint: {CHECKPOINT_DIR}/regime_detector_best.pt")

    return model, best_val_acc


def _cleanup_checkpoints():
    """Keep only the 3 most recent checkpoints."""
    import glob
    checkpoints = sorted(glob.glob(
        os.path.join(CHECKPOINT_DIR, "*.pt")))
    for old in checkpoints[:-3]:
        os.remove(old)


# ── Inference ──────────────────────────────────────────────────

class RegimePredictor:
    """Loads trained model and runs inference on signal vectors."""

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        checkpoint_path = os.path.join(
            CHECKPOINT_DIR, "regime_detector_best.pt")
        if not os.path.exists(checkpoint_path):
            print("No trained model found. Run train_regime_detector() first.")
            return
        checkpoint = torch.load(checkpoint_path, map_location=device)
        self.model = RegimeDetector(n_signals=58, n_regimes=8).to(device)
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()
        print(f"Regime detector loaded "
              f"(val_acc={checkpoint['val_acc']*100:.1f}%)")

    def predict(self, signal_vector):
        """
        Predict regime probabilities from signal vector.
        Returns: dict of regime -> probability
        """
        if self.model is None:
            return None

        with torch.no_grad():
            x = torch.tensor(signal_vector, dtype=torch.float32).unsqueeze(0).to(device)
            probs = self.model.predict_proba(x).squeeze(0).cpu().numpy()

        result = {name: float(prob)
                  for name, prob in zip(REGIME_NAMES, probs)}

        # Top regime
        top_idx = probs.argmax()
        result["top_regime"] = REGIME_NAMES[top_idx]
        result["top_probability"] = float(probs[top_idx])
        result["probabilities"] = probs.tolist()

        return result

    def predict_verbose(self, signal_vector):
        """Print regime probabilities."""
        result = self.predict(signal_vector)
        if not result:
            return None
        print("\n" + "=" * 45)
        print("MARKET REGIME DETECTION")
        print("=" * 45)
        for name in REGIME_NAMES:
            prob = result[name]
            bar = "█" * int(prob * 30)
            print(f"  {name:<20} {prob*100:5.1f}% {bar}")
        print(f"\n  → TOP REGIME: {result['top_regime']}")
        print(f"  → CONFIDENCE: {result['top_probability']*100:.1f}%")
        print("=" * 45)
        return result


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    # Train the model
    model, val_acc = train_regime_detector(
        n_epochs=200,
        n_samples=10000,
        lr=0.001,
    )

    # Test inference with today's real signals
    print("\nTesting with today's real signals...")
    predictor = RegimePredictor()

    # Use the signal vector from our earlier run
    real_signals = np.array([
        -0.47, 0.0, 1.02, 0.0, 0.23, 0.42, 0.42, 0.0,
         2.87, 0.21, 0.86, -0.09, -0.38, 0.74, 1.49, 0.65,
         0.42, 1.0, 1.0, 0.0, -1.0, 0.40, 0.09, -0.13,
         0.52, 0.01, 0.41, 0.81, 1.89, 1.08, 1.56, 0.84,
        -3.0, -3.0, 0.34, 0.0, -0.21, 0.0, -0.5, 1.05,
         0.0, 0.0, 3.0, 1.02, 3.0, 3.0, 1.0, 0.0,
         0.97, -0.36, -0.44, 0.0, 0.5, 1.0, -0.91, -0.76,
         0.17, 0.0
    ], dtype=np.float32)

    result = predictor.predict_verbose(real_signals)
