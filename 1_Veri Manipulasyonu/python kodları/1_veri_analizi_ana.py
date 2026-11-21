import pandas as pd
import matplotlib
matplotlib.use('Agg') # Başsız ortamlar için pencere açılmasını engeller
import matplotlib.pyplot as plt
import os
import numpy as np

# --- AYARLAR ---
base_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")
data_path = os.path.join(base_path, "0_Datasetler", "Veri_Havuzu_USD.xlsx")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break
if not CURRENCY:
    if "USD" in data_path: CURRENCY = "USD"
    elif "EUR" in data_path: CURRENCY = "EUR"
    elif "TRY" in data_path: CURRENCY = "TRY"


# Çıktı klasörleri (Alt klasör yapısı)
img_base_dir = os.path.join(base_path, "görseller", "1")
IMG_DIR_SECTOR = os.path.join(img_base_dir, "1_Sektorel_Dagilim")
IMG_DIR_MISSING = os.path.join(img_base_dir, "2_Eksik_Donem_Analizi")
IMG_DIR_CONSISTENCY = os.path.join(img_base_dir, "3_Tutarlilik_Raporlari")

report_output_dir = os.path.join(base_path, "raporlar", "1_Donem_Analizi")
report_file_name = "Donem_Filtreleme_Analizi.xlsx"
if CURRENCY:
    report_file_name = f"Donem_Filtreleme_Analizi_{CURRENCY}.xlsx"
report_file_path = os.path.join(report_output_dir, report_file_name)

def check_feature_consistency(file_paths):
    """
    3 farklı kurdaki (USD, EUR, TRY) feature isimlerini karşılaştırır.
    """
    print("\n--- ÖZELLİK TUTARLILIK KONTROLÜ ---")
    feature_sets = {}
    for path in file_paths:
        file_name = os.path.basename(path)
        print(f"Başlıklar Kontrol Ediliyor: {file_name}")
        xl = pd.ExcelFile(path)
        all_cols = set()
        for sheet_name in xl.sheet_names:
            # Sadece kolon isimlerini oku
            df = pd.read_excel(xl, sheet_name=sheet_name, nrows=0)
            all_cols.update(df.columns.tolist())
        
        # Gereksiz kolonları çıkar (Dönem ve Firma Adı dışındakiler feature kabul edilir)
        # Bazı dosyalarda Dönem ismi farklı olabilir, esnek kontrol yapalım
        ignore_cols = {'Dönem', 'Firma Adı', 'Year', 'Month', 'Dnem', 'Firma Ad'}
        features = {col for col in all_cols if col not in ignore_cols}
        feature_sets[file_name] = features

    # Karşılaştırma
    keys = list(feature_sets.keys())
    is_all_same = True
    if len(keys) > 1:
        first_set = feature_sets[keys[0]]
        for i in range(1, len(keys)):
            if feature_sets[keys[i]] != first_set:
                is_all_same = False
                break
    
    return is_all_same, feature_sets

