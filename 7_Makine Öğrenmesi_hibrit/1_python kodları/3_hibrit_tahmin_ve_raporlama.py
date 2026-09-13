import os
import sys
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 3 (Hibrit Tahmin ve Raporlama) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
v1_dataset_path = os.path.join(ml_dir, "3_çıktılar", "00_dataset", "v1_dataset", f"2_BIST_{currency}_VIF.xlsx")
v2_dataset_path = os.path.join(ml_dir, "3_çıktılar", "00_dataset", "v2_dataset", f"5_BIST_{currency}_Scaled.xlsx")
decision_matrix_path = os.path.join(ml_dir, "3_çıktılar", "2_Hibrit_Karar_Matrisi", f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")

models_dir = os.path.join(ml_dir, "4_modeller", "2_Hibrit_Modeller")
output_dir = os.path.join(ml_dir, "3_çıktılar", "3_Hibrit_Tahmin_Raporlari")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "3_Hibrit_Tahmin_Raporlari")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# ── 1. HİBRİT KARAR MATRİSİNİ YÜKLEME ─────────────────────────────────────────
if not os.path.exists(decision_matrix_path):
    print(f"Hata: Karar matrisi dosyası bulunamadı: {decision_matrix_path}")
    sys.exit(1)

df_decision = pd.read_excel(decision_matrix_path, sheet_name="En_Iyi_Yapboz_Matrisi")
# Drop the ORTALAMA row if present
df_decision = df_decision[df_decision["Sektör"] != "ORTALAMA"].reset_index(drop=True)

sectors = df_decision["Sektör"].tolist()
print(f"Sektörler: {sectors}")

hybrid_results = []

# Helper to load dataset and extract features/target based on version
def get_dataset_splits(path, sect, version):
    df_data = pd.read_excel(path, sheet_name=sect)
    target_col = [col for col in df_data.columns if "t+1" in col][0]
    
    if version == "V2":
        meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    else:
        meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", target_col]
        
    feature_cols = [col for col in df_data.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df_data[col].dtype in ["float64", "int64"]]
    
    test_mask = df_data["Dönem"] >= 32
    df_test = df_data[test_mask].copy().reset_index(drop=True)
    
    X_test = df_test[feature_cols].copy()
    y_test = df_test[target_col].copy()
    
    return df_test, X_test, y_test, numeric_features

