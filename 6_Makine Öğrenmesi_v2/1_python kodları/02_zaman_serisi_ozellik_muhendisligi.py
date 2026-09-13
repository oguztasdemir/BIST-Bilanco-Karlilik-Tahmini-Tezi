import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 2 (Zaman Serisi Özellik Mühendisliği) for currency: {currency}")

# Add root folder to sys.path to import kullanici.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
islenmis_dir = os.path.join(ml_dir, "00_dataset", "islenmis_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "2_Feature_Engineering")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "2_Feature_Engineering")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs for Step 2
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

# Kaynak veri: Adım 1'den gelen temizlenmiş veri
source_path = os.path.join(islenmis_dir, f"1_BIST_{currency}_Temiz.xlsx")
dest_path = os.path.join(islenmis_dir, f"2_BIST_{currency}_Feature_Engineered.xlsx")

if not os.path.exists(source_path):
    print(f"Hata: {source_path} bulunamadı! Lütfen önce Adım 1'i çalıştırın.")
    sys.exit(1)

print(f"Loading {source_path}...")
xl = pd.ExcelFile(source_path)
sheet_names = xl.sheet_names

engineered_sheets = {}
report_data = []

for sheet in sheet_names:
    print(f"\nProcessing sector: {sheet}")
    df = pd.read_excel(source_path, sheet_name=sheet)
    
    # Hedef sütunu bul
    target_cols = [col for col in df.columns if "t+1" in col]
    if not target_cols:
        continue
    target_col = target_cols[0]
    
    # Sıralama: Firma Adı ve Dönem'e göre (Zaman serisi mantığı için şart)
    df = df.sort_values(by=["Firma Adı", "Dönem"]).reset_index(drop=True)
    
    meta_cols = ["Dönem", "Firma Adı", "Anomali_Durumu", "Net Dönem Karı/Zararı", target_col]
    numeric_features = [col for col in df.columns if col not in meta_cols and df[col].dtype in ["float64", "int64"]]
    
    initial_col_count = len(df.columns)
    
    # Feature Engineering
    new_cols_df_list = []
    grouped = df.groupby("Firma Adı")
    
    for col in numeric_features:
        lag_col = grouped[col].shift(1)
        pct_col = grouped[col].pct_change().replace([np.inf, -np.inf], 0.0)
        ma_col = grouped[col].transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        
        new_features = pd.DataFrame({
            f"{col}_Lag1": lag_col,
            f"{col}_Momentum": pct_col,
            f"{col}_MA3": ma_col
        })
        new_cols_df_list.append(new_features)
    
    if new_cols_df_list:
        new_features_df = pd.concat(new_cols_df_list, axis=1)
        df = pd.concat([df, new_features_df], axis=1)
        
    new_feature_names = new_features_df.columns if new_cols_df_list else []
    df[new_feature_names] = df[new_feature_names].fillna(0.0)
    
    final_col_count = len(df.columns)
    engineered_sheets[sheet] = df
    
    report_data.append({
        "Sektör": sheet,
        "Orjinal Özellik": initial_col_count - len(meta_cols),
        "Türetilen Özellik": final_col_count - initial_col_count,
        "Toplam Özellik": final_col_count - len(meta_cols)
    })
    print(f"  Orijinal Özellik: {initial_col_count} | Türetilen: {final_col_count - initial_col_count} | Toplam: {final_col_count}")

print(f"\nWriting engineered data to {dest_path}...")
with pd.ExcelWriter(dest_path, engine="xlsxwriter") as writer:
    for sheet, df_eng in engineered_sheets.items():
        df_eng.to_excel(writer, sheet_name=sheet, index=False)

# Raporu kaydet
report_df = pd.DataFrame(report_data)
report_path = os.path.join(output_dir, f"2_Feature_Engineering_Raporu_{currency}.xlsx")
report_df.to_excel(report_path, index=False)

# ── GÖRSEL ÜRETİMİ (ZORUNLU) ──────────────────────────────────────────────────
# Sektörlere göre Özellik Sayısı Artış Grafiği (Stacked Bar Plot)
plt.figure(figsize=(12, 6))
bar_width = 0.5
r = np.arange(len(report_df))

plt.bar(r, report_df["Orjinal Özellik"], color='#34495e', edgecolor='white', width=bar_width, label='Orijinal Finansal Rasyolar')
plt.bar(r, report_df["Türetilen Özellik"], bottom=report_df["Orjinal Özellik"], color='#3498db', edgecolor='white', width=bar_width, label='Türetilen Özellikler (Lag, Momentum, MA)')

plt.xlabel('Sektörler', fontweight='bold', fontsize=12)
plt.ylabel('Özellik (Feature) Sayısı', fontweight='bold', fontsize=12)
plt.xticks(r, report_df["Sektör"], rotation=45, ha="right")
plt.title(f"Sektörel Bazda Zaman Serisi Özellik Mühendisliği Genişleme Analizi ({currency})", fontsize=14, fontweight='bold', pad=15)
plt.legend(loc='upper left')
plt.grid(axis='y', linestyle=':', alpha=0.5)

# Barların üzerine toplam sayıyı yazma
for i in range(len(report_df)):
    total = report_df["Toplam Özellik"].iloc[i]
    orig = report_df["Orjinal Özellik"].iloc[i]
    turet = report_df["Türetilen Özellik"].iloc[i]
    plt.text(i, total + 2, f"{total}\n(+{turet})", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#2c3e50')

plt.tight_layout()
gorsel_path = os.path.join(gorseller_dir, f"2_Feature_Engineering_Artis_{currency}.png")
plt.savefig(gorsel_path, dpi=300)
plt.close()
print(f"Görsel başarıyla kaydedildi: {gorsel_path}")

print("Step 2 Feature Engineering execution completed successfully!")