def create_consistency_visual(is_all_same, feature_sets, output_dir):
    """
    Akademik formatta özellik tutarlılığı analizi görseli oluşturur.
    Tez veya makale kullanımı için optimize edilmiştir.
    """
    # Akademik stil ayarları
    plt.rcParams.update({'font.size': 10, 'font.family': 'sans-serif'})
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.5), gridspec_kw={'height_ratios': [1.5, 1]})
    
    # 1. Grafik Kısmı: Yatay Bar Chart
    labels = list(feature_sets.keys())
    counts = [len(s) for s in feature_sets.values()]
    
    # Kesişim kümesini hesapla (tüm setlerde ortak olanlar)
    try:
        common_features = set.intersection(*feature_sets.values())
        intersect_count = len(common_features)
    except:
        intersect_count = 0
    
    # Verileri hazırla
    plot_labels = labels + ["Kesişim (Ortak Küme)"]
    plot_counts = counts + [intersect_count]
    
    # Renk paleti: Ciddi ve akademik (Koyu maviler ve vurgu rengi)
    base_color = '#2c3e50'
    match_color = '#16a085' if is_all_same else '#c0392b'
    colors = [base_color] * len(labels) + [match_color]
    
    bars = ax1.barh(plot_labels, plot_counts, color=colors, alpha=0.85, height=0.6, edgecolor='black', linewidth=0.8)
    ax1.set_xlabel('Belirlenen Özellik Sayısı (Count of Features)', fontweight='bold', fontsize=11)
    ax1.set_title('Şekil 1: Çoklu Para Birimi Veri Havuzları Özellik Tutarlılık Analizi', fontsize=14, pad=20, fontweight='bold')
    ax1.grid(axis='x', linestyle='--', alpha=0.4, zorder=0)
    
    # Bar değerleri
    for bar in bars:
        width = bar.get_width()
        ax1.text(width + 3, bar.get_y() + bar.get_height()/2, f"{int(width)}", 
                 va='center', fontweight='bold', color=base_color, fontsize=11)

    ax1.set_xlim(0, max(plot_counts) * 1.15)
    ax1.invert_yaxis() 
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # 2. Tablo Kısmı (Veri Özeti)
    ax2.axis('off')
    table_data = []
    
    # Statü metni
    status = "TAM UYUM (%100)" if is_all_same else "EKSİK/FARKLILIK VAR"
    
    for fname, fset in feature_sets.items():
        table_data.append([fname, len(fset), "Eşleşti (Matched)"])
    
    table_data.append(["TOPLAM ÖZELLİK (INTERSECT)", intersect_count, status])
    
    # Akademik tablo stili (temiz ve okunaklı)
    table = ax2.table(cellText=table_data, 
                      colLabels=["Veri Kaynağı (Dataset Category)", "Özellik Sayısı", "Bütünlük Kontrolü"],
                      loc='center', cellLoc='center', colColours=['#f2f2f2']*3)
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.2) 
    
    # Başlık hücrelerini belirginleştir
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='black')
            cell.set_facecolor('#dcdde1')
        if row == len(table_data): # Son satır (Kesişim)
            cell.set_text_props(weight='bold')
            if col == 2: cell.set_text_props(color=match_color)

    plt.tight_layout()
    
    output_name = "0_feature_tutarlilik_raporu.png"
    if CURRENCY:
        output_name = f"0_feature_tutarlilik_raporu_{CURRENCY}.png"
    output_path = os.path.join(output_dir, output_name)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Akademik tutarlılık görseli oluşturuldu: {os.path.basename(output_path)}")



def parse_period(p):
    try:
        year, month = map(int, str(p).split("/"))
        return year, month
    except:
        return 0, 0

