import os
import numpy as np
import pandas as pd
import matplotlib
import tempfile
import shutil
import warnings
import traceback
import random
import zipfile

# ✅ Use non-GUI backend for server compatibility
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.metrics import mean_squared_error, r2_score
from DeepPurpose import utils, DTI as models

warnings.filterwarnings("ignore")


def protein_smiles_uploads(
    file_path,
    model_name="pharmalnet_model",
    Smiles="Smiles",
    Protein="seq1",
    value_name="Value"
):
    try:
        print(f"✅ Loading dataset: {file_path}")
        df = pd.read_csv(file_path)
        print("✅ Original rows:", len(df))
        print(f"📊 Columns found: {list(df.columns)}")

        # ✅ Validate columns
        if Smiles not in df.columns or Protein not in df.columns or value_name not in df.columns:
            raise ValueError(f"❌ Column names not found! Available columns: {list(df.columns)}")

        # ✅ Clean dataset
        df = df.dropna(subset=[Smiles, Protein, value_name]).copy()
        df["seq_len"] = df[Protein].astype(str).apply(len)
        df = df[df[value_name].astype(float) > 0].copy()
        df["normalized"] = np.log10(df[value_name].astype(float))
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
        print("✅ Cleaned rows:", len(df))

        X_drugs = df[Smiles].astype(str).tolist()
        X_targets = df[Protein].astype(str).tolist()
        y = df["normalized"].astype(float).tolist()

        # ✅ Random split
        seed = random.randint(1, 9999)
        print(f"🔁 Using random split seed: {seed}")

        train, val, test = utils.data_process(
            X_drugs, X_targets, y,
            drug_encoding="Morgan",
            target_encoding="Conjoint_triad",
            split_method="random",
            frac=[0.7, 0.1, 0.2],
            random_seed=seed
        )

        # ✅ Model config
        config = utils.generate_config(
            drug_encoding="Morgan",
            target_encoding="Conjoint_triad",
            cls_hidden_dims=[512, 256],
            train_epoch=10,
            LR=0.0005,
            batch_size=32
        )

        model = models.model_initialize(**config)
        print("🚀 Training started...")
        model.train(train, val, test)
        print("✅ Training complete!")

        # ✅ Evaluate
        y_pred = model.predict(test)
        y_true = pd.Series(test.Label.values)

        r2 = float(r2_score(y_true, y_pred))
        mse = float(mean_squared_error(y_true, y_pred))
        corr = float(np.corrcoef(y_true, y_pred)[0, 1])
        metrics = {"R2": r2, "MSE": mse, "Corr": corr}
        print(f"📈 R²: {r2:.3f}, MSE: {mse:.3f}, Corr: {corr:.3f}")

        # ✅ Plot Actual vs Predicted
        plt.figure(figsize=(8, 6))
        plt.scatter(y_true, y_pred, alpha=0.6, color="#007bff", label="Data Points")

        # Regression line
        m, b = np.polyfit(y_true, y_pred, 1)
        plt.plot(y_true, m * np.array(y_true) + b, color="black", linestyle="--", linewidth=1.5, label="Best Fit Line")

        # Ideal diagonal
        lim_min, lim_max = float(min(y_true.min(), np.min(y_pred))), float(max(y_true.max(), np.max(y_pred)))
        plt.plot([lim_min, lim_max], [lim_min, lim_max], "r--", linewidth=1, label="Ideal Fit (y=x)")

        plt.xlabel("Actual Values (log10 IC50)")
        plt.ylabel("Predicted Values (log10 IC50)")
        plt.title("Actual vs Predicted — Pharmal-Net")
        plt.legend()
        plt.tight_layout()

        # ✅ Save model to temp directory
        temp_dir = tempfile.mkdtemp(prefix="pharmalnet_")
        model_dir = os.path.join(temp_dir, model_name)
        os.makedirs(model_dir, exist_ok=True)

        model.save_model(model_dir)  # ⬅️ saves model.pt, config.pkl, result.pkl

        # ✅ Save graph & metrics
        graph_path = os.path.join(model_dir, "graph.png")
        plt.savefig(graph_path, dpi=300)
        plt.close()

        metrics_path = os.path.join(model_dir, "metrics.txt")
        with open(metrics_path, "w") as f:
            for k, v in metrics.items():
                f.write(f"{k}: {v}\n")

        # ✅ Create clean ZIP manually (flat structure, no nested folder)
        zip_path = os.path.join(temp_dir, f"{model_name}_trained_model.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(model_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # ⛔ Skip existing or empty zips
                    if file.endswith(".zip") or os.path.getsize(file_path) == 0:
                        continue
                    arcname = os.path.basename(file_path)  # keep flat structure
                    zipf.write(file_path, arcname)

        print(f"💾 Model folder zipped successfully at: {zip_path}")

        return (
            model_dir,
            zip_path,
            metrics,
            y_true.tolist() if hasattr(y_true, "tolist") else list(y_true),
            y_pred if isinstance(y_pred, list) else y_pred.tolist(),
            graph_path
        )

    except Exception as e:
        print("❌ Error in protein_smiles_uploads:", e)
        print(traceback.format_exc())
        return None, None, None, [], [], None
