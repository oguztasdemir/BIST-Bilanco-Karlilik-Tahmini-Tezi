import sys
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 9 (Meta-Modeling Stacking) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "9_Meta_Modelleme")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "9_Meta_Modelleme")
reg_models_dir = os.path.join(ml_dir, "4_modeller", "6_Regresyon_Analizi")
modeller_dir = os.path.join(ml_dir, "4_modeller", "9_Meta_Modelleme")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)
os.makedirs(modeller_dir, exist_ok=True)

# Clear old outputs
for file in os.listdir(output_dir):
    try: os.remove(os.path.join(output_dir, file))
    except: pass
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

input_path = os.path.join(islenmis_dir, f"5_BIST_{currency}_Scaled.xlsx")
if not os.path.exists(input_path):
    print(f"Hata: {input_path} bulunamadı! Lütfen önce Adım 5'i çalıştırın.")
    sys.exit(1)

xl = pd.ExcelFile(input_path)
sheet_names = xl.sheet_names

stacking_results = []
writer = pd.ExcelWriter(os.path.join(output_dir, f"Stacking_Performans_Raporu_{currency}.xlsx"), engine="xlsxwriter")

# Level-0 models to stack
base_model_names = ["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"]

for sheet in sheet_names:
    print(f"\n==================================================")
    print(f"Stacking Ensemble for Sector: {sheet}")
    print(f"==================================================")
    
    df = pd.read_excel(input_path, sheet_name=sheet)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    train_mask = df["Dönem"] <= 31
    test_mask = df["Dönem"] >= 32
    
    df_train = df[train_mask].copy().reset_index(drop=True)
    df_test = df[test_mask].copy().reset_index(drop=True)
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    X_train = df_train[numeric_features].fillna(0.0)
    y_train = df_train[target_col]
    X_test = df_test[numeric_features].fillna(0.0)
    y_test = df_test[target_col]
    
    # Load Step 6 models
    model_cache_path = os.path.join(reg_models_dir, f"champion_{sheet}_{currency}.pkb")
    if not os.path.exists(model_cache_path):
        print(f"Warning: Cached models not found for {sheet} at {model_cache_path}. Skipping.")
        continue
        
    with open(model_cache_path, "rb") as f:
        cache_data = pickle.load(f)
        
    fitted_models = cache_data["models"]
    best_single_name = cache_data["best_model_name"]
    best_single_model = fitted_models[best_single_name]
    
    # Build Level-0 predictions (Train & Test)
    L0_train = pd.DataFrame()
    L0_test = pd.DataFrame()
    
    for name in base_model_names:
        if name in fitted_models:
            L0_train[name] = fitted_models[name].predict(X_train)
            L0_test[name] = fitted_models[name].predict(X_test)
        else:
            # Fallback if model not found
            L0_train[name] = np.zeros(len(X_train))
            L0_test[name] = np.zeros(len(X_test))
            
    # Train Level-1 Meta Model (Ridge Regressor)
    meta_model = Ridge(alpha=1.0)
    meta_model.fit(L0_train, y_train)
    
    # Save meta model
    meta_model_path = os.path.join(modeller_dir, f"stacking_meta_{sheet}_{currency}.pkl")
    with open(meta_model_path, "wb") as f:
        pickle.dump(meta_model, f)
        
    # Evaluate
    preds_single = best_single_model.predict(X_test)
    preds_stack = meta_model.predict(L0_test)
    
    # Calculate metrics
    def calc_mape(y_true, y_pred):
        mask = y_true != 0
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        
    r2_single = r2_score(y_test, preds_single)
    r2_stack = r2_score(y_test, preds_stack)
    
    rmse_single = np.sqrt(mean_squared_error(y_test, preds_single))
    rmse_stack = np.sqrt(mean_squared_error(y_test, preds_stack))
    
    mae_single = mean_absolute_error(y_test, preds_single)
    mae_stack = mean_absolute_error(y_test, preds_stack)
    
    mape_single = calc_mape(y_test.values, preds_single)
    mape_stack = calc_mape(y_test.values, preds_stack)
    
    # Yön başarısı (Direction Accuracy)
    # Cari kardan yüksek tahmin edip gerçekten yüksek çıkma oranı
    y_test_real_carikar = df_test["Net Dönem Karı/Zararı"].values
    
    dir_real = (y_test.values > y_test_real_carikar).astype(int)
    dir_pred_single = (preds_single > y_test_real_carikar).astype(int)
    dir_pred_stack = (preds_stack > y_test_real_carikar).astype(int)
    
    dir_acc_single = np.mean(dir_real == dir_pred_single) * 100
    dir_acc_stack = np.mean(dir_real == dir_pred_stack) * 100
    
    stacking_results.append({
        "Sektör": sheet,
        "En İyi Tekil Model": best_single_name,
        "R2 (Best Single)": round(r2_single, 4),
        "R2 (Stacking)": round(r2_stack, 4),
        "RMSE (Best Single)": round(rmse_single, 2),
        "RMSE (Stacking)": round(rmse_stack, 2),
        "MAE (Best Single)": round(mae_single, 2),
        "MAE (Stacking)": round(mae_stack, 2),
        "MAPE (Best Single)": round(mape_single, 2),
        "MAPE (Stacking)": round(mape_stack, 2),
        "Yön Doğruluğu (Best Single)": round(dir_acc_single, 2),
        "Yön Doğruluğu (Stacking)": round(dir_acc_stack, 2)
    })
    
    # Save predictions
    df_preds = df_test[["Firma Adı", "Dönem", target_col, "Net Dönem Karı/Zararı"]].copy()
    df_preds["Gerçek"] = y_test
    df_preds[f"Tahmin_{best_single_name}"] = preds_single
    df_preds["Tahmin_Stacking"] = preds_stack
    df_preds.to_excel(writer, sheet_name=sheet[:25], index=False)
    
    # Plot real vs prediction comparison
    plt.figure(figsize=(10, 6))
    plt.plot(y_test.values[:50], label="Gerçek Değer", color="black", linestyle="-", marker="o")
    plt.plot(preds_single[:50], label=f"Best Single ({best_single_name})", color="#e74c3c", linestyle="--", marker="x")
    plt.plot(preds_stack[:50], label="Stacking Ensemble (Level-1)", color="#2ecc71", linestyle="-.", marker="d")
    plt.title(f"Gerçek vs Tahmin Karşılaştırması - {sheet}\n({currency})", fontsize=12, fontweight='bold')
    plt.ylabel("Kar / Zarar")
    plt.xlabel("Test Gözlemleri (İlk 50)")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(gorseller_dir, f"9_Tahmin_Karsilastirma_{sheet}_{currency}.png"), dpi=300)
    plt.close()

