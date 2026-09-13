import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import textwrap
import xlsxwriter

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
PHASE2_DATA = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "3_Zaman_Serisi_Final", "Final_Veri_USD_USD_Indexed.xlsx")
PHASE3_BASE = os.path.join(BASE_PATH, "3_Özellik Seçimi")
OUT_DIR = os.path.join(PHASE3_BASE, "raporlar", "1_Varyans_Filtresi")
IMG_DIR = os.path.join(PHASE3_BASE, "görseller", "1_Varyans")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# --- YARDIMCI FONKSİYONLAR ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    n = text.upper().strip()
    n = n.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
    return n

def wrap_labels(labels, width=25):
    return [textwrap.fill(label, width=width) for label in labels]

def is_id_col(col_name):
    n = normalize_text(col_name)
    ident_keywords = ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY']
    return any(k in n for k in ident_keywords) and len(n) < 15

# --- ANA İŞLEM ---
def run_variance_filter():
    print("\n" + "="*70)
    print("   2. FAZ - ADIM 1: VARYANS EŞİĞİ FİLTRESİ")
    print("="*70)
    
    xl = pd.ExcelFile(PHASE2_DATA)
    summary_report_path = os.path.join(OUT_DIR, "1_Varyans_Genel_Ozet.xlsx")
    filtered_data_pool_path = os.path.join(OUT_DIR, "1_Varyans_Filtreli_Veri.xlsx")
    
    global_summary = []
    global_deleted_log = []
    
    # EŞİK DEĞERLERİ
    # Bir kolonun değerlerinin %95'i aynıysa o kolon 'yarı-sabit' kabul edilir ve elenir.
    CONSTANT_THRESHOLD = 0.95 
    TARGET_COL = 'Net Dönem Karı/Zararı'

    pool_writer = pd.ExcelWriter(filtered_data_pool_path, engine='openpyxl')


    for sector in xl.sheet_names:
        print(f"\nİşleniyor: {sector}")
        df = pd.read_excel(xl, sector)
        
        ids = [c for c in df.columns if is_id_col(c)]
        # Hedef değişkeni öznitelik elemelerinden ayır
        feats = [c for c in df.columns if not is_id_col(c) and c != TARGET_COL and pd.api.types.is_numeric_dtype(df[c])]
        
        total_feats_start = len(feats)

        deleted_feats = []
        keep_feats = []

        for f in feats:
            # 1. Sabitlik Kontrolü (Aynı değer oranı)
            value_counts = df[f].value_counts(normalize=True)
            if not value_counts.empty:
                top_value_ratio = value_counts.iloc[0]
                
                if top_value_ratio >= CONSTANT_THRESHOLD:
                    deleted_feats.append(f)
                    global_deleted_log.append({
                        "Sektör": sector, 
                        "Elenen Özellik": f, 
                        "En Sık Değer Oranı": f"%{top_value_ratio*100:.1f}", 
                        "Neden": "Düşük Varyans / Sabit Değişken"
                    })
                else:
                    keep_feats.append(f)
            else:
                deleted_feats.append(f) # Boş kolon

        # --- SEKTÖREL KAYIT ---
        # Hedef değişkeni en sona ekle
        col_order = ids + keep_feats + [TARGET_COL]
        df[col_order].to_excel(pool_writer, sheet_name=sector, index=False)

        
        global_summary.append({
            "Sektör": sector,
            "Başlangıç Özellik": total_feats_start,
            "Silinen (Düşük Varyans)": len(deleted_feats),
            "Kalan": len(keep_feats)
        })

        # --- GÖRSELLEŞTİRME ---
        # Tüm özelliklerin "Konsantrasyon" (Tekdüzelik) oranlarını topla
        concentration_data = []
        for f in feats:
            vc = df[f].value_counts(normalize=True)
            if not vc.empty:
                concentration_data.append({"Özellik": f, "Oran": vc.iloc[0]})
        
        if concentration_data:
            plt.figure(figsize=(15, 9))
            plot_df = pd.DataFrame(concentration_data).sort_values("Oran", ascending=False).head(25)
            
            # Renkleri belirle (Eşiği geçenler farklı renk olsun)
            colors = ['#E74C3C' if x >= CONSTANT_THRESHOLD else '#3498DB' for x in plot_df["Oran"]]
            
            sns.barplot(x="Oran", y="Özellik", data=plot_df, palette=colors, edgecolor='black', alpha=0.8)
            
            # Eşik çizgisi
            plt.axvline(x=CONSTANT_THRESHOLD, color='red', linestyle='--', label=f'Eleme Eşiği (%{CONSTANT_THRESHOLD*100:.0f})')
            
            # Etiketleri sarmala
            plt.gca().set_yticklabels(wrap_labels(plot_df["Özellik"]))
            
            plt.title(f"{sector}\nÖzellikler Arası Tekdüzelik Dağılımı (Konsantrasyon Analizi)", fontsize=16, fontweight='bold')
            plt.xlabel("En Sık Değerin Oranı (1.00 = Sabit)", fontsize=12)
            plt.ylabel("Özellik Adı", fontsize=12)
            plt.legend()
            plt.grid(axis='x', linestyle=':', alpha=0.6)
            plt.tight_layout()
            
            plt.savefig(os.path.join(IMG_DIR, f"1_Varyans_Dagilimi_{sector}.png"), dpi=180)
            plt.close()

        print(f"   - {total_feats_start} özellikten {len(deleted_feats)} tanesi elendi. Kalan: {len(keep_feats)}")


    pool_writer.close()

    # --- MERKEZİ ÖZET ---
    with pd.ExcelWriter(summary_report_path, engine='xlsxwriter') as summary_writer:
        workbook = summary_writer.book
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#512E5F', 'border': 1, 'align': 'center'})
        note_format = workbook.add_format({'bold': True, 'font_size': 10, 'bg_color': '#F5EEF8', 'border': 2, 'text_wrap': True})

        ws_sum = workbook.add_worksheet("Varyans Özeti")
        ws_sum.set_column('A:D', 20)
        
        note_text = (f"ANALİZ METODOLOJİSİ VE ELEME KRİTERLERİ (ADIM 1)\n\n"
                    f"VARYANS FİLTRESİ: Bir özelliğin içindeki değerlerin %{CONSTANT_THRESHOLD*100:.0f}'i aynıysa, "
                    f"bu değişkenin şirketleri birbirinden ayırma gücü olmadığı kabul edilerek elenmiştir. "
                    f"Bu adım, veri kümesini 'bilgi taşımayan' kalabalıktan temizlemek için uygulanır.")
        
        ws_sum.merge_range('A1:D1', note_text, note_format)
        ws_sum.set_row(0, 70)
        
        df_summary = pd.DataFrame(global_summary)
        ws_sum.write_row(1, 0, df_summary.columns, header_format)
        for r, row in enumerate(df_summary.values):
            ws_sum.write_row(2 + r, 0, row)
            
        pd.DataFrame(global_deleted_log).to_excel(summary_writer, sheet_name="Elenenler_Varyans", index=False)

    print("\n" + "="*80)
    print("ADIM 1: VARYANS FİLTRELEME TAMAMLANDI")
    print("="*80)

if __name__ == "__main__":
    run_variance_filter()
