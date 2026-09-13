import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import textwrap
from statsmodels.stats.outliers_influence import variance_inflation_factor

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
# Girdi: Adım 2'den çıkan Pearson filtreli veri
INPUT_XLSX = os.path.join(PHASE3_BASE, "raporlar", "2_Pearson_Analizleri", "2_Pearson_Filtreli_Veri.xlsx")

OUT_DIR = os.path.join(PHASE3_BASE, "raporlar", "3_VIF_Analizleri")
IMG_DIR = os.path.join(PHASE3_BASE, "görseller", "3_VIF")

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
def run_vif_analysis():
    print("\n" + "="*70)
    print("   2. FAZ - ADIM 3: ÇOKLU DOĞRUSALLIK (VIF) ANALİZİ")
    print("="*70)
    
    if not os.path.exists(INPUT_XLSX):
        print(f"Hata: Adım 2 çıktısı bulunamadı! ({INPUT_XLSX})")
        return

    xl = pd.ExcelFile(INPUT_XLSX)
    summary_report_path = os.path.join(OUT_DIR, "3_VIF_Genel_Ozet.xlsx")
    filtered_data_pool_path = os.path.join(OUT_DIR, "3_VIF_Filtreli_Veri.xlsx")
    
    global_summary = []
    global_deleted_log = []
    
    # Hedef değişken (VIF hesaplamasına dahil edilmez ama veride korunur)
    target_col = 'Net Dönem Karı/Zararı'
    VIF_THRESHOLD = 5.0

    pool_writer = pd.ExcelWriter(filtered_data_pool_path, engine='openpyxl')

    for sector in xl.sheet_names:
        print(f"\nİşleniyor: {sector}")
        df = pd.read_excel(xl, sector)
        
        ids = [c for c in df.columns if is_id_col(c)]
        # Analize girecek özellikler (Hedef ve ID hariç)
        all_features = [c for c in df.columns if not is_id_col(c) and c != target_col]
        
        print(f"   - Başlangıç özellik sayısı: {len(all_features)}")
        
        final_vif_list = all_features.copy()
        
        # İTERATİF VIF ELEME
        while True:
            if len(final_vif_list) <= 1:
                break
            
            # Numeric alt küme
            vif_data = df[final_vif_list].dropna()
            
            vif_scores = []
            for i in range(vif_data.shape[1]):
                try:
                    v = variance_inflation_factor(vif_data.values, i)
                    vif_scores.append(v)
                except:
                    vif_scores.append(9999) # Sayısal hata durumunda öncelikli ele
            
            max_vif = max(vif_scores)
            if max_vif > VIF_THRESHOLD:
                idx = vif_scores.index(max_vif)
                removed_feature = final_vif_list[idx]
                
                global_deleted_log.append({
                    "Sektör": sector, 
                    "Elenen Özellik": removed_feature, 
                    "VIF": round(max_vif, 2), 
                    "Neden": f"VIF > {VIF_THRESHOLD}"
                })
                
                print(f"     * Elendi: {removed_feature} (VIF: {max_vif:.2f})")
                final_vif_list.remove(removed_feature)
            else:
                break
        
        # Final VIF Değerleri
        final_vif_results = []
        if len(final_vif_list) > 0:
            vif_data_final = df[final_vif_list].dropna()
            for i in range(vif_data_final.shape[1]):
                final_vif_results.append({
                    "Özellik": final_vif_list[i],
                    "VIF": round(variance_inflation_factor(vif_data_final.values, i), 2)
                })
        
        final_vif_df = pd.DataFrame(final_vif_results).sort_values("VIF", ascending=False)
        
        # --- SEKTÖREL RAPOR ---
        sector_file = os.path.join(OUT_DIR, f"{sector}_VIF_Analizi.xlsx")
        with pd.ExcelWriter(sector_file, engine='xlsxwriter') as writer:
            total_after_pearson = len(all_features)
            accepted_count = len(final_vif_list)
            deleted_count = total_after_pearson - accepted_count
            
            pd.DataFrame({"Metrik": ["Pearson Sonrası", "VIF ile Elenen", "Kalan (Final)", "%"], 
                          "Değer": [total_after_pearson, deleted_count, accepted_count, f"%{accepted_count/total_after_pearson*100:.1f}"]}).to_excel(writer, sheet_name="Özet", index=False)
            final_vif_df.to_excel(writer, sheet_name="VIF_Degerleri", index=False)

        # --- GÖRSELLEŞTİRME ---
        if not final_vif_df.empty:
            plt.figure(figsize=(14, 8))
            # VIF değerlerini görselleştir
            plot_df = final_vif_df.head(20).sort_values("VIF") # En yüksek 20 özellik
            bar_plot = sns.barplot(x="VIF", y="Özellik", data=plot_df, palette="viridis", edgecolor="black")
            
            # Eşik çizgisi
            plt.axvline(x=VIF_THRESHOLD, color='red', linestyle='--', label=f'Eşik (VIF={VIF_THRESHOLD})')
            
            # Etiketleri sarmala
            plt.gca().set_yticklabels(wrap_labels(plot_df["Özellik"]))
            
            plt.title(f"{sector}\nFinal VIF Değerleri (Bilgi Tekrarı Denetimi)", fontsize=16, fontweight='bold')
            plt.xlabel("VIF Skor (Düşük Daha İyi)", fontsize=12)
            plt.ylabel("Özellik Adı", fontsize=12)
            plt.legend()
            plt.grid(axis='x', linestyle=':', alpha=0.7)
            plt.tight_layout()
            
            plt.savefig(os.path.join(IMG_DIR, f"3_VIF_Sonuclari_{sector}.png"), dpi=200)
            plt.close()



        # 5. POOL'A KAYDET
        # Hedef değişkeni en sona taşı
        final_vif_order = ids + final_vif_list + [target_col]
        df[final_vif_order].to_excel(pool_writer, sheet_name=sector, index=False)

        
        global_summary.append({
            "Sektör": sector, 
            "Pearson Sonrası": total_after_pearson, 
            "VIF Silinen": deleted_count, 
            "Final Kalan": accepted_count
        })

    pool_writer.close()

    # --- 6. MERKEZİ ÖZET ---
    with pd.ExcelWriter(summary_report_path, engine='xlsxwriter') as summary_writer:
        workbook = summary_writer.book
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#1B4F72', 'border': 1, 'align': 'center'})
        note_format = workbook.add_format({'bold': True, 'font_size': 10, 'bg_color': '#D6EAF8', 'border': 2, 'text_wrap': True})

        ws_sum = workbook.add_worksheet("VIF Özeti")
        ws_sum.set_column('A:D', 20)
        
        note_text = (f"ANALİZ METODOLOJİSİ VE ELEME KRİTERLERİ (ADIM 3)\n\n"
                    f"ÇOKLU DOĞRUSALLIK (MULTICOLLINEARITY) DENETİMİ: Özelliklerin birbirleri tarafından açıklanma oranını gösteren "
                    f"VIF (Variance Inflation Factor) değerleri hesaplanmıştır. VIF değeri {VIF_THRESHOLD:.1f} üzerinde olan özellikler "
                    f"iteratif olarak elenerek modelin kararlılığı artırılmıştır.")
        
        ws_sum.merge_range('A1:D1', note_text, note_format)
        ws_sum.set_row(0, 60)
        
        df_summary = pd.DataFrame(global_summary)
        ws_sum.write_row(1, 0, df_summary.columns, header_format)
        for r, row in enumerate(df_summary.values):
            ws_sum.write_row(2 + r, 0, row)
            
        pd.DataFrame(global_deleted_log).to_excel(summary_writer, sheet_name="VIF_Elenenler", index=False)

    print("\n" + "="*80)
    print("ADIM 3: VIF FİLTRELEME TAMAMLANDI")
    print("="*80)

if __name__ == "__main__":
    run_vif_analysis()