# ── 2. MODELLERİ YÜKLEME VE TAHMİN ETME ───────────────────────────────────────
for sect in sectors:
    print(f"\nEvaluating sector: {sect}")
    row = df_decision[df_decision["Sektör"] == sect].iloc[0]
    
    reg_ver = row["Reg_Sayısal_Versiyon"]
    cls_yon_ver = row["Cls_Yön_Versiyon"]
    cls_kz_ver = row["Cls_KZ_Versiyon"]
    
    # ── A. REGRESYON MODELİ YÜKLEME VE TAHMİN ───────────────────────────────
    reg_path = v1_dataset_path if reg_ver == "V1" else v2_dataset_path
    df_test_reg, X_test_reg, y_test_reg, numeric_reg = get_dataset_splits(reg_path, sect, reg_ver)
    
    reg_model_path = os.path.join(models_dir, "3_Regresyon_Analizi", f"champion_{sect}_{currency}.pkb")
    with open(reg_model_path, "rb") as f:
        reg_cache = pickle.load(f)
        
    fitted_models = reg_cache["models"]
    
    if reg_ver == "V1":
        best_single_name = reg_cache["best_model_name"]
        scaler = reg_cache.get("scaler", None)
        if scaler is not None and len(numeric_reg) > 0:
            X_test_reg[numeric_reg] = scaler.transform(X_test_reg[numeric_reg])
        
        preds_reg = fitted_models[best_single_name].predict(X_test_reg)
        champ_algorithm = best_single_name
    else:
        # V2 Stacking
        meta_model_path = os.path.join(models_dir, "9_Meta_Modelleme", f"stacking_meta_{sect}_{currency}.pkl")
        with open(meta_model_path, "rb") as f:
            meta_model = pickle.load(f)
            
        L0_test = pd.DataFrame()
        # The Ridge Stacking model was trained on these columns exactly
        base_model_names = ["CatBoost", "LightGBM", "XGBoost", "Random_Forest", "Extra_Trees"]
        for name in base_model_names:
            if name == "Random_Forest" and "RF" in fitted_models:
                # "RF" was stored, but fit expected "Random_Forest" filled with 0s because of name mismatch.
                # To replicate the V2 stacking meta-predictions perfectly:
                L0_test["Random_Forest"] = np.zeros(len(X_test_reg))
            elif name in fitted_models:
                L0_test[name] = fitted_models[name].predict(X_test_reg)
            else:
                L0_test[name] = np.zeros(len(X_test_reg))
            
        preds_reg = meta_model.predict(L0_test)
        champ_algorithm = "Stacking Ensemble"
        
    # Calculate Regression Metrics
    real_yon = (y_test_reg > df_test_reg["Net Dönem Karı/Zararı"]).astype(int)
    pred_yon = (preds_reg > df_test_reg["Net Dönem Karı/Zararı"]).astype(int)
    reg_yon_acc = np.mean(real_yon == pred_yon) * 100
    
    real_kz = (y_test_reg > 0).astype(int)
    pred_kz = (preds_reg > 0).astype(int)
    reg_kz_acc = np.mean(real_kz == pred_kz) * 100
    
    non_zero = y_test_reg != 0
    mape = np.mean(np.abs((y_test_reg[non_zero] - preds_reg[non_zero]) / y_test_reg[non_zero])) * 100
    wmape = (np.sum(np.abs(y_test_reg - preds_reg)) / np.sum(np.abs(y_test_reg))) * 100
    
    computed_score = (reg_yon_acc / 100 * 0.4) + (reg_kz_acc / 100 * 0.4) + (max(0.0, 1.0 - (mape / 100)) * 0.2)
    
    print(f"  Regresyon: Yöntem={champ_algorithm}, Hesaplanan Skor={computed_score * 100:.2f}% (Matris Skor={row['Reg_Sayısal_Skor (%)']:.2f}%)")
    
    # ── B. CLASSIFICATION YÖN MODELİ YÜKLEME VE TAHMİN ───────────────────────
    cls_yon_path = v1_dataset_path if cls_yon_ver == "V1" else v2_dataset_path
    df_test_yon, X_test_yon, y_test_yon, numeric_yon = get_dataset_splits(cls_yon_path, sect, cls_yon_ver)
    y_test_yon_binary = (y_test_yon > df_test_yon["Net Dönem Karı/Zararı"]).astype(int)
    
    model_yon_path = os.path.join(models_dir, "4_Siniflandirma_Analizi", f"champion_{sect}_Yon_Tahmini_{currency}.pkb")
    with open(model_yon_path, "rb") as f:
        cls_yon_cache = pickle.load(f)
        
    if cls_yon_ver == "V1":
        model_yon = cls_yon_cache["model"]
        scaler_yon = cls_yon_cache.get("scaler", None)
        threshold_yon = cls_yon_cache.get("threshold", 0.5)
        
        if scaler_yon is not None and len(numeric_yon) > 0:
            X_test_yon[numeric_yon] = scaler_yon.transform(X_test_yon[numeric_yon])
            
        probs_yon = model_yon.predict_proba(X_test_yon[numeric_yon])[:, 1]
        preds_yon = (probs_yon >= threshold_yon).astype(int)
    else:
        # V2 Classifier
        models_yon = cls_yon_cache["models"]
        best_name_yon = cls_yon_cache["best_model_name"]
        preds_yon = models_yon[best_name_yon].predict(X_test_yon[numeric_yon])
        
    computed_cls_yon_acc = np.mean(y_test_yon_binary == preds_yon) * 100
    print(f"  Cls Yön: Hesaplanan={computed_cls_yon_acc:.2f}% (Matris={row['Cls_Yön_Skor (%)']:.2f}%)")
    
    # ── C. CLASSIFICATION KAR-ZARAR MODELİ YÜKLEME VE TAHMİN ─────────────────
    cls_kz_path = v1_dataset_path if cls_kz_ver == "V1" else v2_dataset_path
    df_test_kz, X_test_kz, y_test_kz, numeric_kz = get_dataset_splits(cls_kz_path, sect, cls_kz_ver)
    y_test_kz_binary = (y_test_kz > 0).astype(int)
    
    model_kz_path = os.path.join(models_dir, "4_Siniflandirma_Analizi", f"champion_{sect}_Kar_Zarar_Tahmini_{currency}.pkb")
    with open(model_kz_path, "rb") as f:
        cls_kz_cache = pickle.load(f)
        
    if cls_kz_ver == "V1":
        model_kz = cls_kz_cache["model"]
        scaler_kz = cls_kz_cache.get("scaler", None)
        threshold_kz = cls_kz_cache.get("threshold", 0.5)
        
        if scaler_kz is not None and len(numeric_kz) > 0:
            X_test_kz[numeric_kz] = scaler_kz.transform(X_test_kz[numeric_kz])
            
        probs_kz = model_kz.predict_proba(X_test_kz[numeric_kz])[:, 1]
        preds_kz = (probs_kz >= threshold_kz).astype(int)
    else:
        # V2 Classifier
        models_kz = cls_kz_cache["models"]
        best_name_kz = cls_kz_cache["best_model_name"]
        preds_kz = models_kz[best_name_kz].predict(X_test_kz[numeric_kz])
        
    computed_cls_kz_acc = np.mean(y_test_kz_binary == preds_kz) * 100
    print(f"  Cls K/Z: Hesaplanan={computed_cls_kz_acc:.2f}% (Matris={row['Cls_KZ_Skor (%)']:.2f}%)")
    
    hybrid_results.append({
        "Sektör": sect,
        "En_Basarili_Regresyon_Yontemi": champ_algorithm,
        "Reg_Sayisal_Basari": computed_score * 100,
        "Reg_Yon_Basarisi": reg_yon_acc,
        "Reg_KZ_Basarisi": reg_kz_acc,
        "Cls_Yon_Basarisi": computed_cls_yon_acc,
        "Cls_KZ_Basarisi": computed_cls_kz_acc,
        "MAPE": mape,
        "WMAPE": wmape
    })

