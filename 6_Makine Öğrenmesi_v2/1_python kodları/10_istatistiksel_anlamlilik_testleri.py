import sys
import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 10 (Statistical Significance Tests) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "10_Istatistiksel_Testler")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "10_Istatistiksel_Testler")
reg_models_dir = os.path.join(ml_dir, "4_modeller", "6_Regresyon_Analizi")
stack_models_dir = os.path.join(ml_dir, "4_modeller", "9_Meta_Modelleme")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

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

significance_results = []

for sheet in sheet_names:
    print(f"\nProcessing sector: {sheet}")
    df = pd.read_excel(input_path, sheet_name=sheet)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    train_mask = df["Dönem"] <= 31
    test_mask = df["Dönem"] >= 32
    
    df_test = df[test_mask].copy().reset_index(drop=True)
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    X_test = df_test[numeric_features].fillna(0.0)
    y_test = df_test[target_col]
    
    # Load single model
    model_cache_path = os.path.join(reg_models_dir, f"champion_{sheet}_{currency}.pkb")
    if not os.path.exists(model_cache_path):
        continue
    with open(model_cache_path, "rb") as f:
        cache_data = pickle.load(f)
    best_single_name = cache_data["best_model_name"]
    best_single_model = cache_data["models"][best_single_name]
    
    # Load stacking meta model
    meta_model_path = os.path.join(stack_models_dir, f"stacking_meta_{sheet}_{currency}.pkl")
    if not os.path.exists(meta_model_path):
        continue
    with open(meta_model_path, "rb") as f:
        meta_model = pickle.load(f)
        
    # Predict L0
    L0_test = pd.DataFrame()
    for name in ["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"]:
        if name in cache_data["models"]:
            L0_test[name] = cache_data["models"][name].predict(X_test)
        else:
            L0_test[name] = np.zeros(len(X_test))
            
    preds_single = best_single_model.predict(X_test)
    preds_stack = meta_model.predict(L0_test)
    
    # Absolute errors
    ae_single = np.abs(y_test - preds_single)
    ae_stack = np.abs(y_test - preds_stack)
    
    # Paired T-Test
    t_stat, p_val_t = stats.ttest_rel(ae_single, ae_stack)
    
    # Wilcoxon Signed-Rank Test (better for non-normal errors)
    try:
        wilc_stat, p_val_w = stats.wilcoxon(ae_single, ae_stack)
    except Exception as e:
        wilc_stat, p_val_w = 0, 1.0
        
    mean_ae_single = np.mean(ae_single)
    mean_ae_stack = np.mean(ae_stack)
    improvement = ((mean_ae_single - mean_ae_stack) / mean_ae_single) * 100
    
    significant = "EVET (p < 0.05)" if p_val_w < 0.05 else "HAYIR (p >= 0.05)"
    
    significance_results.append({
        "Sektör": sheet,
        "En İyi Tekil Model": best_single_name,
        "Tekil Model MAE": round(mean_ae_single, 2),
        "Stacking MAE": round(mean_ae_stack, 2),
        "Hata İyileşmesi (%)": round(improvement, 2),
        "T-İstatistiği": round(t_stat, 4),
        "T-Test p-değeri": round(p_val_t, 6) if not np.isnan(p_val_t) else 1.0,
        "Wilcoxon p-değeri": round(p_val_w, 6),
        "Anlamlı Fark Var mı?": significant
    })
    
    # Plot absolute error distributions
    plt.figure(figsize=(10, 6))
    sns.kdeplot(ae_single, label=f"Best Single ({best_single_name}) AE", fill=True, color="#e74c3c", alpha=0.4)
    sns.kdeplot(ae_stack, label="Stacking Ensemble (Ridge) AE", fill=True, color="#2ecc71", alpha=0.4)
    plt.title(f"Mutlak Hata Dağılımı Karşılaştırması - {sheet}\nWilcoxon p-val: {p_val_w:.6f}", fontsize=12, fontweight='bold')
    plt.xlabel("Mutlak Hata (Absolute Error)")
    plt.ylabel("Yoğunluk (Density)")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(gorseller_dir, f"10_Hata_Dagilimi_{sheet}_{currency}.png"), dpi=300)
    plt.close()

# Save Report
report_df = pd.DataFrame(significance_results)
report_path = os.path.join(output_dir, f"Istatistiksel_Anlamlilik_Testleri_{currency}.xlsx")
report_df.to_excel(report_path, index=False)
print(f"Rapor başarıyla kaydedildi: {report_path}")

# Plot P-Values Comparison Chart
plt.figure(figsize=(12, 6))
colors = ['#2ecc71' if p < 0.05 else '#e74c3c' for p in report_df["Wilcoxon p-değeri"]]
ax = sns.barplot(data=report_df, x="Sektör", y="Wilcoxon p-değeri", palette="Set1")
plt.axhline(y=0.05, color='red', linestyle='--', label='Kritik Eşik (α = 0.05)')
plt.ylabel('Wilcoxon Test p-Değeri', fontweight='bold', fontsize=12)
plt.title(f'Sektörlere Göre Stacking İyileşmesinin İstatistiki Anlamlılığı (Wilcoxon Test - {currency})', fontsize=14, fontweight='bold')
plt.xticks(rotation=45, ha="right")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(gorseller_dir, f"10_Istatistiksel_Anlamlilik_pvalues_{currency}.png"), dpi=300)
plt.close()

print("Step 10 Statistical Significance Tests completed successfully!")
