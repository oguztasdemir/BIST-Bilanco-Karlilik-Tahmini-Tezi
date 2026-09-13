import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 3 (HIZLI VIF Çoklu Doğrusal Bağlantı) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "3_VIF_Analizi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "3_VIF_Analizi")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs for Step 3
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

source_path = os.path.join(islenmis_dir, f"2_BIST_{currency}_Feature_Engineered.xlsx")
dest_path = os.path.join(islenmis_dir, f"3_BIST_{currency}_VIF_Temiz.xlsx")

if not os.path.exists(source_path):
    print(f"Hata: {source_path} bulunamadı! Lütfen önce Adım 2'yi çalıştırın.")
    sys.exit(1)

print(f"Loading {source_path}...")
xl = pd.ExcelFile(source_path)
sheet_names = xl.sheet_names

cleaned_sheets = {}
report_data = []

# Matris Tersine Çevirme Mantığı ile Ultra Hızlı VIF Elemesi
def calculate_fast_vif_drop(df_feats, thresh=10.0):
    cols = list(df_feats.columns)
    dropped_cols = []
    
    variances = df_feats.var()
    constant_cols = variances[variances == 0].index.tolist()
    for c in constant_cols:
        cols.remove(c)
        dropped_cols.append((c, 99999.0))
        
    while True:
        if len(cols) <= 1:
            break
            
        X = df_feats[cols].values
        corr = np.corrcoef(X, rowvar=False)
        corr = corr + np.eye(corr.shape[0]) * 1e-8
        
        try:
            inv_corr = np.linalg.inv(corr)
            vifs = np.diag(inv_corr)
        except np.linalg.LinAlgError:
            inv_corr = np.linalg.pinv(corr)
            vifs = np.diag(inv_corr)
            
        max_idx = np.argmax(vifs)
        max_vif = vifs[max_idx]
        
        if max_vif > thresh:
            col_to_drop = cols[max_idx]
            cols.remove(col_to_drop)
            dropped_cols.append((col_to_drop, max_vif))
        else:
            break
            
    return cols, dropped_cols

for sheet in sheet_names:
    print(f"\nProcessing sector: {sheet}")
    df = pd.read_excel(source_path, sheet_name=sheet)
    
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    numeric_features = [col for col in df.columns if col not in meta_cols and df[col].dtype in ["float64", "int64"]]
    
    X = df[numeric_features].fillna(0.0)
    
    print(f"  Starting Fast VIF elimination with {len(numeric_features)} features...")
    selected_features, dropped_cols = calculate_fast_vif_drop(X, thresh=10.0)
    
    final_cols = meta_cols + selected_features
    df_cleaned = df[final_cols].copy()
    cleaned_sheets[sheet] = df_cleaned
    
    report_data.append({
        "Sektör": sheet,
        "Başlangıç Özellik Sayısı": len(numeric_features),
        "Kalan Özellik Sayısı": len(selected_features),
        "Elenen Özellik Sayısı": len(numeric_features) - len(selected_features)
    })
    print(f"  Fast VIF Complete. Remaining features: {len(selected_features)}")

print(f"\nWriting VIF cleaned data to {dest_path}...")
with pd.ExcelWriter(dest_path, engine="xlsxwriter") as writer:
    for sheet, df_cleaned in cleaned_sheets.items():
        df_cleaned.to_excel(writer, sheet_name=sheet, index=False)

report_df = pd.DataFrame(report_data)
report_path = os.path.join(output_dir, f"3_VIF_Eleme_Raporu_{currency}.xlsx")
report_df.to_excel(report_path, index=False)

# ── GÖRSEL ÜRETİMİ (ZORUNLU) ──────────────────────────────────────────────────
# VIF Sonrası Kalan vs Elenen Özellikler Grafiği
plt.figure(figsize=(12, 6))
bar_width = 0.5
r = np.arange(len(report_df))

plt.bar(r, report_df["Kalan Özellik Sayısı"], color='#2ecc71', edgecolor='white', width=bar_width, label='VIF Geçen (Kalan Özellikler)')
plt.bar(r, report_df["Elenen Özellik Sayısı"], bottom=report_df["Kalan Özellik Sayısı"], color='#e74c3c', edgecolor='white', width=bar_width, label='VIF Elenen (Çoklu Doğrusal Bağlantı)')

plt.xlabel('Sektörler', fontweight='bold', fontsize=12)
plt.ylabel('Özellik Sayısı', fontweight='bold', fontsize=12)
plt.xticks(r, report_df["Sektör"], rotation=45, ha="right")
plt.title(f"Sektörel Bazda VIF Analizi Kalan vs Elenen Özellik Sayıları ({currency})", fontsize=14, fontweight='bold', pad=15)
plt.legend(loc='upper right')
plt.grid(axis='y', linestyle=':', alpha=0.5)

# Barların üzerine sayıların eklenmesi
for i in range(len(report_df)):
    kalan = report_df["Kalan Özellik Sayısı"].iloc[i]
    toplam = report_df["Başlangıç Özellik Sayısı"].iloc[i]
    plt.text(i, toplam + 2, f"{kalan} / {toplam}", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2c3e50')

plt.tight_layout()
gorsel_path = os.path.join(gorseller_dir, f"3_VIF_Kalan_Ozellikler_{currency}.png")
plt.savefig(gorsel_path, dpi=300)
plt.close()
print(f"Görsel başarıyla kaydedildi: {gorsel_path}")

print("Step 3 Fast VIF execution completed successfully!")
