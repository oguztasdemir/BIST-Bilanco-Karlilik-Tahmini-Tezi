import sys
import os
import pandas as pd
import numpy as np
import optuna
import matplotlib.pyplot as plt
import xgboost as xgb
from sklearn.model_selection import KFold

optuna.logging.set_verbosity(optuna.logging.WARNING)

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 8 (Bayesian Hyperparameter Plots) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "8_Hiperparametre_Optimizasyonu")

os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

input_path = os.path.join(islenmis_dir, f"5_BIST_{currency}_Scaled.xlsx")
if not os.path.exists(input_path):
    print(f"Hata: {input_path} bulunamadı! Lütfen önce Adım 5'i çalıştırın.")
    sys.exit(1)

# İlk sektörü örnek olarak alıp hızlı bir Optuna çalışması yapacağız
print(f"Loading first sector from {input_path}...")
xl = pd.ExcelFile(input_path)
first_sheet = xl.sheet_names[0]
df = pd.read_excel(input_path, sheet_name=first_sheet)

target_cols = [col for col in df.columns if "t+1" in col]
if not target_cols:
    print("Hata: Hedef kolon bulunamadı!")
    sys.exit(1)
target_col = target_cols[0]

meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
feature_cols = [col for col in df.columns if col not in meta_cols]
numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]

X = df[numeric_features].fillna(0.0)
y = df[target_col]

# Hızlı bir XGBoost Regressor hyperparameter tuning çalışması yapalım
def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 20, 100),
        'max_depth': trial.suggest_int('max_depth', 3, 7),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0)
    }
    kf = KFold(n_splits=3, shuffle=True, random_state=42)
    scores = []
    for train_idx, val_idx in kf.split(X):
        X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
        X_va, y_va = X.iloc[val_idx], y.iloc[val_idx]
        model = xgb.XGBRegressor(**params, random_state=42)
        model.fit(X_tr, y_tr)
        preds = model.predict(X_va)
        scores.append(np.mean((y_va - preds) ** 2))
    return np.mean(scores)

print(f"Running quick 15-trial Optuna study on sector {first_sheet} to generate hyperparameter plots...")
study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=15)

# Görselleri çizelim (Optuna visualization matplotlib modülü ile)
import optuna.visualization.matplotlib as ovis

print("Generating Optuna Plots...")

# 1. Optimization History Plot
plt.figure(figsize=(10, 6))
ovis.plot_optimization_history(study)
plt.title(f"Bayesian Optimization History ({first_sheet} - XGBoost)", fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, f"8_Opt_History_{currency}.png"), dpi=300)
plt.close()

# 2. Slice Plot
plt.figure(figsize=(12, 8))
ovis.plot_slice(study, params=['learning_rate', 'max_depth'])
plt.suptitle(f"Hyperparameter Slice Plot ({first_sheet})", fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, f"8_Opt_Slice_{currency}.png"), dpi=300)
plt.close()

# 3. Parameter Importance Plot
plt.figure(figsize=(10, 6))
ovis.plot_param_importances(study)
plt.title(f"Hyperparameter Importance ({first_sheet})", fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, f"8_Opt_Param_Importance_{currency}.png"), dpi=300)
plt.close()

# 4. Contour Plot (learning_rate vs max_depth)
plt.figure(figsize=(10, 8))
ovis.plot_contour(study, params=['learning_rate', 'max_depth'])
plt.suptitle(f"Hyperparameter Contour Plot ({first_sheet})", fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, f"8_Opt_Contour_{currency}.png"), dpi=300)
plt.close()

print("Step 8 Hyperparameter plots saved successfully!")
