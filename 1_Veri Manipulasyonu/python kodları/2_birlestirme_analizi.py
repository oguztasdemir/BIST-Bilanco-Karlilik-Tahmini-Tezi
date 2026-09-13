import pandas as pd
import os
import re

# --- YOLLAR ---
BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection\1_Veri Manipulasyonu"
DATA_PATH = os.path.join(BASE_PATH, "0_Datasetler", "Veri_Havuzu_USD.xlsx")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break
if not CURRENCY:
    if "USD" in DATA_PATH: CURRENCY = "USD"
    elif "EUR" in DATA_PATH: CURRENCY = "EUR"
    elif "TRY" in DATA_PATH: CURRENCY = "TRY"

MAPPING_PATH = os.path.join(BASE_PATH, "raporlar", "2_Features Birlestirme", "Finansal_Rapor.xlsx")

output_report_name = "Birlestirme_Analiz_Raporu.xlsx"
detail_report_name = "Cakisma_Detay_Listesi.xlsx"
if CURRENCY:
    output_report_name = f"Birlestirme_Analiz_Raporu_{CURRENCY}.xlsx"
    detail_report_name = f"Cakisma_Detay_Listesi_{CURRENCY}.xlsx"

OUTPUT_PATH = os.path.join(BASE_PATH, "raporlar", "2_Features Birlestirme", output_report_name)
DETAIL_OUTPUT_PATH = os.path.join(BASE_PATH, "raporlar", "2_Features Birlestirme", detail_report_name)

def clean_col_name(name):
    """Sütun adlarını normalize eder."""
    if pd.isna(name): return ""
    return str(name).strip()

def unify_case_duplicates(df, sources):
    """
    Kasa duyarsız olarak aynı isme sahip olan ve içeriği tamamen aynı olan 
    kolonlardan sadece küçük harf olanı tutarak kolon listesini sadeleştirir.
    """
    if len(sources) <= 1: return sources
    
    unique_sources = []
    seen_lower = {} # lower_name -> list of original names
    
    for s in sources:
        low = s.lower()
        if low not in seen_lower:
            seen_lower[low] = []
        seen_lower[low].append(s)
    
    for low, cols in seen_lower.items():
        if len(cols) == 1:
            unique_sources.append(cols[0])
        else:
            # Örn: ['dönem karı', 'DÖNEM KARI']
            # İçerikleri kontrol et
            first_col = cols[0]
            redundant = True
            for other in cols[1:]:
                if not df[first_col].equals(df[other]):
                    redundant = False
                    break
            
            if redundant:
                # Hepsi aynıysa en az büyük harf içeren (isupper() olmayan ilk) olanı seç
                best_choice = cols[0]
                for c in cols:
                    if not str(c).isupper():
                        best_choice = c
                        break
                unique_sources.append(best_choice)
            else:
                # İçerikler farklıysa hepsini tut (Analize dahil et)
                unique_sources.extend(cols)
                
    return unique_sources