df_hybrid = pd.DataFrame(hybrid_results)

# Calculate ORTALAMA row for Excel output
numeric_cols = ["Reg_Sayisal_Basari", "Reg_Yon_Basarisi", "Reg_KZ_Basarisi", "Cls_Yon_Basarisi", "Cls_KZ_Basarisi", "MAPE", "WMAPE"]
avg_row = {"Sektör": "ORTALAMA", "En_Basarili_Regresyon_Yontemi": "-"}
for col in numeric_cols:
    avg_row[col] = df_hybrid[col].mean()

df_hybrid_excel = pd.concat([df_hybrid, pd.DataFrame([avg_row])], ignore_index=True)

# Save Master Synthesis Excel sheet for Step 3
excel_path = os.path.join(output_dir, f"3_BIST_{currency}_Hibrit_Nihai_Sentez.xlsx")
df_hybrid_excel.to_excel(excel_path, sheet_name="Hibrit_Tahmin_Sentezi", index=False)
print(f"\nHibrit Nihai Sentez Exceli Kaydedildi: {excel_path}")


# ── 3. NİHAİ GÖRSELLERİ OLUŞTURMA (6. Klasördeki Gibi) ──────────────────────────

# 3.1 Şampiyon Modeller Donut Grafiği
plt.figure(figsize=(8, 8))
champ_counts = df_hybrid["En_Basarili_Regresyon_Yontemi"].value_counts()
colors = ['#3498db', '#2ecc71', '#e74c3c', '#f1c40f', '#9b59b6', '#34495e']
plt.pie(champ_counts, labels=champ_counts.index, autopct='%1.1f%%', startangle=90, colors=colors[:len(champ_counts)],
        wedgeprops=dict(width=0.4, edgecolor='white'), textprops={'fontweight':'bold', 'fontsize':11})
plt.title(f"Hibrit Sektörel Regresyon Şampiyon Modellerinin Dağılımı ({currency})", fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
donut_path = os.path.join(gorseller_dir, f"13_Hibrit_Champion_Models_Donut_{currency}.png")
plt.savefig(donut_path, dpi=300)
plt.close()
print(f"Donut Grafiği Kaydedildi: {donut_path}")

# 3.2 Sektörel Tahmin Başarısı Isı Haritası (Heatmap)
heatmap_df = df_hybrid_excel.set_index("Sektör")[
    ["Reg_Sayisal_Basari", "Reg_Yon_Basarisi", "Reg_KZ_Basarisi", "Cls_Yon_Basarisi", "Cls_KZ_Basarisi"]
].copy().astype(float)

heatmap_df.columns = [
    "Regresyon\nSayısal Başarı", 
    "Regresyon\nYön Başarısı", 
    "Regresyon\nKar-Zarar Başarısı", 
    "Sınıflandırma\nYön Başarısı", 
    "Sınıflandırma\nKar-Zarar Başarısı"
]

import matplotlib.colors as mcolors
df_sectors = heatmap_df.iloc[:-1]
df_ortalama = heatmap_df.iloc[-1:]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), gridspec_kw={'height_ratios': [7, 1.2]})
fig.subplots_adjust(right=0.88, hspace=0.08)
cbar_ax = fig.add_axes([0.91, 0.22, 0.015, 0.65])

