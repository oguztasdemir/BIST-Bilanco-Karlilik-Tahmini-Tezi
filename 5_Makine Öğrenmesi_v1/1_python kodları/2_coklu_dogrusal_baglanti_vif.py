import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.stats.outliers_influence import variance_inflation_factor

# Add root folder to sys.path to import kullanici.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# Define paths dynamically using kb.klasor
ml_dir = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "2_Ozellik_Secimi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "2_Ozellik_Secimi")

# Ensure target directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs for Step 2
print("Clearing old outputs for Step 2...")
for file in os.listdir(output_dir):
    os.remove(os.path.join(output_dir, file))
for file in os.listdir(gorseller_dir):
    os.remove(os.path.join(gorseller_dir, file))

input_path = os.path.join(islenmis_dir, "1_BIST_USD_Temiz.xlsx")
print(f"Loading {input_path}...")
xl = pd.ExcelFile(input_path)
sheet_names = xl.sheet_names

report_data = []
vif_sheets = {}

def prune_features_by_vif(df, features, threshold=10.0):
    cols = list(features)
    dropped = []
    
    while True:
        if len(cols) <= 1:
            break
        # Create design matrix
        X = df[cols].copy()
        # Handle constant features (zero variance)
        for col in X.columns:
            if X[col].nunique() <= 1:
                X[col] = X[col] + np.random.normal(0, 1e-5, size=len(X))
        
        # Add intercept
        X['const'] = 1.0
        
        vifs = []
        for i in range(len(cols)):
            try:
                vif = variance_inflation_factor(X.values, i)
            except Exception:
                vif = 999.0  # singular matrix fallback
            vifs.append(vif)
            
        max_idx = np.argmax(vifs)
        max_vif = vifs[max_idx]
        
        if max_vif > threshold:
            dropped_col = cols[max_idx]
            dropped.append(dropped_col)
            cols.remove(dropped_col)
        else:
            break
            
    # Calculate final VIFs
    final_vifs = {}
    if len(cols) > 0:
        X = df[cols].copy()
        # Add noise if constant just to prevent singular error
        for col in X.columns:
            if X[col].nunique() <= 1:
                X[col] = X[col] + np.random.normal(0, 1e-5, size=len(X))
        X['const'] = 1.0
        for i, col in enumerate(cols):
            try:
                vif = variance_inflation_factor(X.values, i)
            except Exception:
                vif = 999.0
            final_vifs[col] = round(vif, 2)
            
    return cols, dropped, final_vifs

for sheet in sheet_names:
    print(f"\nPerforming VIF analysis for sector: {sheet}")
    df = pd.read_excel(input_path, sheet_name=sheet)
    
    target_col = [col for col in df.columns if "t+1" in col][0]
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", target_col]
    
    # Identify feature columns (exclude meta columns)
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    # We do VIF calculation on numeric features
    kept_features, dropped_features, final_vifs = prune_features_by_vif(df, numeric_features, threshold=10.0)
    
    # Reconstruct dataframe with meta columns + kept features
    keep_cols = meta_cols + kept_features
    # Check if there are non-numeric features to preserve
    non_numeric_features = [col for col in feature_cols if col not in numeric_features]
    keep_cols += non_numeric_features
    
    df_vif = df[keep_cols].copy()
    vif_sheets[sheet] = df_vif
    
    # Log report statistics
    report_data.append({
        "Sektör": sheet,
        "Başlangıç Özellik Sayısı": len(numeric_features),
        "Seçilen Özellik Sayısı": len(kept_features),
        "Elenen Özellik Sayısı": len(dropped_features),
        "Elenen Özellikler": ", ".join(dropped_features),
        "Seçilen Özellikler & VIF Değerleri": str(final_vifs)
    })
    print(f"Sector {sheet} complete: Kept {len(kept_features)} features, Dropped {len(dropped_features)} features.")

# Save VIF dataset to 2_BIST_USD_VIF.xlsx
vif_dataset_path = os.path.join(islenmis_dir, "2_BIST_USD_VIF.xlsx")
print(f"\nSaving VIF pruned dataset to {vif_dataset_path}...")
with pd.ExcelWriter(vif_dataset_path, engine="xlsxwriter") as writer:
    for sheet, df_vif in vif_sheets.items():
        df_vif.to_excel(writer, sheet_name=sheet, index=False)

# Save Report Excel
report_df = pd.DataFrame(report_data)
report_path = os.path.join(output_dir, "2_VIF_Raporu.xlsx")
report_df.to_excel(report_path, index=False)
print(f"VIF report saved to {report_path}")

# Plot VIF feature reduction comparison
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(report_df["Sektör"]))
width = 0.35

rects1 = ax.bar(x - width/2, report_df["Başlangıç Özellik Sayısı"], width, label='Başlangıç Özellik Sayısı', color='#34495e')
rects2 = ax.bar(x + width/2, report_df["Seçilen Özellik Sayısı"], width, label='Seçilen Özellik Sayısı (VIF <= 10)', color='#2ecc71')

# Add data labels
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{int(height)}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

autolabel(rects1)
autolabel(rects2)

plt.xlabel('Sektör')
plt.ylabel('Özellik Sayısı')
plt.title('VIF Analizi ile Çoklu Doğrusal Bağlantı Temizliği Özeti')
plt.xticks(x, report_df["Sektör"], rotation=45, ha="right")
plt.legend()
plt.tight_layout()

gorsel_path = os.path.join(gorseller_dir, "VIF_Temizleme_Ozeti.png")
plt.savefig(gorsel_path, dpi=300)
plt.close()
print(f"Plot saved to {gorsel_path}")
print("Step 2 VIF execution completed successfully!")
