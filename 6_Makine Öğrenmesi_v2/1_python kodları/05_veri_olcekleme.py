import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import RobustScaler

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 5 (Veri Ölçekleme) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "5_Veri_Olcekleme")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "5_Veri_Olcekleme")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs for Step 5
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

source_path = os.path.join(islenmis_dir, f"4_BIST_{currency}_RFE_Secilmis.xlsx")
dest_path = os.path.join(islenmis_dir, f"5_BIST_{currency}_Scaled.xlsx")

if not os.path.exists(source_path):
    print(f"Hata: {source_path} bulunamadı! Lütfen önce Adım 4'ü çalıştırın.")
    sys.exit(1)

print(f"Loading {source_path}...")
xl = pd.ExcelFile(source_path)
sheet_names = xl.sheet_names

scaled_sheets = {}
sample_before = None
sample_after = None
sample_feature_name = ""

for sheet in sheet_names:
    print(f"\nProcessing sector: {sheet}")
    df = pd.read_excel(source_path, sheet_name=sheet)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    numeric_features = [col for col in df.columns if col not in meta_cols and df[col].dtype in ["float64", "int64"]]
    
    # Train setini al (Dönem <= 31)
    train_mask = df["Dönem"] <= 31
    df_train = df[train_mask]
    
    # Fit scaler strictly on train set to prevent data leakage!
    scaler = RobustScaler()
    scaler.fit(df_train[numeric_features].fillna(0.0))
    
    # Sample before scaling (for visualization)
    if sample_before is None and len(numeric_features) > 0:
        sample_feature_name = numeric_features[0]
        sample_before = df[sample_feature_name].fillna(0.0).copy()
        
    # Transform whole dataset
    scaled_features = scaler.transform(df[numeric_features].fillna(0.0))
    
    df_scaled = df.copy()
    df_scaled[numeric_features] = scaled_features
    
    # Sample after scaling
    if sample_after is None and len(numeric_features) > 0:
        sample_after = df_scaled[sample_feature_name].copy()
        
    scaled_sheets[sheet] = df_scaled
    print(f"  Scaling complete. Total features: {len(numeric_features)}")

print(f"\nWriting Scaled data to {dest_path}...")
with pd.ExcelWriter(dest_path, engine="xlsxwriter") as writer:
    for sheet, df_scaled in scaled_sheets.items():
        df_scaled.to_excel(writer, sheet_name=sheet, index=False)

# ── GÖRSEL ÜRETİMİ (ZORUNLU) ──────────────────────────────────────────────────
# Ölçekleme Öncesi ve Sonrası Dağılım Karşılaştırması (Boxplot)
if sample_before is not None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    sns.boxplot(data=sample_before, ax=axes[0], color='#e74c3c')
    axes[0].set_title(f"Ölçekleme Öncesi Dağılım\n({sample_feature_name})", fontsize=12, fontweight='bold')
    axes[0].set_ylabel("Orijinal Değerler")
    axes[0].grid(True, linestyle=":", alpha=0.6)
    
    sns.boxplot(data=sample_after, ax=axes[1], color='#2ecc71')
    axes[1].set_title(f"RobustScaler Sonrası Dağılım\n({sample_feature_name})", fontsize=12, fontweight='bold')
    axes[1].set_ylabel("Ölçeklenmiş Değerler")
    axes[1].grid(True, linestyle=":", alpha=0.6)
    
    plt.suptitle(f"RobustScaler ile Finansal Özelliklerin Standartlaştırılması Karşılaştırması ({currency})", fontsize=14, fontweight='bold')
    plt.tight_layout()
    gorsel_path = os.path.join(gorseller_dir, f"5_RobustScaler_Etkisi_{currency}.png")
    plt.savefig(gorsel_path, dpi=300)
    plt.close()
    print(f"Görsel başarıyla kaydedildi: {gorsel_path}")

print("Step 5 Data Scaling execution completed successfully!")
