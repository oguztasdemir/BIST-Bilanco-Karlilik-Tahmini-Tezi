import pandas as pd
import numpy as np
import os
import re
from openpyxl.styles import PatternFill
grey_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
blue_fill = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")

# --- YOLLAR ---
BASE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break

# Eğer Adım 12 (Wrapper) üzerinden çalışıyorsa 'Veri_Havuzu.xlsx' ismini kullanır, yoksa varsayılan USD
temp_data_path = os.path.join(BASE_PATH, "0_Datasetler", "Veri_Havuzu.xlsx")
if os.path.exists(temp_data_path):
    DATA_PATH = temp_data_path
else:
    data_file_name = f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu_USD.xlsx"
    DATA_PATH = os.path.join(BASE_PATH, "0_Datasetler", data_file_name)

if not CURRENCY:
    if "USD" in DATA_PATH: CURRENCY = "USD"
    elif "EUR" in DATA_PATH: CURRENCY = "EUR"
    elif "TRY" in DATA_PATH: CURRENCY = "TRY"

MAPPING_PATH = os.path.join(BASE_PATH, "raporlar", "2_Features Birlestirme", "Finansal_Rapor.xlsx")

# Step 3 Çıktıları için Yeni Klasör
STEP3_OUT_DIR = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme")
os.makedirs(STEP3_OUT_DIR, exist_ok=True)

out_data_name = "Veri_Havuzu.xlsx"
out_report_name = "3_Birlestirme_Performans_Raporu.xlsx"
if CURRENCY:
    out_data_name = f"Veri_Havuzu_{CURRENCY}.xlsx"
    out_report_name = f"3_Birlestirme_Performans_Raporu_{CURRENCY}.xlsx"

OUTPUT_DATA_PATH = os.path.join(STEP3_OUT_DIR, out_data_name)
REPORT_PATH = os.path.join(STEP3_OUT_DIR, out_report_name)

def clean_col_name(name):
    if pd.isna(name): return ""
    return str(name).strip()

def is_id_col(col_name):
    n = str(col_name).upper()
    keywords = ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY']
    return any(k in n for k in keywords)

def resolve_collision_single_row(row, sources):
    active = row[sources].dropna()
    if len(active) <= 1: return active.iloc[0] if len(active) == 1 else None, False
    
    unique_vals = active.unique()
    if len(unique_vals) == 1:
        return unique_vals[0], False
    
    # Farklı değerler - Küçük Harf Tercihi (User preference)
    # Eğer sadece bir tane tamamen büyük harf OLMAYAN (küçük harf içeren) kolon varsa onu seç
    non_caps_sources = [c for c in active.index if not str(c).isupper()]
    if len(non_caps_sources) == 1:
        return active[non_caps_sources[0]], False
    
    unresolved_str = " | ".join(active.astype(str))
    return unresolved_str, True

def unify_case_duplicates(df, sources):
    """
    Kasa duyarsız olarak aynı isme sahip olan ve içeriği tamamen aynı olan 
    kolonlardan sadece küçük harf olanı tutarak kolon listesini sadeleştirir.
    """
    if len(sources) <= 1: return sources
    
    # Grupla (case-insensitive)
    groups = {}
    for s in sources:
        key = s.lower()
        if key not in groups:
            groups[key] = []
        groups[key].append(s)
        
    final_sources = []
    for key, cols in groups.items():
        if len(cols) == 1:
            final_sources.append(cols[0])
            continue
            
        # Birden fazla var (örn: 'dönem net', 'DÖNEM NET')
        # Hepsi gerçekten aynı veriyi mi içeriyor?
        first_col = cols[0]
        all_identical = True
        for other in cols[1:]:
            if not df[first_col].equals(df[other]):
                all_identical = False
                break
        
        if all_identical:
            # İçerik aynıysa: En az büyük harf içeren (veya ilk isupper() False olanı) seç
            # Tamamı küçük harf olan bir versiyon varsa onu al
            best_choice = cols[0]
            for c in cols:
                if not str(c).isupper():
                    best_choice = c
                    break
            final_sources.append(best_choice)
        else:
            # İçerikler farklıysa: Hepsini tut ki collision_resolver (satır bazlı) karar versin
            final_sources.extend(cols)
            
    return final_sources

