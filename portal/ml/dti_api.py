import os
import tempfile
import zipfile
import shutil
import pandas as pd
from django.http import JsonResponse
from django.conf import settings  # ✅ For MEDIA_URL + MEDIA_ROOT

# ✅ DeepPurpose imports
from DeepPurpose import utils, DTI as models
from .dti_processor import protein_smiles_uploads


# ---------------- PHARMAL-NET TRAIN API ----------------
def pharmalnet_train_api(request):
    """Handle DTI training request, return model metrics + ZIP for download"""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        csv_file = request.FILES.get("dataset")
        smiles_col = request.POST.get("smiles_col")
        protein_col = request.POST.get("protein_col")
        value_col = request.POST.get("value_col")
        model_name = request.POST.get("model_name", "pharmalnet_model")

        if not csv_file or not smiles_col or not protein_col or not value_col:
            return JsonResponse({"error": "Please upload CSV and fill all required fields"}, status=400)

        # ✅ Save uploaded CSV temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            for chunk in csv_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        # ✅ Run training pipeline
        model_dir, zip_path, metrics, y_true, y_pred, graph_path = protein_smiles_uploads(
            file_path=tmp_path,
            model_name=model_name,
            Smiles=smiles_col,
            Protein=protein_col,
            value_name=value_col
        )

        if not metrics:
            return JsonResponse({"error": "Training failed. Please verify dataset or columns."}, status=500)

        # ✅ Build model ZIP URL (make it downloadable through /media/)
        model_zip_url = None
        if zip_path and os.path.exists(zip_path):
            # Create media directory (persistent) if not exists
            media_model_dir = os.path.join(settings.MEDIA_ROOT, "pharmalnet_models")
            os.makedirs(media_model_dir, exist_ok=True)

            # Copy the ZIP file to the media folder
            zip_filename = f"{model_name}_trained_model.zip"
            media_zip_path = os.path.join(media_model_dir, zip_filename)
            shutil.copy(zip_path, media_zip_path)

            # Build downloadable media URL
            model_zip_url = settings.MEDIA_URL.rstrip("/") + f"/pharmalnet_models/{zip_filename}"

        # ✅ Return all response data
        return JsonResponse({
            "message": "✅ Model trained successfully!",
            "metrics": metrics,
            "graph_url": graph_path,
            "model_zip": model_zip_url,   # ✅ frontend button can download directly
            "graph_data": {
                "actual": y_true,
                "predicted": y_pred
            }
        })

    except Exception as e:
        print("❌ Error in pharmalnet_train_api:", e)
        return JsonResponse({"error": f"Internal server error: {e}"}, status=500)



