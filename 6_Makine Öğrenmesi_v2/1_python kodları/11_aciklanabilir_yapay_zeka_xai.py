import sys
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.inspection import PartialDependenceDisplay
import shap

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 11 (XAI: SHAP & PDP) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "11_XAI")
reg_models_dir = os.path.join(ml_dir, "4_modeller", "6_Regresyon_Analizi")

os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

input_path = os.path.join(islenmis_dir, f"5_BIST_{currency}_Scaled.xlsx")
if not os.path.exists(input_path):
    print(f"Hata: {input_path} bulunamadı! Lütfen önce Adım 5'i çalıştırın.")
    sys.exit(1)

xl = pd.ExcelFile(input_path)
sheet_names = xl.sheet_names

# Zaman kazanmak için ilk 2 sektörde XAI yapalım (Sanayi ve Finans)
sectors_to_explain = [s for s in sheet_names if "SANAY" in s.upper() or "FINANS" in s.upper()][:2]
if not sectors_to_explain:
    sectors_to_explain = sheet_names[:2]

for sheet in sectors_to_explain:
    print(f"\nComputing SHAP and PDP for Sector: {sheet}")
    df = pd.read_excel(input_path, sheet_name=sheet)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    X_test = df[df["Dönem"] >= 32][numeric_features].fillna(0.0).reset_index(drop=True)
    
    # Load champion model
    model_cache_path = os.path.join(reg_models_dir, f"champion_{sheet}_{currency}.pkb")
    if not os.path.exists(model_cache_path):
        continue
    with open(model_cache_path, "rb") as f:
        cache_data = pickle.load(f)
    best_single_name = cache_data["best_model_name"]
    best_model = cache_data["models"][best_single_name]
    
    print(f"  Champion model: {best_single_name}. Computing SHAP...")
    
    # ── SHAP ──────────────────────────────────────────────────────────────────
    try:
        # TreeExplainer works for tree based models
        if best_single_name in ["LightGBM", "XGBoost", "CatBoost", "Random_Forest", "Extra_Trees", "Gradient_Boosting"]:
            explainer = shap.TreeExplainer(best_model)
        else:
            # Fallback KernelExplainer on a small background set
            bg_data = shap.sample(X_test, 10)
            explainer = shap.KernelExplainer(best_model.predict, bg_data)
            
        # Compute on a subset of test observations to speed up execution
        explain_subset = X_test.head(50)
        shap_values = explainer(explain_subset)
        
        # 1. SHAP Summary Bar Plot
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, explain_subset, plot_type="bar", show=False)
        plt.title(f"SHAP Özellik Önem Dereceleri - {sheet}", fontsize=12, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(gorseller_dir, f"11_SHAP_Bar_{sheet}_{currency}.png"), dpi=300)
        plt.close()
        
        # 2. SHAP Beeswarm Plot
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, explain_subset, show=False)
        plt.title(f"SHAP Değerleri Arı Kovanı (Beeswarm) Grafiği - {sheet}", fontsize=12, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(gorseller_dir, f"11_SHAP_Beeswarm_{sheet}_{currency}.png"), dpi=300)
        plt.close()
        print("    SHAP plots saved successfully.")
    except Exception as e:
        print(f"    SHAP computation failed or skipped: {e}")
        
    # ── PDP (Partial Dependence Plot) ─────────────────────────────────────────
    try:
        # Plot PDP for the top 2 features
        # We can find the top 2 features by checking which ones exist in X_test
        features_to_pdp = numeric_features[:2]
        
        fig, ax = plt.subplots(figsize=(12, 5))
        PartialDependenceDisplay.from_estimator(best_model, X_test, features_to_pdp, ax=ax)
        plt.suptitle(f"Kısmi Bağımlılık Grafiği (PDP) - {sheet}", fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(gorseller_dir, f"11_PDP_{sheet}_{currency}.png"), dpi=300)
        plt.close()
        print("    PDP plot saved successfully.")
    except Exception as e:
        print(f"    PDP plotting failed: {e}")

print("Step 11 XAI Execution completed successfully!")
