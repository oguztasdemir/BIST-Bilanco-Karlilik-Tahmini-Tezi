import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# --- YOLLAR ---
BASE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break

DATA_BEFORE = os.path.join(BASE_PATH, "0_Datasetler", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu_USD.xlsx")
DATA_AFTER = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu_Birlesik.xlsx")

if not CURRENCY:
    if "USD" in DATA_BEFORE: CURRENCY = "USD"
    elif "EUR" in DATA_BEFORE: CURRENCY = "EUR"
    elif "TRY" in DATA_BEFORE: CURRENCY = "TRY"

OUT_DIR = os.path.join(BASE_PATH, "görseller", "4_Gorsellestirme")
os.makedirs(OUT_DIR, exist_ok=True)

def sanitize_sheet_name(name):
    return re.sub(r'[\\/*?:\[\]]', '', str(name))[:31]

def get_metrics(file_path, is_before=True):
    print(f"Veriler okunuyor: {os.path.basename(file_path)}")
    xl = pd.ExcelFile(file_path)
    metrics = []
    
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        # ID kolonlarını ayıkla (3_veri_birlestirme.py ile aynı mantık)
        id_cols = [c for c in df.columns if any(x in str(c).upper() for x in ['FRMA', 'FIRMA', 'DNEM', 'DÖNEM', 'YEAR', 'MONTH'])]
        feature_cols = [c for c in df.columns if c not in id_cols]
        
        num_features = len(feature_cols)
        total_rows = len(df)
        
        if num_features > 0 and total_rows > 0:
            # Tüm hücreler içindeki doluluk oranı
            fill_rate = (df[feature_cols].notna().sum().sum() / (total_rows * num_features)) * 100
        else:
            fill_rate = 0
            
        metrics.append({
            "Sektör": sanitize_sheet_name(sheet),
            "Özellik Sayısı": num_features,
            "Doluluk Oranı (%)": fill_rate,
            "Durum": "Öncesi" if is_before else "Sonrası"
        })
    return pd.DataFrame(metrics)

def run_visualization():
    print("--- Step 4: Birleştirme Etki Analizi Görselleştirmesi ---")
    
    if not os.path.exists(DATA_BEFORE) or not os.path.exists(DATA_AFTER):
        print("Hata: Gerekli veri dosyaları bulunamadı!")
        return

    # Metrikleri topla
    df_before = get_metrics(DATA_BEFORE, is_before=True)
    df_after = get_metrics(DATA_AFTER, is_before=False)
    
    # Verileri birleştir
    combined_df = pd.concat([df_before, df_after], axis=0)
    
    # Görselleştirme Ayarları
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Roboto', 'Arial']
    
    # 2 Subplot oluştur (Üst üste)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
    plt.subplots_adjust(hspace=0.4)

    # GRAFİK 1: Özellik Sayısı
    sns.barplot(
        data=combined_df, 
        x="Sektör", y="Özellik Sayısı", hue="Durum",
        ax=ax1, palette=["#ff9999", "#66b3ff"],
        edgecolor="0.2"
    )
    ax1.set_title("Sektör Bazlı Özellik Sayısı Karşılaştırması (Feature Consolidation)", fontsize=16, fontweight='bold', pad=20)
    ax1.set_xlabel("")
    ax1.tick_params(axis='x', rotation=15)
    
    # Değerleri barların üzerine yaz (Plot 1)
    for p in ax1.patches:
        ax1.annotate(f'{int(p.get_height())}', 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha = 'center', va = 'center', 
                   xytext = (0, 9), 
                   textcoords = 'offset points',
                   fontsize=10, fontweight='bold')

    # GRAFİK 2: Doluluk Oranı
    sns.barplot(
        data=combined_df, 
        x="Sektör", y="Doluluk Oranı (%)", hue="Durum",
        ax=ax2, palette=["#ffcc99", "#99ff99"],
        edgecolor="0.2"
    )
    ax2.set_title("Sektör Bazlı Ortalama Doluluk Oranı Karşılaştırması (%)", fontsize=16, fontweight='bold', pad=20)
    ax2.set_xlabel("Sektörler", fontsize=12)
    ax2.set_ylabel("Doluluk Oranı (%)", fontsize=12)
    ax2.set_ylim(0, 110)
    ax2.tick_params(axis='x', rotation=15)

    # Değerleri barların üzerine yaz (Plot 2)
    for p in ax2.patches:
        ax2.annotate(f'%{p.get_height():.1f}', 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha = 'center', va = 'center', 
                   xytext = (0, 9), 
                   textcoords = 'offset points',
                   fontsize=10, fontweight='bold')

    # PDF/Görsel Kaydet
    output_name = f"Birlestirme_Etki_Analizi_{CURRENCY}.png" if CURRENCY else "Birlestirme_Etki_Analizi.png"
    output_path = os.path.join(OUT_DIR, output_name)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # EXCEL RAPORU OLUŞTUR (Anlaşılabilir Tablo)
    report_df = df_before.merge(df_after, on="Sektör", suffixes=(' (Önce)', ' (Sonra)'))
    
    # Gereksiz "Durum" kolonlarını sil
    report_df = report_df.drop(columns=['Durum (Önce)', 'Durum (Sonra)'])
    
    # Değişim yüzdelerini hesapla
    report_df['Özellik Azalma (%)'] = round((1 - report_df['Özellik Sayısı (Sonra)'] / report_df['Özellik Sayısı (Önce)']) * 100, 2)
    report_df['Doluluk Artışı (%)'] = round(report_df['Doluluk Oranı (%) (Sonra)'] - report_df['Doluluk Oranı (%) (Önce)'], 2)
    
    # Sütun sırasını düzenle
    cols = ['Sektör', 'Özellik Sayısı (Önce)', 'Özellik Sayısı (Sonra)', 'Özellik Azalma (%)', 
            'Doluluk Oranı (%) (Önce)', 'Doluluk Oranı (%) (Sonra)', 'Doluluk Artışı (%)']
    report_df = report_df[cols]
    
    excel_name = f"4_Birlesme_Etki_Raporu_{CURRENCY}.xlsx" if CURRENCY else "4_Birlesme_Etki_Raporu.xlsx"
    excel_dir = os.path.join(BASE_PATH, "raporlar", "4_Birlesme_Analizi")
    os.makedirs(excel_dir, exist_ok=True)
    excel_path = os.path.join(excel_dir, excel_name)
    report_df.to_excel(excel_path, index=False)
    
    print(f"\nAnaliz tamamlandı.")
    print(f"  - Görsel: {output_path}")
    print(f"  - Excel Raporu: {excel_path}")

if __name__ == "__main__":
    run_visualization()