# Plot main sectors
sns.heatmap(df_sectors, annot=True, fmt=".1f", cmap="YlGnBu", ax=ax1, cbar_ax=cbar_ax, cbar_kws={'label': 'Başarı Oranı (%)'}, linewidths=1, annot_kws={"size": 10, "weight": "bold"})
ax1.set_title(f"Sektörel Tahmin Başarısı Hibrit Isı Haritası ({currency})", fontsize=14, fontweight='bold', pad=20)
ax1.set_ylabel("Sektör", fontsize=12, fontweight='bold')
ax1.set_xticklabels([])

# Plot ORTALAMA as neutral clean light grey/white background
neutral_cmap = mcolors.ListedColormap(['#f8f9fa'])
sns.heatmap(df_ortalama, annot=True, fmt=".1f", cmap=neutral_cmap, ax=ax2, cbar=False, linewidths=1, annot_kws={"size": 10, "weight": "bold", "color": "black"})
ax2.set_ylabel("")
ax2.set_yticklabels(["ORTALAMA"], rotation=0, fontsize=10, fontweight='bold')
ax2.set_xticklabels(df_sectors.columns, rotation=30, ha='right', fontsize=10, fontweight='bold')

heatmap_path = os.path.join(gorseller_dir, f"13_Hibrit_Sektorel_R2_Heatmap_{currency}.png")
plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"Heatmap Grafiği Kaydedildi: {heatmap_path}")

# 3.3 Sektörel Regresyon Tahmin Zorluğu (Ortalama MAPE)
df_hybrid_plot = pd.concat([
    df_hybrid,
    pd.DataFrame([{
        "Sektör": "ORTALAMA",
        "MAPE": df_hybrid["MAPE"].mean(),
        "WMAPE": df_hybrid["WMAPE"].mean()
    }])
], ignore_index=True)

plt.figure(figsize=(12, 6))
ax_mape = sns.barplot(data=df_hybrid_plot, x="Sektör", y="MAPE", hue="Sektör", palette="Reds_r", legend=False)

for p in ax_mape.patches:
    h = p.get_height()
    if not np.isnan(h):
        ax_mape.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h),
                         ha='center', va='bottom', fontsize=10, fontweight='bold',
                         xytext=(0, 2), textcoords='offset points')
                         
plt.xlabel("Sektör Adı", fontweight='bold', fontsize=12)
plt.ylabel("Hata Oranı (MAPE %)", fontweight='bold', fontsize=12)
plt.title(f"Sektörel Regresyon Tahmin Zorluğu (Hibrit Sistem MAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
plt.xticks(rotation=45, ha="right")

for spine in ax_mape.spines.values():
    spine.set_visible(True)
    spine.set_color('black')
    spine.set_linewidth(1.0)
    
plt.tight_layout()
mape_plot_path = os.path.join(gorseller_dir, f"13_Hibrit_MAPE_Comparison_{currency}.png")
plt.savefig(mape_plot_path, dpi=300)
plt.close()
print(f"MAPE Grafiği Kaydedildi: {mape_plot_path}")

# 3.4 Sektörel Regresyon Tahmin Zorluğu (Ortalama WMAPE)
plt.figure(figsize=(12, 6))
ax_wmape = sns.barplot(data=df_hybrid_plot, x="Sektör", y="WMAPE", hue="Sektör", palette="Reds_r", legend=False)

for p in ax_wmape.patches:
    h = p.get_height()
    if not np.isnan(h):
        ax_wmape.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h),
                         ha='center', va='bottom', fontsize=10, fontweight='bold',
                         xytext=(0, 2), textcoords='offset points')
                         
plt.xlabel("Sektör Adı", fontweight='bold', fontsize=12)
plt.ylabel("Hata Oranı (WMAPE %)", fontweight='bold', fontsize=12)
plt.title(f"Sektörel Regresyon Tahmin Zorluğu (Hibrit Sistem WMAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
plt.xticks(rotation=45, ha="right")

for spine in ax_wmape.spines.values():
    spine.set_visible(True)
    spine.set_color('black')
    spine.set_linewidth(1.0)
    
plt.tight_layout()
wmape_plot_path = os.path.join(gorseller_dir, f"13_Hibrit_WMAPE_Comparison_{currency}.png")
plt.savefig(wmape_plot_path, dpi=300)
plt.close()
print(f"WMAPE Grafiği Kaydedildi: {wmape_plot_path}")

print("Step 3 completed successfully!")