def create_sector_chart(df, sector_name, output_dir, total_firms_with_dupes=None):
    """Sektörel veya genel bar grafiği oluşturur."""
    print(f"Grafik Hazırlanıyor: {sector_name}")
    
    # 2016 ve sonrası filtreleme
    df["Year"], df["Month"] = zip(*df["Dönem"].map(parse_period))
    filtered_df = df[df["Year"] >= 2016].copy()
    
    if filtered_df.empty:
        return

    # Dönem frekansları
    period_counts = filtered_df.groupby(["Year", "Month"]).size().reset_index(name="Frekans")
    period_counts = period_counts.sort_values(["Year", "Month"])
    period_counts["Label"] = period_counts.apply(lambda x: f"{int(x['Year'])}/{int(x['Month'])}", axis=1)
    
    total_records = period_counts["Frekans"].sum()
    total_firms_unique = filtered_df["Firma Adı"].nunique()
    
    # Matplotlib Çizimi
    plt.figure(figsize=(15, 8))
    colors = plt.cm.tab20(np.linspace(0, 1, len(period_counts)))
    bars = plt.bar(period_counts["Label"], period_counts["Frekans"], color=colors, edgecolor="gray", alpha=0.8)
    
    # Bar üstü sayılar
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + (yval * 0.01), int(yval), 
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.title(f"Dönem Dağılımı: {sector_name} (2016+) | Toplam: {total_records} Rapor", fontsize=15, fontweight='bold', pad=20)
    plt.xlabel("Dönem (Yıl/Ay)", fontsize=12)
    plt.ylabel("Rapor Sayısı", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.xticks(rotation=90)
    
    # Bilgi Notları
    plt.text(0.02, 0.95, f"Bu grafiğe {total_firms_unique} adet benzersiz firma katılmıştır", 
             transform=plt.gca().transAxes, fontsize=11, fontweight='bold', 
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))
    
    if sector_name == "GENEL_TOPLAM" and total_firms_with_dupes is not None:
        note_text = f"Bazı firmalar birkaç sektörde bulunuyor.\nBunları da dahil edersek {total_firms_with_dupes} adet firma var."
        plt.text(0.02, 0.85, note_text, 
                 transform=plt.gca().transAxes, fontsize=11, fontweight='bold', 
                 verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.4))
    
    plt.tight_layout()
    
    # Kaydetme
    safe_name = sector_name.replace(" ", "_").replace("İ", "I").replace("Ş", "S").replace("Ğ", "G").replace("Ü", "U").replace("Ö", "O").replace("Ç", "C")
    output_path = os.path.join(output_dir, f"1_donem_dagilimi_{safe_name}.png")
    plt.savefig(output_path, dpi=200)
    plt.close()

def create_retention_report(sector_data_dict, sheet_names, output_path):
    """Başlangıç dönemi bazlı veri tutma raporu oluşturur."""
    print("\nExcel Raporu (Hassasiyet Analizi) Hazırlanıyor...")
    
    all_periods = set()
    for df in sector_data_dict.values():
        all_periods.update(df["Dönem"].unique())
        
    sorted_periods = sorted([p for p in all_periods if parse_period(p)[0] >= 2016], key=lambda x: parse_period(x))
    
    results = []
    for start_period in sorted_periods:
        s_year, s_month = parse_period(start_period)
        row = {"Başlangıç Dönemi": start_period}
        total_rem = 0
        
        for sector, df in sector_data_dict.items():
            mask = (df["Year"] > s_year) | ((df["Year"] == s_year) & (df["Month"] >= s_month))
            count = len(df[mask])
            row[sector] = count
            total_rem += count
        
        row["TOPLAM VERİ"] = total_rem
        results.append(row)
        
    report_df = pd.DataFrame(results)
    cols = ["Başlangıç Dönemi", "TOPLAM VERİ"] + sheet_names
    report_df = report_df[cols]
    report_df.to_excel(output_path, index=False)
    print(f"Rapor kaydedildi: {os.path.basename(output_path)}")

def _plot_missing_freq_chart(all_missing_periods_flat, output_path, title_suffix, to_quarter_index_func):
    """Eksik dönemlerin frekans grafiğini çizen yardımcı fonksiyon."""
    from collections import Counter
    if not all_missing_periods_flat:
        return
        
    freq_counts = Counter(all_missing_periods_flat)
    freq_df = pd.DataFrame(list(freq_counts.items()), columns=["Dönem", "Eksik Firma Sayısı"])
    freq_df["sort_key"] = freq_df["Dönem"].apply(to_quarter_index_func)
    freq_df = freq_df.sort_values(by="sort_key")
    
    plt.figure(figsize=(15, 8))
    colors = plt.cm.autumn_r(np.linspace(0.2, 0.8, len(freq_df)))
    bars = plt.bar(freq_df["Dönem"], freq_df["Eksik Firma Sayısı"], color=colors, edgecolor="black", alpha=0.8)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + (yval * 0.01), int(yval), 
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
                 
    plt.title(f"Zaman Çizelgesi Boşluk Analizi: {title_suffix}", fontsize=15, fontweight='bold', pad=20)
    plt.xlabel("Dönem (Yıl/Ay)", fontsize=12)
    plt.ylabel("Eksik Beyan Sayısı (Firma)", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.xticks(rotation=90)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f" -> Grafik oluşturuldu: {os.path.basename(output_path)}")

