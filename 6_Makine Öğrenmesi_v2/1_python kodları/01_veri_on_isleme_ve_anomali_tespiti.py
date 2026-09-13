import sys
import os
import shutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import IsolationForest
from sklearn.covariance import EllipticEnvelope
from sklearn.decomposition import PCA

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 1 (Veri Ön İşleme) for currency: {currency}")

# Add root folder to sys.path to import kullanici.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
ham_dir = os.path.join(ml_dir, "00_dataset", "ham_dataset")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "1_Veri_On_Isleme")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "1_Veri_On_Isleme")

# Ensure target directories exist
os.makedirs(ham_dir, exist_ok=True)
os.makedirs(islenmis_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Kaynak veri seti yolu (Faz 4'ten gelir)
source_path = os.path.join(kb.klasor, "4_ Veri Son Hazırlık", "çıktılar", "9_Adim_Sektorel_Akran_Kiyaslama", f"9_Final_Sektorel_Akran_Kiyaslama_{currency}.xlsx")
dest_path = os.path.join(ham_dir, f"BIST_{currency}.xlsx")

print(f"Copying base dataset to ham_dataset/BIST_{currency}.xlsx...")
try:
    shutil.copy(source_path, dest_path)
except Exception as e:
    print(f"Uyarı: {source_path} bulunamadı! Lütfen kaynağı kontrol edin.")
    sys.exit(1)

# Clear old outputs for Step 1
print("Clearing old outputs for Step 1...")
for file in os.listdir(output_dir):
    try: os.remove(os.path.join(output_dir, file))
    except: pass
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

# Load Excel File
print(f"Loading BIST_{currency}.xlsx...")
xl = pd.ExcelFile(dest_path)
sheet_names = xl.sheet_names

report_data = []
cleaned_sheets = {}

for sheet in sheet_names:
    print(f"\nProcessing sector: {sheet}")
    df = pd.read_excel(dest_path, sheet_name=sheet)
    original_len = len(df)
    
    # Drop rows where target variable is NaN
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        print(f"Warning: No target column found for {sheet}. Skipping.")
        continue
    target_col = target_cols[0]
    
    df = df.dropna(subset=[target_col]).copy()
    len_after_target_dropna = len(df)
    
    # Meta columns that are not features to be scaled/imputed
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    feature_cols = [col for col in df.columns if col not in meta_cols]
    numeric_features = [col for col in feature_cols if df[col].dtype in ["float64", "int64"]]
    
    # Impute missing values based on sector-level median fit on Train (Dönem <= 31)
    train_mask = df["Dönem"] <= 31
    for col in numeric_features:
        train_median = df.loc[train_mask, col].median()
        if pd.isna(train_median):
            train_median = df[col].median()
            if pd.isna(train_median):
                train_median = 0.0
        df[col] = df[col].fillna(train_median)
        
    # Anomaly Detection on Train Set (Dönem <= 31)
    df_train = df[train_mask].copy()
    if len(df_train) > 0:
        scaler = RobustScaler()
        # Scale numeric features
        scaled_train = scaler.fit_transform(df_train[numeric_features].fillna(0.0))
        
        # Isolation Forest
        if_model = IsolationForest(contamination=0.05, random_state=42)
        if_preds = if_model.fit_predict(scaled_train)
        
        # Elliptic Envelope (using PCA to avoid singular covariance matrix errors)
        ee_preds = np.ones(len(df_train))
        try:
            non_const_cols = [col for col in numeric_features if df_train[col].nunique() > 1]
            if len(non_const_cols) > 0:
                scaled_train_ee = RobustScaler().fit_transform(df_train[non_const_cols].fillna(0.0))
                pca = PCA(n_components=min(5, scaled_train_ee.shape[1], scaled_train_ee.shape[0] - 1))
                pca_train = pca.fit_transform(scaled_train_ee)
                ee_model = EllipticEnvelope(contamination=0.05, random_state=42)
                ee_preds = ee_model.fit_predict(pca_train)
        except Exception as e:
            print(f"Warning: EllipticEnvelope failed for {sheet}. Falling back to IF.")
            
        # Identify intersection anomalies (both models say -1)
        anomalies = (if_preds == -1) & (ee_preds == -1)
        anomaly_indices = df_train[anomalies].index
        
        num_anomalies = len(anomaly_indices)
        pct_anomaly = (num_anomalies / len(df_train)) * 100
        
        # Drop anomalies
        df_cleaned = df.drop(anomaly_indices).copy()
    else:
        num_anomalies = 0
        pct_anomaly = 0.0
        df_cleaned = df.copy()
        
    cleaned_sheets[sheet] = df_cleaned
    
    # Save stats
    report_data.append({
        "Sektör": sheet,
        "Toplam Gözlem": original_len,
        "Hedef NaN Çıkarılan": original_len - len_after_target_dropna,
        "Train Gözlem": len(df_train),
        "Tespit Edilen Anomali": num_anomalies,
        "Anomali Oranı (%)": round(pct_anomaly, 2),
        "Temizlenmiş Gözlem": len(df_cleaned)
    })
    print(f"Sector {sheet} complete. Anomalies removed: {num_anomalies} ({pct_anomaly:.2f}%)")

# Write cleaned dataset to 1_BIST_{currency}_Temiz.xlsx
cleaned_path = os.path.join(islenmis_dir, f"1_BIST_{currency}_Temiz.xlsx")
print(f"\nWriting cleaned data to {cleaned_path}...")
with pd.ExcelWriter(cleaned_path, engine="xlsxwriter") as writer:
    for sheet, df_cleaned in cleaned_sheets.items():
        df_cleaned.to_excel(writer, sheet_name=sheet, index=False)

# Save Report Excel
report_df = pd.DataFrame(report_data)
report_path = os.path.join(output_dir, f"1_Anomali_Temizleme_Raporu_{currency}.xlsx")
report_df.to_excel(report_path, index=False)
print(f"Report saved to {report_path}")

# Plot Anomaly Rates
plt.figure(figsize=(12, 6))
ax = sns.barplot(data=report_df, x="Sektör", y="Anomali Oranı (%)", palette="viridis")
for p in ax.patches:
    ax.annotate(f"{p.get_height():.2f}%", 
                (p.get_x() + p.get_width() / 2., p.get_height()), 
                ha='center', va='center', 
                xytext=(0, 9), 
                textcoords='offset points',
                fontsize=10, fontweight='bold')
plt.title(f"Sektörel Bazda Anomali Oranları (Eğitim Seti - {currency})")
plt.xticks(rotation=45, ha="right")
plt.ylabel("Anomali Oranı (%)")
plt.tight_layout()
gorsel_path = os.path.join(gorseller_dir, f"1_Sektorel_Anomali_Oranlari_{currency}.png")
plt.savefig(gorsel_path, dpi=300)
plt.close()
print(f"Plot saved to {gorsel_path}")
print("Step 1 execution completed successfully!")
