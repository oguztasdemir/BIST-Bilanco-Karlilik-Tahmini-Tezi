import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import textwrap

# --- KULLANICI MODÜLÜ ENTEGRASYONU ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.append(project_root)
    import kullanici as kb
except ImportError:
    print("Hata: 'kullanici.py' bulunamadı.")
    exit(1)

# --- YOLLAR ---
BASE_PATH = kb.klasor
PHASE3_BASE = os.path.join(BASE_PATH, "3_Özellik Seçimi")
FINAL_DATA_PATH = os.path.join(PHASE3_BASE, "raporlar", "3_VIF_Analizleri", "3_VIF_Filtreli_Veri.xlsx")

OUT_DIR = os.path.join(PHASE3_BASE, "görseller", "4_Final_Ozet")
os.makedirs(OUT_DIR, exist_ok=True)

FINAL_IMG_PATH = os.path.join(OUT_DIR, "Final_Ozellik_Varlik_Matrisi.png")
TARGET_COL = 'Net Dönem Karı/Zararı'

def normalize_text(text):

    if not isinstance(text, str): return str(text)
    n = text.upper().strip()
    n = n.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
    return n

def is_id_col(col_name):
    n = normalize_text(col_name)
    ident_keywords = ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY']
    return any(k in n for k in ident_keywords) or len(n) < 3

def wrap_labels(labels, width=40):

    return [textwrap.fill(label, width=width) for label in labels]

def run_matrix_visualization():
    print("\n" + "="*70)
    print("   2. FAZ - ADIM 5: FİNAL ÖZELLİK VARLIK MATRİSİ GÖRSELLEŞTİRME")
    print("="*70)
    
    if not os.path.exists(FINAL_DATA_PATH):
        print(f"Hata: Final veri bulunamadı! ({FINAL_DATA_PATH})")
        return

    xl = pd.ExcelFile(FINAL_DATA_PATH)
    
    # 1. Tüm benzersiz özellikleri topla
    all_final_features = set()
    sector_features = {}
    
    for sector in xl.sheet_names:
        df = pd.read_excel(xl, sector)
        # Hedef dahil özellikleri al
        feats = [c for c in df.columns if not is_id_col(c) or c == TARGET_COL]
        all_final_features.update(feats)
        sector_features[sector] = set(feats)
    
    # 2. Sıralama Mantığı: Öznitelikler Alfabetik + En Sonda Hedef
    other_features = sorted([f for f in all_final_features if f != TARGET_COL])
    sorted_features = other_features + [TARGET_COL]
    sectors = xl.sheet_names

    
    # 2. Varlık Matrisi Oluştur (Binary)
    matrix_data = []
    for feat in sorted_features:
        row = {"Özellik": feat}
        for sector in sectors:
            row[sector] = 1 if feat in sector_features[sector] else 0
        matrix_data.append(row)
    
    df_matrix = pd.DataFrame(matrix_data).set_index("Özellik")
    
    # 3. Görselleştirme (Stil ve Boyut Optimizasyonu)
    # Dinamik figür boyutu
    fig_height = max(14, len(sorted_features) * 0.45)
    plt.figure(figsize=(24, fig_height))
    
    # Isı haritası çizimi
    cmap = sns.color_palette(["#F2F4F4", "#1F618D"]) # Daha doygun bir mavi
    
    ax = sns.heatmap(df_matrix, cmap=cmap, cbar=False, linewidths=1.2, linecolor='#EBEDEF', alpha=0.95)
    
    # Sektör isimlerini (X ekseni) yukarı al
    ax.xaxis.tick_top()
    plt.xticks(rotation=45, ha='left', fontsize=12, fontweight='bold', color='#1B4F72')
    
    # Y ekseni etiketlerini (Özellikler) sar ve optimize et
    # Hedef değişkeni bold yapalım
    ytick_labels = wrap_labels(df_matrix.index, width=55)
    ax.set_yticklabels(ytick_labels, rotation=0, fontsize=10.5)
    
    # Hedef değişken etiketini kalın yap (en sonuncu)
    ax.get_yticklabels()[-1].set_fontweight('bold')
    ax.get_yticklabels()[-1].set_color('red') # Hedef fark edilsin
    
    plt.title("FİNAL ÖZNİTELİK VE HEDEF DEĞİŞKEN VARLIK MATRİSİ\n", fontsize=22, fontweight='bold', pad=30, color='#154360')
    plt.ylabel("Seçilen Öznitelikler ve Hedef", fontsize=14, fontweight='bold')
    
    # Legend ekle (Daha şık)
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#1F618D', edgecolor='black', label='Modele Dahil Edildi / Bağımlı Değişken'),
        Patch(facecolor='#F2F4F4', edgecolor='black', label='Filtrede Elendi / Veride Yok')
    ]
    plt.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.04), ncol=2, fontsize=13, frameon=True, shadow=True)
    
    plt.tight_layout()
    
    plt.savefig(FINAL_IMG_PATH, dpi=220)
    plt.close()


    print("\n" + "="*80)
    print("ADIM 5: VARLIK MATRİSİ GÖRSELİ OLUŞTURULDU")
    print(f"Yol: {FINAL_IMG_PATH}")
    print("="*80)

if __name__ == "__main__":
    run_matrix_visualization()
