import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re
from difflib import SequenceMatcher

# --- YOLLAR ---
BASE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break

STEP3_PATH = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu_Birlesik.xlsx")
STEP7_PATH = os.path.join(BASE_PATH, "raporlar", "7_Final_Veri", f"Final_Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Final_Veri_Havuzu.xlsx")

if not os.path.exists(STEP3_PATH): STEP3_PATH = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", "Veri_Havuzu_Birlesik.xlsx")
if not os.path.exists(STEP7_PATH): STEP7_PATH = os.path.join(BASE_PATH, "raporlar", "7_Final_Veri", "Final_Veri_Havuzu.xlsx")

OUT_REPORT_DIR = os.path.join(BASE_PATH, "raporlar", "8_Dogrulama_Analizi")
OUT_IMG_DIR = os.path.join(BASE_PATH, "görseller", "8_Dogrulama")

os.makedirs(OUT_REPORT_DIR, exist_ok=True)
os.makedirs(OUT_IMG_DIR, exist_ok=True)

def normalize_name(name):
    n = str(name).upper().strip()
    n = n.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
    n = re.sub(r'[\.\s]\d+$', '', n)
    n = re.sub(r'\d+$', '', n)
    n = n.replace('KARI', 'KAR').replace('K R', 'KAR')
    n = re.sub(r'[^A-Z0-9]', ' ', n)
    words = sorted([w for w in n.split() if w])
    return " ".join(words)

def is_id_col(col_name):
    n = str(col_name).upper().strip()
    n = n.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
    ident_keywords = ['DONEM', 'FIRMA ADI', 'FIRMA', 'FRMA', 'YEAR', 'MONTH', 'YIL', 'AY']
    if any(k in n for k in ident_keywords): return True
    return False

def fuzzy_similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def save_df_as_image(df, title, path):
    """Pandas DataFrame'i profesyonel bir tablo görseli olarak kaydeder."""
    if df.empty:
        return
        
    plt.figure(figsize=(14, len(df)*0.8 + 2))
    plt.axis('off')
    plt.title(title, fontsize=18, fontweight='bold', pad=30)
    
    table = plt.table(cellText=df.values, 
                      colLabels=df.columns, 
                      cellLoc='center', 
                      loc='center',
                      colColours=["#2c3e50"]*len(df.columns),
                      cellColours=[["#f8f9fa"]*len(df.columns)]*len(df))
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 3.0)
    
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
        cell.set_edgecolor('#bdc3c7')

    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()