def analyze_merging():
    print("--- Birleştirme Analizi Başlatıldı ---")
    
    # 1. Mapping Yükle
    if not os.path.exists(MAPPING_PATH):
        print(f"Hata: Mapping dosyası bulunamadı: {MAPPING_PATH}")
        return
    
    mapping_df = pd.read_excel(MAPPING_PATH)
    # Sütun adlarını bul (Encoding kaynaklı sorunları önlemek için)
    ana_sutun_col = [col for col in mapping_df.columns if 'ANA' in str(col).upper() and 'S' in str(col).upper()][0]
    kalemler_col = [col for col in mapping_df.columns if 'B' in str(col).upper() and 'RLE' in str(col).upper() and 'KAL' in str(col).upper()][0]
    
    print(f"Mapping yüklendi. {len(mapping_df)} kural bulundu.")

    # 2. Veri Havuzu Dosyasını Oku
    xl = pd.ExcelFile(DATA_PATH)
    all_sector_results = {}
    all_sector_details = {}

    for sector_name in xl.sheet_names:
        print(f"\nSektör İnceleniyor: {sector_name}")
        df = pd.read_excel(xl, sheet_name=sector_name)
        
        sector_report_rows = []
        sector_detail_list = [] # Çakışan satırların detaylı verileri
        total_rows = len(df)
        
        if total_rows == 0:
            print(f"Uyarı: {sector_name} sektörü boş.")
            continue

        # Kimlik kolonlarını bul (Firma, Dönem vb.)
        id_cols = [c for c in df.columns if any(x in str(c).upper() for x in ['FRMA', 'FIRMA', 'DNEM', 'DÖNEM', 'YEAR', 'MONTH'])]

        for _, row in mapping_df.iterrows():
            target_name = clean_col_name(row[ana_sutun_col])
            raw_kalemler = str(row[kalemler_col])
            
            source_candidates = [c.strip() for c in raw_kalemler.split(",") if c.strip()]
            existing_sources = [c for c in source_candidates if c in df.columns]
            
            # --- YENİ: Kasa Duyarsız Özdeş Kolon Sadeleştirme ---
            # Eğer aynı ismin (lower/upper) içeriği de aynıysa, sadece küçüğü tut.
            existing_sources = unify_case_duplicates(df, existing_sources)
            
            if not existing_sources:
                continue 

            subset = df[existing_sources]
            any_filled_mask = subset.notna().any(axis=1)
            initial_fill_count = any_filled_mask.sum()
            initial_fill_rate = (initial_fill_count / total_rows) * 100
            
            fill_count_per_row = subset.notna().sum(axis=1)
            collision_mask = fill_count_per_row > 1
            collision_count = collision_mask.sum()
            
            # --- Çakışma Detaylarını Topla (Sıkıştırılmış Yatay Format) ---
            if collision_count > 0:
                # 1. Çakışan satırları çek
                collisions = df[collision_mask].copy()
                
                # 2. Kimlik kolonlarını ve çakışan değerleri ayıkla
                for idx, coll_row in collisions.iterrows():
                    detail_entry = {}
                    
                    # Kimlik Bilgileri (A ve B Kolonları için)
                    # Firma ismi ve Dönem'i en başa koyalım
                    firma = next((coll_row[c] for c in id_cols if 'FIRMA' in str(c).upper() or 'FRMA' in str(c).upper()), "-")
                    donem = next((coll_row[c] for c in id_cols if 'DNEM' in str(c).upper() or 'DÖNEM' in str(c).upper() or 'YEAR' in str(c).upper()), "-")
                    
                    detail_entry["Firma Adı"] = firma
                    detail_entry["Dönem"] = donem
                    detail_entry["Ana Sütun (Hedef)"] = target_name
                    
                    # Sadece dolu olan bileşenleri ayıkla ("Kolon: Değer" formatında)
                    active_vals = coll_row[existing_sources].dropna()
                    for i, (col_name, val) in enumerate(active_vals.items(), 1):
                        detail_entry[f"Değer {i}"] = f"{col_name}: {val}"
                    
                    sector_detail_list.append(detail_entry)

            # --- YENİ: Çakışma Benzerlik Analizi (Değer Aynılığı) ---
            identical_collision_count = 0
            if collision_count > 0:
                collision_rows = subset[collision_mask]
                identical_mask = collision_rows.apply(lambda r: r.dropna().nunique() == 1, axis=1)
                identical_collision_count = identical_mask.sum()
            
            harmful_collision_count = collision_count - identical_collision_count

            # --- YENİ: Büyük Harf Filtreli Analiz (CAPS Filter & Fill Rate Comparison) ---
            caps_filtered_sources = [c for c in existing_sources if not c.isupper()]
            if not caps_filtered_sources:
                caps_filtered_sources = existing_sources
            
            filtered_subset = df[caps_filtered_sources]
            filtered_fill_count = (filtered_subset.notna().sum(axis=1) > 0).sum()
            filtered_fill_rate = (filtered_fill_count / total_rows) * 100
            filtered_collision_count = (filtered_subset.notna().sum(axis=1) > 1).sum()
            
            elenenler = [c for c in existing_sources if c not in caps_filtered_sources]
            caps_status = "✅ ÇAKIŞMA SIFIRLANDI" if filtered_collision_count == 0 else "⚠️ ÇAKIŞMA DEVAM EDİYOR"
            if not elenenler: caps_status = "Büyük Harf Yok"

            sector_report_rows.append({
                "Ana Sütun (Yeni)": target_name,
                "Sektörde Bulunan Bileşenler": ", ".join(existing_sources),
                "Bileşen Sayısı": len(existing_sources),
                "Sektör Toplam Satır": total_rows,
                "Dolu Satır Sayısı": initial_fill_count,
                "Doluluk Oranı (%)": round(initial_fill_rate, 2),
                "Çakışma Sayısı (Collision)": collision_count,
                "Durum": "⚠️ ÇAKIŞMA VAR" if collision_count > 0 else "✅ TEMİZ",
                " ": "", # BOŞ AYIRICI
                "Aynı Değerli Çakışma": identical_collision_count,
                "Gerçek (Farklı Veri) Çakışma": harmful_collision_count,
                "Benzerlik Durumu": "💎 TÜM ÇAKIŞMALAR AYNI" if collision_count > 0 and harmful_collision_count == 0 else "-",
                "  ": "", # SİYAH AYIRICI KOLON
                "Büyük Harf Filtre Durumu": caps_status,
                "Elenen (Caps) Kolonlar": ", ".join(elenenler) if elenenler else "-",
                "Filtre Sonrası Çakışma": filtered_collision_count,
                "   ": "", # ÜÇÜNCÜ AYIRICI (Fill Rate Comparison)
                "İlk Doluluk %": round(initial_fill_rate, 2),
                "Son Doluluk %": round(filtered_fill_rate, 2),
                "Doluluk Değişimi %": round(filtered_fill_rate - initial_fill_rate, 4)
            })
        
        # Raporları sakla
        all_sector_results[sector_name] = pd.DataFrame(sector_report_rows)
        if sector_detail_list:
            detail_df = pd.DataFrame(sector_detail_list)
            # Kolon sırasını düzenle: Önce Kimlikler ve Hedef, sonra Değerler
            cols = ["Firma Adı", "Dönem", "Ana Sütun (Hedef)"]
            value_cols = [c for c in detail_df.columns if c.startswith("Değer ")]
            # Değer kolonlarını sayısal olarak sıralayalım (Değer 1, Değer 2, Değer 10...)
            value_cols.sort(key=lambda x: int(x.split()[1]))
            detail_df = detail_df[cols + value_cols]
            all_sector_details[sector_name] = detail_df

    # 3. Sonuçları Kaydet
    print(f"\nSonuçlar kaydediliyor: {OUTPUT_PATH}")
    from openpyxl.styles import PatternFill
    black_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")

    # Özet Raporu Kaydet
    with pd.ExcelWriter(OUTPUT_PATH, engine='openpyxl') as writer:
        for sector, report_df in all_sector_results.items():
            if report_df.empty: continue
            # Sıralama: Çakışma Sayısı (Azalan)
            sort_cols = ["Çakışma Sayısı (Collision)", "Doluluk Değişimi %", "İlk Doluluk %"]
            report_df = report_df.sort_values(by=sort_cols, ascending=[False, True, False])
            
            sheet_name = re.sub(r'[\\/*?:\[\]]', '', sector)[:31]
            report_df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            
            sep_idx_white1 = report_df.columns.get_loc(" ") if " " in report_df.columns else -1
            sep_idx_black = report_df.columns.get_loc("  ") if "  " in report_df.columns else -1
            sep_idx_white2 = report_df.columns.get_loc("   ") if "   " in report_df.columns else -1

            for i, col in enumerate(report_df.columns):
                column_letter = chr(65 + i) if i < 26 else f"{chr(64 + i // 26)}{chr(65 + i % 26)}"
                if i in [sep_idx_white1, sep_idx_white2]:
                    worksheet.column_dimensions[column_letter].width = 3
                elif i == sep_idx_black:
                    worksheet.column_dimensions[column_letter].width = 3
                    for row in range(1, len(report_df) + 2):
                        worksheet[f"{column_letter}{row}"].fill = black_fill
                else:
                    column_len = max(report_df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.column_dimensions[column_letter].width = min(column_len, 50)

    # Detay Raporunu Kaydet
    if all_sector_details:
        print(f"Detay raporu kaydediliyor: {DETAIL_OUTPUT_PATH}")
        with pd.ExcelWriter(DETAIL_OUTPUT_PATH, engine='openpyxl') as writer:
            for sector, detail_df in all_sector_details.items():
                sheet_name = re.sub(r'[\\/*?:\[\]]', '', sector)[:31]
                detail_df.to_excel(writer, sheet_name=sheet_name, index=False)
                # Genişlik ayarı
                worksheet = writer.sheets[sheet_name]
                for i, col in enumerate(detail_df.columns):
                    column_letter = chr(65 + i) if i < 26 else f"{chr(64 + i // 26)}{chr(65 + i % 26)}"
                    worksheet.column_dimensions[column_letter].width = 25

    print("\n--- Analiz Tamamlandı ---")

    print(f"Rapor şurada oluşturuldu: {OUTPUT_PATH}")

if __name__ == "__main__":
    analyze_merging()
