import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFE

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 4 (İleri Özellik Seçimi - RFE) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "4_RFE_Secimi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "4_RFE_Secimi")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

source_path = os.path.join(islenmis_dir, f"3_BIST_{currency}_VIF_Temiz.xlsx")
dest_path = os.path.join(islenmis_dir, f"4_BIST_{currency}_RFE_Secilmis.xlsx")

if not os.path.exists(source_path):
    print(f"Hata: {source_path} bulunamadı! Lütfen önce Adım 3'ü çalıştırın.")
    sys.exit(1)

print(f"Loading {source_path}...")
xl = pd.ExcelFile(source_path)
sheet_names = xl.sheet_names

cleaned_sheets = {}
N_FEATURES_TO_SELECT = 25 # Top 25 özellikleri seçeceğiz

for sheet in sheet_names:
    print(f"\nProcessing sector: {sheet}")
    df = pd.read_excel(source_path, sheet_name=sheet)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    numeric_features = [col for col in df.columns if col not in meta_cols and df[col].dtype in ["float64", "int64"]]
    
    if len(numeric_features) <= N_FEATURES_TO_SELECT:
        print(f"  Already {len(numeric_features)} features, skipping RFE.")
        cleaned_sheets[sheet] = df.copy()
        continue
        
    X = df[numeric_features].fillna(0.0)
    y = df[target_col].fillna(0.0)
    
    # Train setini al (Dönem <= 31) RFE'nin veri sızdırmaması için sadece eğitim verisiyle yapılır!
    train_mask = df["Dönem"] <= 31
    X_train = X[train_mask]
    y_train = y[train_mask]
    
    if len(X_train) < 20:
        print(f"  Not enough train samples ({len(X_train)}), skipping RFE.")
        cleaned_sheets[sheet] = df.copy()
        continue
    
    print(f"  Running RFE to select {N_FEATURES_TO_SELECT} out of {len(numeric_features)} features...")
    estimator = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    selector = RFE(estimator, n_features_to_select=N_FEATURES_TO_SELECT, step=5)
    selector = selector.fit(X_train, y_train)
    
    selected_features = X.columns[selector.support_].tolist()
    
    # Kalan özellikleri kaydet
    final_cols = meta_cols + selected_features
    df_cleaned = df[final_cols].copy()
    cleaned_sheets[sheet] = df_cleaned
    
    # Seçilen özelliklerin önem grafiğini çiz
    estimator.fit(X_train[selected_features], y_train)
    importances = estimator.feature_importances_
    
    imp_df = pd.DataFrame({"Feature": selected_features, "Importance": importances})
    imp_df = imp_df.sort_values(by="Importance", ascending=False)
    
    plt.figure(figsize=(10, 8))
    ax = sns.barplot(data=imp_df, x="Importance", y="Feature", palette="viridis")
    
    # Annotate values
    for p in ax.patches:
        w = p.get_width()
        if w > 0.001:
            ax.annotate(f"{w:.3f}", (w, p.get_y() + p.get_height() / 2.),
                        ha='left', va='center', fontsize=8, fontweight='bold', xytext=(5, 0), textcoords='offset points')
                        
    plt.title(f"{sheet} - RFE İle Seçilen En İyi 25 Özellik")
    plt.tight_layout()
    plt.savefig(os.path.join(gorseller_dir, f"RFE_Importance_{sheet}_{currency}.png"), dpi=300)
    plt.close()
    
    print(f"  RFE Complete. Selected {len(selected_features)} features.")

print(f"\nWriting RFE cleaned data to {dest_path}...")
with pd.ExcelWriter(dest_path, engine="xlsxwriter") as writer:
    for sheet, df_cleaned in cleaned_sheets.items():
        df_cleaned.to_excel(writer, sheet_name=sheet, index=False)

print("Step 4 RFE execution completed successfully!")
