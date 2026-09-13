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
# Girdi: Adım 1'den çıkan varyans filtreli veri
PHASE3_BASE = os.path.join(BASE_PATH, "3_Özellik Seçimi")
PHASE1_DATA = os.path.join(PHASE3_BASE, "raporlar", "1_Varyans_Filtresi", "1_Varyans_Filtreli_Veri.xlsx")
OUT_DIR = os.path.join(PHASE3_BASE, "raporlar", "2_Pearson_Analizleri")
IMG_DIR = os.path.join(PHASE3_BASE, "görseller", "2_Pearson")

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
def run_pearson_analysis():
    print("\n" + "="*70)
    print("   2. FAZ - ADIM 2: HEDEF ODAKLI PEARSON ANALİZİ")
    print("="*70)
    
    if not os.path.exists(PHASE1_DATA):
        print(f"Hata: Adım 1 çıktısı bulunamadı! ({PHASE1_DATA})")
        return
    
    xl = pd.ExcelFile(PHASE1_DATA)
    summary_report_path = os.path.join(OUT_DIR, "2_Pearson_Genel_Ozet.xlsx")
    filtered_data_pool_path = os.path.join(OUT_DIR, "2_Pearson_Filtreli_Veri.xlsx")
    
    global_summary = []
    global_deleted_log = []
    
    # ANA HEDEF DEĞİŞKEN
    target_col = 'Net Dönem Karı/Zararı'
    CORR_THRESHOLD = 0.10

    pool_writer = pd.ExcelWriter(filtered_data_pool_path, engine='openpyxl')

    for sector in xl.sheet_names:
        print(f"\nİşleniyor: {sector}")
        df = pd.read_excel(xl, sector)
        
        # ID kolonlarını ayır
        ids = [c for c in df.columns if is_id_col(c)]
        
        if target_col not in df.columns:
            print(f"Uyarı: {target_col} kolonu {sector} sayfasında bulunamadı!")
            continue

        # --- YENİ: Sütün Sıralamasını Düzenle (Target En Başta) ---
        all_numeric_cols = [c for c in df.columns if not is_id_col(c) and pd.api.types.is_numeric_dtype(df[c])]
        if target_col in all_numeric_cols:
            all_numeric_cols.remove(target_col)
        ordered_cols = [target_col] + all_numeric_cols
        X_full = df[ordered_cols].copy()


        # 1. KORELASYON HESAPLAMA
        full_corr = X_full.corr()
        target_corrs = full_corr[target_col].drop(target_col)
        
        # 2. ELEME (abs > 0.1)
        pruning_df = pd.DataFrame({
            "Özellik Adı": target_corrs.index,
            "Pearson": target_corrs.values,
            "Mutlak": target_corrs.abs().values
        })
        pruning_df["DURUM"] = np.where(pruning_df["Mutlak"] >= CORR_THRESHOLD, "KABUL", "RED")
        pruning_df = pruning_df.sort_values("Mutlak", ascending=False)
        
        deleted_ones = pruning_df[pruning_df["DURUM"] == "RED"]
        for _, row in deleted_ones.iterrows():
            global_deleted_log.append({
                "Sektör": sector, "Elenen Özellik": row["Özellik Adı"], 
                "Değer": round(row["Pearson"], 4), "Neden": f"Zayıf Korelasyon (<{CORR_THRESHOLD})"
            })
        
        accepted_feats = pruning_df[pruning_df["DURUM"] == "KABUL"]["Özellik Adı"].tolist()
        
        # --- 1.5 YÜKSEK KORELASYON FİLTRESİ (Özellikler Arası Redundancy) ---
        print(f"   - Özellikler Arası Redundancy Kontrolü Başlatılıyor (Eşik: 0.85)...")
        redundancy_threshold = 0.85
        to_drop_redundant = set()
        
        # Sadece kabul edilenlerin korelasyon matrisi
        if len(accepted_feats) > 1:
            accepted_corr = full_corr.loc[accepted_feats, accepted_feats].abs()
            
            for i in range(len(accepted_feats)):
                f1 = accepted_feats[i]
                if f1 in to_drop_redundant: continue
                
                for j in range(i + 1, len(accepted_feats)):
                    f2 = accepted_feats[j]
                    if f2 in to_drop_redundant: continue
                    
                    if accepted_corr.loc[f1, f2] >= redundancy_threshold:
                        # Hedefle korelasyonları karşılaştır
                        c1 = pruning_df.loc[pruning_df["Özellik Adı"] == f1, "Mutlak"].values[0]
                        c2 = pruning_df.loc[pruning_df["Özellik Adı"] == f2, "Mutlak"].values[0]
                        
                        if c1 >= c2:
                            to_drop_redundant.add(f2)
                            global_deleted_log.append({
                                "Sektör": sector, "Elenen Özellik": f2, 
                                "Değer": round(accepted_corr.loc[f1, f2], 4), 
                                "Neden": f"Yüksek Redundancy ({f1} ile >{redundancy_threshold})"
                            })
                        else:
                            to_drop_redundant.add(f1)
                            global_deleted_log.append({
                                "Sektör": sector, "Elenen Özellik": f1, 
                                "Değer": round(accepted_corr.loc[f1, f2], 4), 
                                "Neden": f"Yüksek Redundancy ({f2} ile >{redundancy_threshold})"
                            })
                            break # f1 elendiği için bu satırla işimiz bitti
        
        final_accepted_feats = [f for f in accepted_feats if f not in to_drop_redundant]

        
        # --- 3. SEKTÖREL EXCEL ---
        sector_file = os.path.join(OUT_DIR, f"{sector}_Pearson_Analizi.xlsx")
        with pd.ExcelWriter(sector_file, engine='xlsxwriter') as writer:
            total_count = len(target_corrs)
            accepted_count = len(final_accepted_feats)
            deleted_count = total_count - accepted_count
            
            pd.DataFrame({"Metrik": ["Toplam", "Silinen", "Kalan", "%"], 
                          "Değer": [total_count, deleted_count, accepted_count, f"%{accepted_count/total_count*100:.1f}"]}).to_excel(writer, sheet_name="Özet", index=False)
            
            # --- YENİ: HAM MATRİS ---
            full_corr.to_excel(writer, sheet_name="Ham_Matris")

            # --- GÜNCELLENMİŞ: TEMİZLENMİŞ MATRİS ---
            ordered_matrix_cols = [target_col] + final_accepted_feats
            styled_corr = full_corr.loc[ordered_matrix_cols, ordered_matrix_cols]
            styled_corr.to_excel(writer, sheet_name="Temizlenmiş_Matris")
            writer.sheets["Temizlenmiş_Matris"].conditional_format(1, 1, len(ordered_matrix_cols), len(ordered_matrix_cols), {'type': '2_color_scale', 'min_color': "#FADBD8", 'max_color': "#D4EFDF"})
            
            pruning_df.to_excel(writer, sheet_name="Detay_Pearson", index=False)

        # --- 4. GÖRSELLER ---
        # 4a. Çubuk Grafik (Mevcut)
        plt.figure(figsize=(14, 10))
        plot_feats = final_accepted_feats[:20]
        corrs_plot = target_corrs[plot_feats].sort_values()
        colors = ['#27AE60' if x > 0 else '#E74C3C' for x in corrs_plot]
        corrs_plot.plot(kind='barh', color=colors, edgecolor='black')
        plt.title(f"{sector}\nNet Dönem Karı ile En İlişkili Özellikler (Pearson)", fontsize=16, fontweight='bold')
        plt.tight_layout(); plt.savefig(os.path.join(IMG_DIR, f"1_Pearson_Cubuk_{sector}.png"), dpi=200); plt.close()

        # 4b. YENİ: Isı Haritası (Heatmap)
        if len(final_accepted_feats) > 0:
            map_cols = [target_col] + final_accepted_feats[:30]
            
            # --- DİNAMİK BOYUTLANDIRMA VE OKUNABİLİRLİK GÜNCELLEMESİ ---
            # Her satır için dikey alanı ve her sütun için yatay alanı optimize et
            fig_height = max(12, len(map_cols) * 0.75) 
            fig_width = 24
            
            plt.figure(figsize=(fig_width, fig_height))
            
            # Uzun isimleri kaydır (Daha dengeli wrap)
            wrapped_map_labels = wrap_labels(map_cols, width=30)
            
            sns.heatmap(full_corr.loc[map_cols, map_cols], 
                        annot=True, fmt=".2f", cmap='RdYlGn', center=0, square=True, 
                        cbar_kws={'shrink': .4}, 
                        linewidths=.5,      # Hücre sınırlarını belirginleştir
                        linecolor='#E0E0E0', 
                        annot_kws={"size": 8.5}, # Rakam font boyutu
                        xticklabels=wrapped_map_labels, 
                        yticklabels=wrapped_map_labels)
            
            plt.title(f"{sector}\nKorelasyon Isı Haritası (Kalan Özellikler)", fontsize=24, fontweight='bold', pad=30)
            plt.xticks(rotation=45, ha='right', fontsize=11)
            plt.yticks(rotation=0, fontsize=11)
            
            # Etiketlerin kesilmemesi için kenar boşluklarını manuel ayarla
            plt.subplots_adjust(left=0.28, bottom=0.18, right=0.98, top=0.94)
            
            plt.savefig(os.path.join(IMG_DIR, f"1_Pearson_Isi_Haritasi_{sector}.png"), dpi=180)
            plt.close()



        
        # --- 5. POOL'A KAYDET ---
        # Hedef değişkeni en sona taşı
        final_col_order = ids + final_accepted_feats + [target_col]
        df[final_col_order].to_excel(pool_writer, sheet_name=sector, index=False)
        
        global_summary.append({
            "Sektör": sector, 
            "Toplam": total_count, 
            "Silinen": deleted_count, 
            "Kalan": accepted_count
        })

    pool_writer.close()

    # --- 6. MERKEZİ ÖZET ---
    with pd.ExcelWriter(summary_report_path, engine='xlsxwriter') as summary_writer:
        workbook = summary_writer.book
        note_format = workbook.add_format({'bold': True, 'font_size': 10, 'bg_color': '#EBF5FB', 'border': 2, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#2E4053', 'border': 1, 'align': 'center'})

        ws_sum = workbook.add_worksheet("Sektörel Özet")
        ws_sum.set_column('A:D', 20)
        ws_sum.set_row(0, 60)
        
        note_text = (f"ANALİZ METODOLOJİSİ VE ELEME KRİTERLERİ (ADIM 2)\n\n"
                    f"1. HEDEF İLİŞKİSİ: Özelliklerin '{target_col}' ile olan mutlak korelasyonu {CORR_THRESHOLD:.2f} altında olanlar elenmiştir.\n"
                    f"2. REDUNDANCY (GEREKSİZLİK): Kendi aralarında {redundancy_threshold:.2f} üzerinde korelasyon gösteren çiftlerden, "
                    f"hedef değişkeni daha az açıklayan özellik elenerek bilgi tekrarı önlenmiştir.")
        
        ws_sum.merge_range('A1:D1', note_text, note_format)
        
        df_summary = pd.DataFrame(global_summary)
        ws_sum.write_row(1, 0, df_summary.columns, header_format)
        for r, row in enumerate(df_summary.values):
            ws_sum.write_row(2 + r, 0, row)
            
        pd.DataFrame(global_deleted_log).to_excel(summary_writer, sheet_name="Elenenler", index=False)

    print("\n" + "="*80)
    print("ADIM 2: PEARSON FİLTRELEME TAMAMLANDI")
    print("="*80)

if __name__ == "__main__":
    run_pearson_analysis()