# ---------------- PHARMAL-NET PREDICTION API ----------------
def run_pharmalnet_prediction(request):
    """
    Perform ML prediction using DeepPurpose trained model (from ZIP or .pt/.pkl)
    """
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    try:
        model_file = request.FILES.get("model")
        if not model_file:
            return JsonResponse({"error": "Please upload a trained model file (.zip or .pkl)."}, status=400)

        # ✅ Save uploaded model temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(model_file.name)[1]) as tmp_model:
            for chunk in model_file.chunks():
                tmp_model.write(chunk)
            model_path = tmp_model.name

        # ✅ Handle ZIP model or direct model.pt/config.pkl
        model_dir = None
        if model_path.endswith(".zip"):
            extract_dir = tempfile.mkdtemp(prefix="pharmalnet_model_")
            with zipfile.ZipFile(model_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            print("📂 Extracted files structure:")
            for root, dirs, files in os.walk(extract_dir):
                print(f"  {root} → {files}")

            # ✅ Automatically detect correct model directory
            possible_dirs = []
            for root, dirs, files in os.walk(extract_dir):
                if any(f.endswith(".pt") for f in files) and any(f.endswith(".pkl") for f in files):
                    possible_dirs.append(root)

            if possible_dirs:
                model_dir = possible_dirs[0]
                print(f"✅ Found model files in: {model_dir}")
            else:
                raise ValueError("❌ Could not find model files (.pt / .pkl) in extracted ZIP.")
        else:
            model_dir = os.path.dirname(model_path)

        # ✅ Load pretrained DeepPurpose model
        try:
            model = models.model_pretrained(model_dir)
            print(f"✅ Loaded model from: {model_dir}")
        except Exception as e:
            print("❌ Model loading error:", e)
            return JsonResponse({"error": f"Failed to load DeepPurpose model: {e}"}, status=500)

        # ✅ CASE 1: CSV Prediction
        csv_file = request.FILES.get("dataset")
        if csv_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_csv:
                for chunk in csv_file.chunks():
                    tmp_csv.write(chunk)
                csv_path = tmp_csv.name

            df = pd.read_csv(csv_path)
            print(f"📄 Loaded CSV: {csv_path}")
            print(f"📊 Columns: {list(df.columns)}")

            smiles_col = request.POST.get("smiles_col", "Smiles")
            protein_col = request.POST.get("protein_col", "seq1")

            # ✅ Validate columns
            if smiles_col not in df.columns or protein_col not in df.columns:
                return JsonResponse({
                    "error": f"Missing required columns ({smiles_col}, {protein_col})"
                }, status=400)

            smiles = df[smiles_col].astype(str).dropna().tolist()
            proteins = df[protein_col].astype(str).dropna().tolist()

            print(f"🧪 SMILES count: {len(smiles)}, Protein count: {len(proteins)}")

            if not smiles or not proteins:
                return JsonResponse({
                    "error": "Empty SMILES or Protein sequence provided."
                }, status=400)

            # ✅ Convert data for DeepPurpose (⚡ FIXED HERE)
            try:
                print("🧠 Preparing data for DeepPurpose prediction...")

                # ✅ Add dummy y values for backward compatibility (fixes NoneType error)
                dummy_y = [0] * len(smiles)

                X_pred = utils.data_process(
                    X_drug=smiles,
                    X_target=proteins,
                    y=dummy_y,  # ✅ added for compatibility
                    drug_encoding=model.drug_encoding,
                    target_encoding=model.target_encoding,
                    split_method="no_split"
                )

                print(f"✅ X_pred prepared successfully — Type: {type(X_pred)}")

            except Exception as e:
                import traceback
                print("❌ Error during data processing:", e)
                print(traceback.format_exc())
                return JsonResponse({"error": f"Data preprocessing failed: {e}"}, status=500)

            if X_pred is None or len(X_pred) == 0:
                return JsonResponse({
                    "error": "Prediction data processing failed — check SMILES/Protein sequences."
                }, status=400)

            print("🚀 Running prediction...")
            y_pred = model.predict(X_pred)

            if y_pred is None:
                return JsonResponse({
                    "error": "Model failed to generate predictions. Check data or encodings."
                }, status=500)

            # ✅ Safely convert predictions for JSON serialization
        import numpy as np
        df["Predicted"] = [float(x) if pd.notna(x) and not np.isinf(x) else None for x in y_pred]

        # ✅ Drop any problematic types (like Timestamp, NumPy int/float)
        def make_json_safe(val):
            try:
                if pd.isna(val) or val in [np.inf, -np.inf]:
                    return None
                if isinstance(val, (np.generic, np.ndarray)):
                    return val.item() if hasattr(val, "item") else str(val)
                return val
            except:
                return str(val)

        safe_preview = df.head(5).applymap(make_json_safe).to_dict(orient="records")
        safe_full = df.applymap(make_json_safe).to_dict(orient="records")

        print(f"✅ Returning {len(df)} predictions safely as JSON.")

        return JsonResponse({
            "message": "✅ Prediction successful!",
            "total_records": len(df),
            "preview": safe_preview,   # shows first 5
            "full_data": safe_full     # for 'Show More'
        }, safe=False)

        # ✅ CASE 2: Manual SMILES + Protein input
        
        smiles = request.POST.get("smiles")
        protein = request.POST.get("protein")

        if smiles and protein:
            dummy_y = [0]  # ✅ Added dummy Y for compatibility
            X_pred = utils.data_process(
                X_drug=[smiles],
                X_target=[protein],
                y=dummy_y,  # ✅ fix added
                drug_encoding=model.drug_encoding,
                target_encoding=model.target_encoding,
                split_method="no_split"
            )

            if X_pred is None:
                return JsonResponse({"error": "Invalid SMILES or Protein input."}, status=400)

            y_pred = model.predict(X_pred)
            if y_pred is None:
                return JsonResponse({"error": "Prediction failed due to invalid inputs."}, status=500)

            return JsonResponse({
                "message": "✅ Prediction successful!",
                "prediction": float(y_pred[0])
            })

        return JsonResponse({"error": "No valid input provided (CSV or manual)."}, status=400)

    except Exception as e:
        print("❌ Error in run_pharmalnet_prediction:", e)
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)