def run_step8_final_polish():
    print("\n" + "="*60)
    print("   STEP 8: FINAL DOGRULAMA VE SUPHELI ANALIZI")
    print("="*60)

    xl3 = pd.ExcelFile(STEP3_PATH)
    xl7 = pd.ExcelFile(STEP7_PATH)

    summary_stats = []
    all_fuzzy_reports = []

    for sector in xl7.sheet_names:
        print(f"\nSektör İşleniyor: {sector}")
        
        df3 = pd.read_excel(xl3, sheet_name=sector)
        df7 = pd.read_excel(xl7, sheet_name=sector)

        id_cols = [c for c in df7.columns if is_id_col(c)]
        features = [c for c in df7.columns if c not in id_cols]

        # --- 1. Klasik Analiz ---
        initial_features = [c for c in df3.columns if not is_id_col(c)]
        norm_initial = set([normalize_name(c) for c in initial_features])
        
        # --- 2. FUZZY (Benzerlik) Analizi - ŞÜPHELİLER ---
        print(f"  - Şüpheli (Benzer İsimli) Özellikler Aranıyor...")
        sector_fuzzy = []
        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                ratio = fuzzy_similar(features[i], features[j])
                if ratio > 0.85: # %85 benzerlik eşiği
                    sector_fuzzy.append({
                        "Sektör": sector,
                        "Özellik 1": features[i],
                        "Özellik 2": features[j],
                        "Benzerlik (%)": round(ratio * 100, 2)
                    })
        
        all_fuzzy_reports.extend(sector_fuzzy)

        summary_stats.append({
            "Sektör": sector,
            "Ham Özellik": len(initial_features),
            "Birleştirilen": len(initial_features) - len(norm_initial),
            "Eşik Altı Atılan": len(norm_initial) - len(features),
            "Final Özellik": len(features),
            "Şüpheli Sayısı": len(sector_fuzzy)
        })

        # --- 3. ANLAMLI ISI HARİTASI ---
        if 'Dönem' in df7.columns:
            top_n = min(40, len(features))
            df7_sorted = df7.sort_values(by='Dönem')
            pivot_data = df7_sorted.groupby('Dönem')[features[:top_n]].apply(lambda x: x.notna().mean() * 100)
            
            plt.figure(figsize=(20, 10))
            sns.heatmap(pivot_data, cmap="RdYlGn", annot=False, cbar_kws={'label': 'Doluluk (%)'}, linewidths=.5)
            plt.title(f"{sector}: Dönemsel Veri Tamlığı (Top {top_n})", fontsize=18, fontweight='bold', pad=20)
            heatmap_path = os.path.join(OUT_IMG_DIR, f"8_Anlamli_Heatmap_{sector.replace(' ', '_')}.png")
            plt.tight_layout()
            plt.savefig(heatmap_path, dpi=300)
            plt.close()

    # --- Özet Raporlar ---
    summary_df = pd.DataFrame(summary_stats)
    summary_report_name = f"8_Ozet_Final_Raporu_{CURRENCY}.xlsx" if CURRENCY else "8_Ozet_Final_Raporu.xlsx"
    summary_df.to_excel(os.path.join(OUT_REPORT_DIR, summary_report_name), index=False)
    save_df_as_image(summary_df, "Step 8: Final Doğrulama Özeti", os.path.join(OUT_IMG_DIR, f"8_Final_Ozet_Tablo_{CURRENCY}.png" if CURRENCY else "8_Final_Ozet_Tablo.png"))
    
    # --- Şüpheli Raporu ve Görselleştirme ---
    fuzzy_df = pd.DataFrame(all_fuzzy_reports)
    if not fuzzy_df.empty:
        fuzzy_report_name = f"8_Supheli_Benzerlik_Listesi_{CURRENCY}.xlsx" if CURRENCY else "8_Supheli_Benzerlik_Listesi.xlsx"
        fuzzy_df.to_excel(os.path.join(OUT_REPORT_DIR, fuzzy_report_name), index=False)
        # Sadece en yüksek benzerliğe sahip ilk 15 şüpheliyi görselleştir (tablo çok uzamasın)
        top_fuzzy = fuzzy_df.sort_values(by="Benzerlik (%)", ascending=False).head(15)
        save_df_as_image(top_fuzzy, "Adım 8: En Şüpheli Benzer Özellikler (Top 15)", os.path.join(OUT_IMG_DIR, "8_Supheli_Tablo_Gorseli.png"))
        print(f"\n[!] {len(fuzzy_df)} adet şüpheli benzerlik bulundu. Rapor ve görsel oluşturuldu.")
    else:
        print("\n[OK] Herhangi bir şüpheli benzerlik (benzer isimli farklı sütun) bulunamadı.")

    # --- Özellik Akış Grafiği ---
    plt.figure(figsize=(15, 8))
    ax = summary_df.set_index("Sektör")[["Final Özellik", "Eşik Altı Atılan", "Birleştirilen"]].plot(
        kind='bar', stacked=True, color=['#27ae60', '#e74c3c', '#3498db'], figsize=(14, 8)
    )
    plt.title("Veri Temizleme Süreci Atılım Analizi", fontsize=18, fontweight='bold', pad=20)
    for p in ax.patches:
        height = p.get_height()
        if height > 5:
            ax.text(p.get_x()+p.get_width()/2, p.get_y()+height/2, f'{int(height)}', ha='center', va='center', color='white', fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_IMG_DIR, "8_Final_Ozellik_Akisi.png"), dpi=300)
    plt.close()

    print("\n" + "="*80)
    print("   ANALIZ TAMAMLANDI - TÜM RAPORLAR VE ŞÜPHELİ LİSTESİ OLUŞTURULDU")
    print("="*80)

if __name__ == "__main__":
    run_step8_final_polish()