def analyze_missing_periods_multi(sector_dfs, output_path, img_output_dir):
    """
    Firmaların ilk raporladığı dönemden, son raporladıkları döneme kadar 
    arada atladıkları/eksik olan çeyreklik dönemleri SEKTÖRE GÖRE tespit eder.
    Ayrıca her sektör için ayrı frekans grafiği üretir.
    """
    def to_quarter_index(p_str):
        try:
            y, m = map(int, str(p_str).split('/'))
            return y * 4 + (m // 3)
        except:
            return 0
            
    def from_quarter_index(idx):
        y = idx // 4
        quarter = idx % 4
        if quarter == 0: y -= 1; quarter = 4
        return f"{y}/{quarter * 3}"

    # Hazırlık
    data_to_analyze = sector_dfs.copy()
    # "TÜMÜ" (Genel Toplam) için veri birleştirme
    combined_all = pd.concat(sector_dfs.values(), ignore_index=True).drop_duplicates(subset=["Firma Adı", "Dönem"])
    data_to_analyze["TÜMÜ"] = combined_all

    # Kullanıcı Etkileşimi Kontrolü
    if os.path.exists(output_path):
        if CURRENCY:
            print(f"\n[!] Mevcut rapor bulundu, otonom modda yeniden analiz yapılıyor: {os.path.basename(output_path)}")
            ans = '1'
        else:
            print(f"\n[?] Mevcut eksik dönem analizi raporu bulundu: {os.path.basename(output_path)}")
            print(" 1. Yeniden Analiz Yap (Sektör bazlı baştan işle)")
            print(" 2. Sadece Görselleri Güncelle (Mevcut Excel verisini kullan)")
            print(" 3. Atla")
            ans = input("Seçiminiz: ").strip()
        
        if ans == '3':
            print(" -> Eksik dönem analizi atlandı.")
            return
        if ans == '2':
            print(" -> Mevcut rapor okunuyor ve grafikler güncelleniyor...")
            try:
                xl_existing = pd.ExcelFile(output_path)
                for sh_name in xl_existing.sheet_names:
                    df_sh = pd.read_excel(xl_existing, sheet_name=sh_name)
                    all_missing = []
                    for val in df_sh["Eksik Dönemler"].dropna():
                        if val != "Yok": all_missing.extend(str(val).split(", "))
                    img_path = os.path.join(img_output_dir, f"eksik_donem_frekans_{sh_name}.png")
                    _plot_missing_freq_chart(all_missing, img_path, sh_name, to_quarter_index)
                return
            except Exception as e:
                print(f" [HATA] Mevcut rapor okunamadı, yeniden analize geçiliyor: {e}")

    print("\nSektör Bazlı 'Eksik Dönem' Analizi Başlatıldı...")
    
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        for sector_name, df in data_to_analyze.items():
            print(f" İşleniyor: {sector_name}")
            results = []
            all_missing_flat = []
            
            clean_df = df.drop_duplicates(subset=["Firma Adı", "Dönem"]).copy()
            grouped = clean_df.groupby('Firma Adı')
            
            for firm, group in grouped:
                periods = group['Dönem'].dropna().unique()
                valid_indices = sorted([to_quarter_index(p) for p in periods if to_quarter_index(p) > 0])
                
                if not valid_indices: continue
                
                min_idx, max_idx = min(valid_indices), max(valid_indices)
                expected = set(range(min_idx, max_idx + 1))
                actual = set(valid_indices)
                missing = sorted(list(expected - actual))
                missing_p = [from_quarter_index(idx) for idx in missing]
                all_missing_flat.extend(missing_p)
                
                results.append({
                    "Firma Adı": firm,
                    "İlk Rapor Dönemi": from_quarter_index(min_idx),
                    "Son Rapor Dönemi": from_quarter_index(max_idx),
                    "Eksik Dönem Sayısı": len(missing_p),
                    "Eksik Dönemler": ", ".join(missing_p) if missing_p else "Yok"
                })
            
            # Excel Sayfası
            report_df = pd.DataFrame(results).sort_values(by=["Eksik Dönem Sayısı", "Firma Adı"], ascending=[False, True])
            safe_sheet = sector_name[:31].replace(" ", "_")
            report_df.to_excel(writer, sheet_name=safe_sheet, index=False)
            
            # Formata uygun kolon genişlikleri
            worksheet = writer.sheets[safe_sheet]
            for i, col in enumerate(report_df.columns):
                w = max(report_df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(w, 80))
            
            # Sektörel Grafik
            img_path = os.path.join(img_output_dir, f"eksik_donem_frekans_{safe_sheet}.png")
            _plot_missing_freq_chart(all_missing_flat, img_path, sector_name, to_quarter_index)

    print(f" -> Tüm sektörler analiz edildi. Rapor: {os.path.basename(output_path)}")
        
def main():
    # Klasörleri hazırla (Alt klasör yapısı için düzenlendi)
    for d in [IMG_DIR_SECTOR, IMG_DIR_MISSING, IMG_DIR_CONSISTENCY, report_output_dir]:
        if not os.path.exists(d): os.makedirs(d, exist_ok=True)

    print("--- 1. ADIM: VERİ ANALİZİ VE RAPORLAMA ---")
    
    # --- YENİ: Özellik Tutarlılık Kontrolü ---
    currency_files = [
        data_path,
        os.path.join(os.path.dirname(data_path), "Veri_Havuzu_EUR.xlsx"),
        os.path.join(os.path.dirname(data_path), "Veri_Havuzu_TRY.xlsx")
    ]
    
    is_consistent, f_sets = check_feature_consistency(currency_files)
    create_consistency_visual(is_consistent, f_sets, IMG_DIR_CONSISTENCY)
    
    if is_consistent:
        print("Müjde! Tüm kurlardaki özellik isimleri birebir uyuşuyor.")
    else:
        print("UYARI: Özellik isimlerinde farklılıklar var!")

    xl = pd.ExcelFile(data_path)
    
    all_sector_dfs = {}
    total_firms_sum = 0
    
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet_name, usecols=["Dönem", "Firma Adı"])
        df = df.dropna(subset=["Dönem"])
        df["Year"], df["Month"] = zip(*df["Dönem"].map(parse_period))
        
        # Sektörel benzersiz firma sayısı
        total_firms_sum += df["Firma Adı"].nunique()
        all_sector_dfs[sheet_name] = df
        
        # Grafik oluştur (Alt klasöre)
        create_sector_chart(df, sheet_name, IMG_DIR_SECTOR)
        
    # Genel Toplam Grafiği
    combined_df = pd.concat(all_sector_dfs.values(), ignore_index=True)
    create_sector_chart(combined_df, "GENEL_TOPLAM", IMG_DIR_SECTOR, total_firms_with_dupes=total_firms_sum)
    
    # Excel Raporu
    create_retention_report(all_sector_dfs, xl.sheet_names, report_file_path)
    
    # YENİ: Kayıp Dönemler Analizi (Sektörel Destekli)
    missing_report_name = "Firma_Eksik_Donem_Analizi.xlsx"
    if CURRENCY:
        missing_report_name = f"Firma_Eksik_Donem_Analizi_{CURRENCY}.xlsx"
    missing_report_path = os.path.join(report_output_dir, missing_report_name)
    analyze_missing_periods_multi(all_sector_dfs, missing_report_path, IMG_DIR_MISSING)
    
    print("\n--- İŞLEM TAMAMLANDI ---")
    print(f"Görseller: {img_base_dir}")
    print(f"Rapor: {report_output_dir}")

if __name__ == "__main__":
    main()
