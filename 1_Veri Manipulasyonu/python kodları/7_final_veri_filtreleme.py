import pandas as pd
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

temp_data_path = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu.xlsx")
if os.path.exists(temp_data_path):
    INPUT_PATH = temp_data_path
else:
    # Fallback to generic name if suffixed not found (for old runs)
    INPUT_PATH = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", "Veri_Havuzu.xlsx")
    if not os.path.exists(INPUT_PATH):
        INPUT_PATH = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", "Veri_Havuzu_Birlesik.xlsx")

OUT_DIR = os.path.join(BASE_PATH, "raporlar", "7_Final_Veri")
os.makedirs(OUT_DIR, exist_ok=True)

import sys

import matplotlib.pyplot as plt
import seaborn as sns

def run_filtering():
    print("\n" + "="*60)
    print("   STEP 7: FINAL VERI FILTRELEME VE TEMIZLEME")
    print("="*60)
    
    IMG_OUT_DIR = os.path.join(BASE_PATH, "görseller", "7_Final_Filtreleme")
    os.makedirs(IMG_OUT_DIR, exist_ok=True)
    
    if not os.path.exists(INPUT_PATH):
        print(f"Hata: Giriş dosyası (Step 3 sonucu) bulunamadı: {INPUT_PATH}")
        return

    # Eşik değerini belirle (Argüman veya Giriş)
    if len(sys.argv) > 1:
        try:
            threshold = float(sys.argv[1])
        except:
            threshold = 70.0
    else:
        threshold = 70.0

    print(f"\nFiltreleme başlatılıyor (Eşik: %{threshold})...")
    
    xl = pd.ExcelFile(INPUT_PATH)
    out_file_name = f"Final_Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Final_Veri_Havuzu.xlsx"
    final_writer_path = os.path.join(OUT_DIR, out_file_name)
    
    filtering_stats = []

    with pd.ExcelWriter(final_writer_path, engine='openpyxl') as writer:
        for sector_name in xl.sheet_names:
            print(f"Sektör İşleniyor: {sector_name}")
            try:
                df = pd.read_excel(xl, sheet_name=sector_name)
            except Exception as e:
                print(f"  Sektör okuma hatası ({sector_name}): {e}")
                continue
                
            def normalize_name(name):
                # 1. Temel Temizlik (Büyük harf, boşluk, Türkçe karakter)
                n = str(name).upper().strip()
                n = n.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
                
                # 2. Sayısal Ekleri Temizle (Pandas .1, .2 veya kod sonundaki rakamlar)
                n = re.sub(r'[\.\s]\d+$', '', n) # "KAR .1" veya "KAR 1" -> "KAR"
                n = re.sub(r'\d+$', '', n)       # "KAR1" -> "KAR"
                
                # 3. Finansal Terim Standardizasyonu
                n = n.replace('KARI', 'KAR').replace('K R', 'KAR')
                
                # 4. Sadece Harf ve Rakam Bırak
                n = re.sub(r'[^A-Z0-9]', ' ', n)
                
                # 5. Kelime Sırasından Bağımsız Hale Getir (SIRALAMA)
                words = sorted([w for w in n.split() if w])
                n = " ".join(words)
                
                return n.strip()

            def is_id_col(col_name):
                # ID tespiti için daha basit normalizasyon (Özel karakterleri bozmadan)
                n = str(col_name).upper().strip()
                n = n.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
                ident_keywords = ['DONEM', 'FIRMA ADI', 'FIRMA', 'FRMA', 'YEAR', 'MONTH', 'YIL', 'AY']
                if n in ident_keywords: return True
                if n.startswith('DONEM ('): return True # Dönem (Yıl/Ay) gibi
                return False

            id_cols = [c for c in df.columns if is_id_col(c)]
            
            # --- YENİ: Sütun Tekilleştirme (Case-Insensitive Consolidation) ---
            features_only = [c for c in df.columns if c not in id_cols]
            norm_map = {}
            for col in features_only:
                norm = normalize_name(col)
                if norm not in norm_map: norm_map[norm] = []
                norm_map[norm].append(col)
            
            unified_data = {}
            unified_count = 0
            for norm_name, source_cols in norm_map.items():
                if len(source_cols) > 1:
                    # Mükerrerleri birleştir
                    combined = df[source_cols[0]]
                    for next_col in source_cols[1:]:
                        combined = combined.combine_first(df[next_col])
                    unified_data[norm_name] = combined
                    unified_count += 1
                else:
                    unified_data[norm_name] = df[source_cols[0]]
            
            # Unidentified ID cols'ları ve temizlenmiş özellikleri birleştir
            df_unified = pd.concat([df[id_cols], pd.DataFrame(unified_data)], axis=1)
            if unified_count > 0:
                print(f"  [!] {unified_count} mükerrer sütun grubu tekilleştirildi.")
            
            # Artık df_unified üzerinden devam et
            features = [c for c in df_unified.columns if c not in id_cols]
            initial_count = len(features)
            if initial_count == 0: continue
            
            fill_rates = df_unified[features].notna().mean() * 100
            
            # --- HİBRİT GÜVENLİK GÜNCELLEMESİ ---
            PROTECTED_KEYWORDS = ['KAR', 'ZARAR', 'HASILAT', 'VARLIK', 'OZKAYNAK', 'SERMAYE', 'BORC', 'YUKUMLULUK', 'CIRO']
            PROTECTED_THRESHOLD = 50.0 # Kritik veriler için tolerans sınırı
            
            def is_protected(col_name):
                n = str(col_name).upper()
                return any(k in n for k in PROTECTED_KEYWORDS)

            keep_features = []
            for col in features:
                fr = fill_rates[col]
                # Eğer kritik veriyse %50, değilse %70 eşiğine bak
                current_threshold = PROTECTED_THRESHOLD if is_protected(col) else threshold
                
                if fr >= current_threshold:
                    keep_features.append(col)
            
            final_df = df_unified[id_cols + keep_features]
            final_count = len(keep_features)
            
            sheet_name_clean = re.sub(r'[\\/*?:\[\]]', '', sector_name)[:31]
            final_df.to_excel(writer, sheet_name=sheet_name_clean, index=False)
            
            # Yeni: Kalan özelliklerin ortalama doluluk oranını hesapla
            final_avg_fill = fill_rates[keep_features].mean() if keep_features else 0
            
            filtering_stats.append({
                "Sektör": sector_name,
                "Özellik Sayısı": initial_count,
                "Ort. Doluluk (%)": round(fill_rates.mean(), 2),
                "Durum": "Önce"
            })
            filtering_stats.append({
                "Sektör": sector_name,
                "Özellik Sayısı": final_count,
                "Ort. Doluluk (%)": round(final_avg_fill, 2),
                "Durum": "Sonra"
            })

    # İstatistik Raporunu Kaydet (Wide format için tekrar hazırla)
    if filtering_stats:
        viz_df = pd.DataFrame(filtering_stats)
        
        # GÖRSELLEŞTİRME
        print("\nGrafikler oluşturuluyor...")
        sns.set_theme(style="whitegrid")
        
        # 1. GRAFİK: ÖZELLİK SAYISI (ADET)
        plt.figure(figsize=(14, 8))
        ax1 = sns.barplot(data=viz_df, x="Sektör", y="Özellik Sayısı", hue="Durum", palette="viridis")
        plt.title(f"Final Filtreleme: Özellik Sayısı Değişimi (Eşik: %{threshold})", fontsize=16, fontweight='bold', pad=20)
        plt.xticks(rotation=30, ha='right')
        plt.ylabel("Özellik Sayısı", fontsize=12)
        plt.xlabel("Sektörler", fontsize=12)
        
        # Y eksenini ve X eksenini esnet (Üstte ve yanlarda boşluk bırak)
        max_val_count = viz_df["Özellik Sayısı"].max()
        plt.ylim(0, max_val_count * 1.3)
        plt.margins(x=0.1) # Yanlarda boşluk bırak (En sağdaki barın kesilmesini önler)
        plt.legend(title="Durum", loc='upper right')
        
        for p in ax1.patches:
            if p.get_height() > 0:
                ax1.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()), ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=10, fontweight='bold')
        
        img_path_count = os.path.join(IMG_OUT_DIR, "Filtreleme_1_Ozellik_Sayisi.png")
        plt.tight_layout()
        plt.savefig(img_path_count, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Grafik 1 kaydedildi: {img_path_count}")

        # 2. GRAFİK: ORTALAMA DOLULUK ORANI (%)
        plt.figure(figsize=(14, 8))
        ax2 = sns.barplot(data=viz_df, x="Sektör", y="Ort. Doluluk (%)", hue="Durum", palette="magma")
        plt.title(f"Final Filtreleme: Ortalama Doluluk Oranı Değişimi (Eşik: %{threshold})", fontsize=16, fontweight='bold', pad=20)
        plt.xticks(rotation=30, ha='right')
        plt.ylabel("Doluluk Oranı (%)", fontsize=12)
        plt.xlabel("Sektörler", fontsize=12)
        
        # Y eksenini ve X eksenini esnet (%130'a kadar çekerek lejanta yer aç, yanları aç)
        plt.ylim(0, 130)
        plt.margins(x=0.1) # Yanlarda boşluk bırak (En sağdaki barın kesilmesini önler)
        plt.legend(title="Durum", loc='upper right')
        
        for p in ax2.patches:
            if p.get_height() > 0:
                ax2.annotate(f'%{p.get_height():.1f}', (p.get_x() + p.get_width() / 2., p.get_height()), ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=10, fontweight='bold')
        
        img_path_fill = os.path.join(IMG_OUT_DIR, f"Filtreleme_2_Doluluk_Orani_{CURRENCY}.png" if CURRENCY else "Filtreleme_2_Doluluk_Orani.png")
        plt.tight_layout()
        plt.savefig(img_path_fill, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Grafik 2 kaydedildi: {img_path_fill}")

        # Excel Raporu (Geniş Format)
        pivot_count = viz_df.pivot(index="Sektör", columns="Durum", values="Özellik Sayısı")
        pivot_fill = viz_df.pivot(index="Sektör", columns="Durum", values="Ort. Doluluk (%)")
        
        report_df = pivot_count.merge(pivot_fill, on="Sektör", suffixes=(' (Adet)', ' (Doluluk %)'))
        report_df = report_df.reset_index()
        
        report_df['Azalma (%)'] = round((1 - report_df['Sonra (Adet)'] / report_df['Önce (Adet)']) * 100, 2)
        
        # Sütunları sırala
        report_df = report_df[['Sektör', 'Önce (Adet)', 'Sonra (Adet)', 'Azalma (%)', 'Önce (Doluluk %)', 'Sonra (Doluluk %)']]
        
        report_excel_name = f"7_Filtreleme_Istatistikleri_{CURRENCY}.xlsx" if CURRENCY else "7_Filtreleme_Istatistikleri.xlsx"
        excel_path = os.path.join(OUT_DIR, report_excel_name)
        report_df.to_excel(excel_path, index=False)
        print(f"Istatistik raporu kaydedildi: {excel_path}")

    print("\n" + "-"*60)
    print(f"ISLEM TAMAMLANDI")
    print(f"Final Veri Havuzu: {final_writer_path}")
    print("-"*60)

if __name__ == "__main__":
    run_filtering()
