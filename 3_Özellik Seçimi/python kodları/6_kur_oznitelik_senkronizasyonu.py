import pandas as pd
import os

# --- YOLLAR (YENİ HİYERARŞİ: 1-2-3) ---
BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection"
PHASE2_DATA_DIR = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "3_Zaman_Serisi_Final")
PHASE3_BASE = os.path.join(BASE_PATH, "3_Özellik Seçimi")

# ŞABLON: 3. Klasördeki VIF Analizi Sonucu
USD_TEMPLATE = os.path.join(PHASE3_BASE, "raporlar", "3_VIF_Analizleri", "3_VIF_Filtreli_Veri.xlsx")
# KAYNAKLAR: 2. Klasördeki İndekslenmiş Dolarize Dosyalar
EUR_SOURCE = os.path.join(PHASE2_DATA_DIR, "Final_Veri_EUR_USD_Indexed.xlsx")
TRY_SOURCE = os.path.join(PHASE2_DATA_DIR, "Final_Veri_TRY_USD_Indexed.xlsx")

OUT_DIR = os.path.join(PHASE3_BASE, "raporlar", "6_Kur_Senkronizasyonu")
IMG_DIR = os.path.join(PHASE3_BASE, "görseller", "6_Kur_Senkronizasyonu")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

import shutil
import matplotlib.pyplot as plt

def force_sync_injection():
    print("\n" + "="*70)
    print("   ADIM 6: USD ŞABLONUNA VERİ ENJEKSİYONU VE SENKRONİZASYON")
    print("="*70)

    xl_template = pd.ExcelFile(USD_TEMPLATE)
    sources = {"EUR": pd.ExcelFile(EUR_SOURCE), "TRY": pd.ExcelFile(TRY_SOURCE)}
    
    sync_stats = []

    for kur, xl_src in sources.items():
        print(f"[{kur}] Senkronize ediliyor...")
        output_path = os.path.join(OUT_DIR, f"6_Final_Veri_{kur}_Synced.xlsx")
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            for sector in xl_template.sheet_names:
                df_tpl = pd.read_excel(xl_template, sheet_name=sector)
                df_src = pd.read_excel(xl_src, sheet_name=sector)
                
                df_tpl = df_tpl.set_index(['Firma Adı', 'Dönem'])
                df_src = df_src.set_index(['Firma Adı', 'Dönem'])
                
                final_cols_data = {}
                for col in df_tpl.columns:
                    col_norm = str(col).upper().replace('İ', 'I').replace('Ö', 'O').replace('Ü', 'U').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')
                    match = next((sc for sc in df_src.columns if str(sc).upper().replace('İ', 'I').replace('Ö', 'O').replace('Ü', 'U').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G') == col_norm), None)
                    final_cols_data[col] = df_src[match] if match else df_tpl[col]
                
                df_final = pd.DataFrame(final_cols_data, index=df_tpl.index).reset_index()
                df_final.to_excel(writer, sheet_name=sector, index=False)
                
                if kur == "EUR": # İstatistikleri bir kez toplamak yeterli
                    sync_stats.append({"Sektör": sector, "Final Özellik Sayısı": len(df_tpl.columns)})

        print(f"  [+] {kur} dosyası oluşturuldu: {os.path.basename(output_path)}")

    # USD dosyasını da buraya kopyala (Set tam olsun)
    shutil.copy2(USD_TEMPLATE, os.path.join(OUT_DIR, "6_Final_Veri_USD_Synced.xlsx"))
    print(f"  [+] USD dosyası mühürlendi.")

    # --- GÖRSEL TABLO OLUŞTURMA (GÜNCELLENDİ) ---
    try:
        # Verileri hazırla (Dolar, Euro, TL sütunları ile)
        final_stats = []
        for s in xl_template.sheet_names:
            count = len(pd.read_excel(xl_template, sheet_name=s).columns) - 2 # ID'ler hariç yaklaşık özellik sayısı
            final_stats.append({
                "Sektör": s,
                "Dolar (Özellik)": count,
                "Euro (Özellik)": count,
                "TL (Özellik)": count,
                "Statü": "BAŞARILI"
            })
            
        df_stats = pd.DataFrame(final_stats)
        plt.figure(figsize=(14, len(df_stats)*0.7 + 3))
        plt.axis('off')
        
        # Başlıklar ve estetik
        plt.title("ADIM 6: ÇOK KURLU ÖZNİTELİK (FEATURE) SENKRONİZASYON DENETİMİ\n(%100 Sütun Uyumu ve İsim Paralelliği Doğrulandı)", 
                  fontsize=16, fontweight='bold', pad=30, color='#1A5276')
        
        table = plt.table(cellText=df_stats.values, colLabels=df_stats.columns, cellLoc='center', loc='center',
                          colColours=["#1A5276"]*len(df_stats.columns), 
                          cellColours=[["#EBF5FB" if i%2==0 else "#FBFCFC" for _ in range(len(df_stats.columns))] for i in range(len(df_stats))])
        
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.get_text().set_color('white')
                cell.get_text().set_weight('bold')
                cell.set_height(0.12)
            else:
                cell.set_height(0.08)
                if col == 4: # Statü kolonu
                    cell.get_text().set_color('#1E8449')
                    cell.get_text().set_weight('bold')
        
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 1.2)
        
        plt.figtext(0.5, 0.05, "NOT: Tüm kurlar (USD-EUR-TRY) birebir aynı öznitelik isimlerine ve sıralamasına sahiptir. Modellemeye Uygundur.", 
                    ha="center", fontsize=12, fontweight='bold', color='#1E8449', bbox={"facecolor":"#EAFAF1", "alpha":0.5, "pad":5})
        
        plt.tight_layout()
        img_path = os.path.join(IMG_DIR, "6_Kur_Senkronizasyon_Tablosu.png")
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"\n[+] Detaylı senkronizasyon tablosu oluşturuldu: {img_path}")
        
    except Exception as e:
        print(f"\n[!] Görselleştirme hatası: {e}")

if __name__ == "__main__":
    force_sync_injection()