def execute_merging():
    print("--- Veri Birleştirme (Step 3) - Vektörize Başlatıldı ---")
    
    if not os.path.exists(MAPPING_PATH):
        print(f"Hata: Mapping dosyası bulunamadı: {MAPPING_PATH}")
        return

    mapping_df = pd.read_excel(MAPPING_PATH)
    ana_sutun_col = [col for col in mapping_df.columns if 'ANA' in str(col).upper()][0]
    kalemler_col = [col for col in mapping_df.columns if 'B' in str(col).upper() and 'KAL' in str(col).upper()][0]

    xl = pd.ExcelFile(DATA_PATH)
    grey_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    
    final_sector_datasets = {}
    performance_reports = {}

    for sector_name in xl.sheet_names:
        print(f"\nSektör İşleniyor: {sector_name}")
        df = pd.read_excel(xl, sheet_name=sector_name)
        id_cols = [c for c in df.columns if any(x in str(c).upper() for x in ['FRMA', 'FIRMA', 'DNEM', 'DÖNEM', 'YEAR', 'MONTH'])]
        
        merged_df = df[id_cols].copy()
        new_columns_data = {}
        sector_stats = []
        conflict_coords = []

        for _, m_row in mapping_df.iterrows():
            target_name = clean_col_name(m_row[ana_sutun_col])
            raw_sources = str(m_row[kalemler_col])
            source_candidates = [c.strip() for c in raw_sources.split(",") if c.strip()]
            
            def find_robust_match(candidate, columns):
                # Karakterleri temizle ve normalize et (Basit yaklaşım)
                def clean(text):
                    return str(text).upper().replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U').replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C').strip()
                
                c_clean = clean(candidate)
                for col in columns:
                    if clean(col) == c_clean:
                        return col
                return None

            existing_sources = []
            for cand in source_candidates:
                match = find_robust_match(cand, df.columns)
                if match and match not in existing_sources:
                    existing_sources.append(match)

            # --- YENİ: Kasa Duyarsız Özdeş Kolon Sadeleştirme ---
            # Eğer aynı ismin (lower/upper) içeriği de aynıysa, sadece küçüğü tut kolon sayısı azalsın.
            existing_sources = unify_case_duplicates(df, existing_sources)
            
            if not existing_sources: continue
            
            subset = df[existing_sources]
            ham_fill_mask = subset.notna().any(axis=1)
            ham_fill_count = ham_fill_mask.sum()
            
            # --- VEKTÖRİZE BAŞLANGIÇ ---
            # Varsayılan olarak ilk bulduğunu al (Hızlı)
            merged_values = subset.bfill(axis=1).iloc[:, 0] if len(existing_sources) > 1 else subset.iloc[:, 0]
            is_conflict_final = pd.Series([False] * len(df))
            
            # YENİ KURAL: Eğer ham doluluk oranı %50'den az ise çakışmaları önemseme, ilkini al geç.
            # %50 ve üzeri ise akademik titizlikle çakışmaları incele.
            ham_fill_rate = (ham_fill_count / len(df) * 100) if len(df) > 0 else 0
            
            if ham_fill_rate >= 50:
                # Sadece çakışma olan satılarda detaylı kontrol yap
                collision_mask = subset.notna().sum(axis=1) > 1
                if collision_mask.any():
                    # Çakışmalar içinde değerleri farklı olanlar asıl sorundur
                    # (Aynıysa zaten merged_values içindeki değer doğrudur)
                    def check_diff(r):
                        v = r.dropna().unique()
                        return len(v) > 1
                    
                    diff_mask = subset[collision_mask].apply(check_diff, axis=1)
                    harmful_indices = diff_mask[diff_mask].index
                    
                    if not harmful_indices.empty:
                        # Gelecekteki tip uyarılarını önlemek için object'e çevir (çünkü string birleştirme gelebilir)
                        merged_values = merged_values.astype(object)
                        
                        # Sadece zararlı çakışmalar için resolver çalıştır
                        sub_results = df.loc[harmful_indices].apply(lambda r: resolve_collision_single_row(r, existing_sources), axis=1)
                        merged_values.loc[harmful_indices] = [res[0] for res in sub_results]
                        is_conflict_final.loc[harmful_indices] = [res[1] for res in sub_results]
            
            new_columns_data[target_name] = merged_values
            
            # Koordinatları topla
            conf_indices = is_conflict_final[is_conflict_final].index
            for idx in conf_indices:
                conflict_coords.append((idx, target_name))
                
            final_fill_count = merged_values.notna().sum()
            unresolved_count = is_conflict_final.sum()
            total_rows = len(df)
            
            sector_stats.append({
                "Ana Sütun": target_name,
                "Ham Doluluk (Satır)": ham_fill_count,
                "Final Doluluk (Satır)": final_fill_count,
                "Final Doluluk Oranı (%)": round((final_fill_count / total_rows * 100), 2) if total_rows > 0 else 0,
                "Çözülemeyen Çelişki (Gri)": unresolved_count,
                "Başarı Oranı (%)": round(( (final_fill_count - unresolved_count) / ham_fill_count * 100), 2) if ham_fill_count > 0 else 100
            })
        
        if new_columns_data:
            merged_df = pd.concat([merged_df, pd.DataFrame(new_columns_data)], axis=1)
            
        final_sector_datasets[sector_name] = (merged_df, conflict_coords)
        performance_reports[sector_name] = pd.DataFrame(sector_stats)

    # 3. Final Veri Kümesini Kaydet
    print(f"\nFinal veri kümesi kaydediliyor (Bu işlem büyük dosyalarda zaman alabilir): {OUTPUT_DATA_PATH}")
    with pd.ExcelWriter(OUTPUT_DATA_PATH, engine='openpyxl') as writer:
        for sector, (m_df, coords) in final_sector_datasets.items():
            sheet_name = re.sub(r'[\\/*?:\[\]]', '', sector)[:31]
            print(f"  > {sheet_name} sayfası yazılıyor...")
            m_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            if coords:
                worksheet = writer.sheets[sheet_name]
                print(f"  > {sheet_name} için {len(coords)} çakışma hücresi griye boyanıyor...")
                
                # Sütun indekslerini önceden hesapla (Hız optimizasyonu)
                col_to_idx = {col: i + 1 for i, col in enumerate(m_df.columns)}
                
                for i, (r_idx, col_name) in enumerate(coords):
                    c_idx = col_to_idx[col_name]
                    worksheet.cell(row=r_idx + 2, column=c_idx).fill = grey_fill
                    
                    # Her 5000 hücrede bir ilerleme göster
                    if (i + 1) % 5000 == 0:
                        print(f"    - Boyama ilerlemesi: %{round((i+1)/len(coords)*100, 1)}")

            # --- YENİ: MAVİ BOYAMA (BİRLEŞTİRİLEN SÜTUNLAR) ---
            print(f"  > {sheet_name} için birleştirilen sütunlar maviye boyanıyor...")
            worksheet = writer.sheets[sheet_name]
            headers = [c.value for c in worksheet[1]]
            for c_idx, header in enumerate(headers, 1):
                if not is_id_col(header):
                    for r_idx in range(2, worksheet.max_row + 1):
                        cell = worksheet.cell(row=r_idx, column=c_idx)
                        # Eğer hücre zaten renkli değilse (GRİ değilse) MAVİ yap
                        if cell.fill.start_color.index in ["00000000", "FFFFFFFF"]:
                             if cell.value is not None:
                                 cell.fill = blue_fill

    # 4. Performans Raporunu Kaydet
    print(f"\nPerformans raporu kaydediliyor: {REPORT_PATH}")
    with pd.ExcelWriter(REPORT_PATH, engine='openpyxl') as writer:
        for sector, stat_df in performance_reports.items():
            # Sıralama: Önce Çözülemeyen Çelişki (Gri), sonra Final Doluluk Oranı (%) - Her ikisi de azalan
            if not stat_df.empty:
                stat_df = stat_df.sort_values(by=["Çözülemeyen Çelişki (Gri)", "Final Doluluk Oranı (%)"], ascending=False)
                
            sheet_name = re.sub(r'[\\/*?:\[\]]', '', sector)[:31]
            stat_df.to_excel(writer, sheet_name=sheet_name, index=False)

    # --- GÖRSELLEŞTİRME (YENİ EKLEME) ---
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        IMG_DIR = os.path.join(BASE_PATH, "görseller", "3_Birlesme_Analizi")
        os.makedirs(IMG_DIR, exist_ok=True)
        
        plot_data = []
        for s, report in performance_reports.items():
            if not report.empty:
                total_conflict = report["Çözülemeyen Çelişki (Gri)"].sum()
                avg_fill = report["Final Doluluk Oranı (%)"].mean()
                plot_data.append({"Sektör": s, "Toplam Çakışma": total_conflict, "Ort. Doluluk (%)": avg_fill})
        
        p_df = pd.DataFrame(plot_data)
        
        # Grafik 1: Sektörel Çakışma Analizi
        plt.figure(figsize=(12, 6))
        plt.savefig(os.path.join(IMG_DIR, f"3_1_Sektorel_Cakisim_{CURRENCY}.png" if CURRENCY else "3_1_Sektorel_Cakisim.png"), dpi=300)
        plt.close()
        
        # Grafik 2: Birleşme Sonrası Doluluk Verimliliği
        plt.figure(figsize=(12, 6))
        sns.lineplot(data=p_df, x="Sektör", y="Ort. Doluluk (%)", marker='o', color='red', linewidth=2)
        plt.title("Birleşme Sonrası Sektörel Ortalama Doluluk Oranları", fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(IMG_DIR, f"3_2_Doluluk_Verimliligi_{CURRENCY}.png" if CURRENCY else "3_2_Doluluk_Verimliligi.png"), dpi=300)
        plt.close()
        
        print(f"\n[+] Analitik görseller oluşturuldu: {IMG_DIR}")
    except Exception as e:
        print(f"\n[!] Görselleştirme atlandı: {e}")

    print("\n--- Step 3 Tamamlandı ---")

if __name__ == "__main__":
    execute_merging()
