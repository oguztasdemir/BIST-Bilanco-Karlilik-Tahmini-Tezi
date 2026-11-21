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

DATA_PATH = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu_Birlesik.xlsx")
if not os.path.exists(DATA_PATH):
    # Fallback
    DATA_PATH = os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", "Veri_Havuzu_Birlesik.xlsx")

if not CURRENCY:
    if "USD" in DATA_PATH: CURRENCY = "USD"
    elif "EUR" in DATA_PATH: CURRENCY = "EUR"
    elif "TRY" in DATA_PATH: CURRENCY = "TRY"

OUT_DIR = os.path.join(BASE_PATH, "görseller", "5_Esik_Analizi")
os.makedirs(OUT_DIR, exist_ok=True)

def run_threshold_analysis():
    print("--- Step 5: Doluluk Eşiği Analizi Başlatıldı ---")
    
    if not os.path.exists(DATA_PATH):
        print(f"Hata: Veri dosyası bulunamadı: {DATA_PATH}")
        return

    xl = pd.ExcelFile(DATA_PATH)
    thresholds = [i for i in range(0, 101, 10)] # %0, %10, ..., %100
    
    # Görsel stil ayarları
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Roboto', 'Arial']
    
    for sector_name in xl.sheet_names:
        print(f"Sektör Analiz Ediliyor: {sector_name}")
        df = pd.read_excel(xl, sheet_name=sector_name)
        
        # ID kolonlarını ayıkla (Önceki adımlarla uyumlu)
        id_cols = [c for c in df.columns if any(x in str(c).upper() for x in ['FRMA', 'FIRMA', 'DNEM', 'DÖNEM', 'YEAR', 'MONTH', 'DÖNEM'])]
        features = [c for c in df.columns if c not in id_cols]
        
        if not features:
            print(f"Uyarı: {sector_name} sektörü için özellik sütunu bulunamadı.")
            continue
            
        total_features = len(features)
        # Her bir özelliğin (sütunun) doluluk oranını hesapla
        fill_rates = df[features].notna().mean() * 100
        
        counts = []
        for t in thresholds:
            # Eşiği geçen özellik sayısını say
            count = (fill_rates >= t).sum()
            counts.append(count)
            
        # --- GÖRSELLEŞTİRME ---
        plt.figure(figsize=(11, 7))
        
        # Renk paleti (Eşiğe göre koyulaşan)
        palette = sns.color_palette("viridis_r", len(thresholds))
        
        # Bar chart
        bars = plt.bar(thresholds, counts, width=7, color=palette, alpha=0.8, edgecolor='0.3')
        
        # Çizgi grafik (Trendi göstermek için)
        plt.plot(thresholds, counts, marker='o', color='#e74c3c', linewidth=3, markersize=8, label='Kalan Özellik Sayısı')
        
        # Değerleri barların üzerine yaz
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + (total_features * 0.02), int(yval), 
                     ha='center', va='bottom', fontweight='bold', fontsize=10, color='black')

        # Başlık ve Etiketler
        plt.title(f"Sektör: {sector_name}\nDoluluk Oranı Eşiğine Göre Özellik Eleme Analizi", fontsize=15, fontweight='bold', pad=20)
        plt.xlabel("Doluluk Eşiği (%)", fontsize=12, fontweight='bold')
        plt.ylabel("Kalan Özellik Sayısı", fontsize=12, fontweight='bold')
        plt.xticks(thresholds, [f"%{t}" for t in thresholds])
        
        # Y eksenini biraz esnet (Yazıların sığması için)
        plt.ylim(0, total_features * 1.2)
        
        # Izgara ve estetik dokunuşlar
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout()
        
        # Kaydet
        safe_name = re.sub(r'[\\/*?:\[\]]', '', sector_name)[:31]
        out_path = os.path.join(OUT_DIR, f"{safe_name}_Esik_Analizi.png")
        plt.savefig(out_path, dpi=300)
        plt.close()

    # EXCEL RAPORU OLUŞTUR
    summary_data = {"Eşik (%)": [f"%{t}" for t in thresholds]}
    
    # Her sektör için hesaplanan counts değerlerini bir sözlükte topla (Yukarıdaki döngüde toplamak daha doğru olur)
    # Bu yüzden döngüyü hafifçe güncelleyelim.
    
    # (Hızlıca tekrar hesaplamak yerine yukarıdaki döngüyü refine etmek daha iyi ama bu yapıya uygun devam edelim)
    
    # RE-RUN logic for summary table (Hızlı ve temiz)
    for sector_name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sector_name)
        id_cols = [c for c in df.columns if any(x in str(c).upper() for x in ['FRMA', 'FIRMA', 'DNEM', 'DÖNEM', 'YEAR', 'MONTH', 'DÖNEM'])]
        features = [c for c in df.columns if c not in id_cols]
        if not features: continue
        
        fill_rates = df[features].notna().mean() * 100
        summary_data[sector_name] = [(fill_rates >= t).sum() for t in thresholds]

    summary_df = pd.DataFrame(summary_data)
    excel_dir = os.path.join(BASE_PATH, "raporlar", "5_Doluluk_Esik")
    os.makedirs(excel_dir, exist_ok=True)
    report_name = f"5_Doluluk_Esik_Raporu_{CURRENCY}.xlsx" if CURRENCY else "5_Doluluk_Esik_Raporu.xlsx"
    excel_path = os.path.join(excel_dir, report_name)
    summary_df.to_excel(excel_path, index=False)

    # --- YENİ EKLEME: ISİ HARİTASI (HEATMAP) ---
    try:
        plt.figure(figsize=(14, 8))
        # Eşik sütununu indekse al
        heatmap_df = summary_df.set_index("Eşik (%)").transpose()
        sns.heatmap(heatmap_df, annot=True, fmt="d", cmap="YlGnBu", linewidths=.5, cbar_kws={'label': 'Özellik Sayısı'})
        plt.title("Sektörler ve Eşik Değerlerine Göre Özellik Korunumu (Heatmap)", fontsize=16, fontweight='bold', pad=20)
        plt.xlabel("Doluluk Eşiği", fontsize=12)
        plt.ylabel("Sektörler", fontsize=12)
        plt.tight_layout()
        heatmap_out = os.path.join(OUT_DIR, "99_Genel_Esik_Karsilastirma_Heatmap.png")
        plt.savefig(heatmap_out, dpi=300)
        plt.close()
        print(f"  - Karşılaştırmalı Heatmap oluşturuldu: {heatmap_out}")
    except Exception as e:
        print(f"  - Isı haritası oluşturulamadı: {e}")

    print(f"\nAnaliz tamamlandı.")
    print(f"  - Görseller: {OUT_DIR}")
    print(f"  - Excel Raporu: {excel_path}")

if __name__ == "__main__":
    run_threshold_analysis()