# Save general summary
summary_df = pd.DataFrame(stacking_results)
summary_df.to_excel(writer, sheet_name="Genel_Stacking_Ozet", index=False)
writer.close()

# Plot Stacking vs Best Single R2 Comparison Plot
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(summary_df))
width = 0.35

rects1 = ax.bar(x - width/2, summary_df["R2 (Best Single)"], width, label='Best Single Model', color='#e74c3c')
rects2 = ax.bar(x + width/2, summary_df["R2 (Stacking)"], width, label='Stacking Ensemble (Meta)', color='#2ecc71')

# Annotate values
for rect in rects1:
    h = rect.get_height()
    if not np.isnan(h):
        ax.annotate(f"{h:.4f}", (rect.get_x() + rect.get_width()/2., h),
                    ha='center', va='bottom', fontsize=8, fontweight='bold', xytext=(0, 3), textcoords='offset points')
for rect in rects2:
    h = rect.get_height()
    if not np.isnan(h):
        ax.annotate(f"{h:.4f}", (rect.get_x() + rect.get_width()/2., h),
                    ha='center', va='bottom', fontsize=8, fontweight='bold', xytext=(0, 3), textcoords='offset points')

ax.set_ylabel('R2 Skoru', fontweight='bold', fontsize=12)
ax.set_title(f'Sektörel Stacking Ensemble vs En İyi Tekil Model R2 Karşılaştırması ({currency})', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(summary_df["Sektör"], rotation=45, ha="right")
ax.legend()
ax.grid(axis='y', linestyle=':', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, f"9_Stacking_R2_Karsilastirma_{currency}.png"), dpi=300)
plt.close()

print("Step 9 Stacking Ensemble completed successfully!")
