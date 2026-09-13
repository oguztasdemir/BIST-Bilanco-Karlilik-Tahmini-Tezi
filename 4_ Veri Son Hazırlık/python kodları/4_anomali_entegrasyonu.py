import pandas as pd
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns

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
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "3_Adim_Zeki_Eleme")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "4_Adim_Anomali_Entegrasyonu")
os.makedirs(OUT_DIR, exist_ok=True)
ANOMALY_LIST_PATH = os.path.join(PHASE4_BASE, "kaynak_veriler", "Anomali_Listesi.xlsx")

def restore_anomaly_list(target_path):
    """Anomali_Listesi.xlsx dosyasını yeniden oluşturur."""
    data = [
        {'Dönem': 1, 'Tarih': '2016 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 2, 'Tarih': '2016 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 3, 'Tarih': '2016 Q3', 'Anomali': 1, 'Açıklama': '15 Temmuz Darbe Girişimi'},
        {'Dönem': 4, 'Tarih': '2016 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 5, 'Tarih': '2017 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 6, 'Tarih': '2017 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 7, 'Tarih': '2017 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 8, 'Tarih': '2017 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 9, 'Tarih': '2018 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 10, 'Tarih': '2018 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 11, 'Tarih': '2018 Q3', 'Anomali': 1, 'Açıklama': 'Rahip Brunson Krizi / Kur Şoku'},
        {'Dönem': 12, 'Tarih': '2018 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 13, 'Tarih': '2019 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 14, 'Tarih': '2019 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 15, 'Tarih': '2019 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 16, 'Tarih': '2019 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 17, 'Tarih': '2020 Q1', 'Anomali': 1, 'Açıklama': 'COVID-19 Pandemi Başlangıcı'},
        {'Dönem': 18, 'Tarih': '2020 Q2', 'Anomali': 1, 'Açıklama': 'Pandemi Kapanma Tedbirleri'},
        {'Dönem': 19, 'Tarih': '2020 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 20, 'Tarih': '2020 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 21, 'Tarih': '2021 Q1', 'Anomali': 1, 'Açıklama': 'TCMB Başkan Değişimi (Naci Ağbal)'},
        {'Dönem': 22, 'Tarih': '2021 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 23, 'Tarih': '2021 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 24, 'Tarih': '2021 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 25, 'Tarih': '2022 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 26, 'Tarih': '2022 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 27, 'Tarih': '2022 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 28, 'Tarih': '2022 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 29, 'Tarih': '2023 Q1', 'Anomali': 1, 'Açıklama': 'Kahramanmaraş Depremleri'},
        {'Dönem': 30, 'Tarih': '2023 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 31, 'Tarih': '2023 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 32, 'Tarih': '2023 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 33, 'Tarih': '2024 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 34, 'Tarih': '2024 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 35, 'Tarih': '2024 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 36, 'Tarih': '2024 Q4', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 37, 'Tarih': '2025 Q1', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 38, 'Tarih': '2025 Q2', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 39, 'Tarih': '2025 Q3', 'Anomali': 0, 'Açıklama': None},
        {'Dönem': 40, 'Tarih': '2025 Q4', 'Anomali': 0, 'Açıklama': None}
    ]
    pd.DataFrame(data).to_excel(target_path, index=False)

def run_anomaly_integration(input_file_name="3_Final_Filtreli_Veri_USD.xlsx"):
    currency = input_file_name.split("_")[-1].replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, f"4_Final_Anomali_Entegre_Veri_{currency}.xlsx")

    print(f"\n[>>>] Anomali Entegrasyonu Başlatılıyor: {input_file_name}")
    
    if not os.path.exists(ANOMALY_LIST_PATH):
        restore_anomaly_list(ANOMALY_LIST_PATH)
    
    # Verileri Yükle
    xl = pd.ExcelFile(input_path)
    anom_df = pd.read_excel(ANOMALY_LIST_PATH)
    
    # Görselleştirme Klasörünü Hazırla
    img_dir = os.path.join(PHASE4_BASE, "görseller", currency, "4_Anomali")
    os.makedirs(img_dir, exist_ok=True)

    anom_clean = anom_df[['Dönem', 'Anomali']].copy()
    anom_clean.rename(columns={'Anomali': 'Anomali_Durumu'}, inplace=True)
    anomaly_sector_stats = []

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - Sıfırdan Hedef İnşası (Shift-Lead): {sector}")
            df = pd.read_excel(xl, sector)
            target_col = 'Net Dönem Karı/Zararı'
            new_col = 'Net Dönem Karı (t+1)'
            if new_col in df.columns: df = df.drop(columns=[new_col])
            
            df['Firma_Temp'] = df['Firma Adı'].astype(str).str.upper().str.strip()
            df = df.sort_values(by=['Firma_Temp', 'Dönem'])
            df[new_col] = df.groupby('Firma_Temp')[target_col].shift(-1)
            df = df.drop(columns=['Firma_Temp'])
            
            df_final = pd.merge(df, anom_clean, on='Dönem', how='left')
            
            # Mevsimsellik Formülü: (Dönem - 1) % 4 + 1
            df_final['Mevsimsellik'] = ((df_final['Dönem'] - 1) % 4) + 1
            
            cols = list(df_final.columns)
            if 'Anomali_Durumu' in cols:
                cols.remove('Anomali_Durumu')
                cols.insert(2, 'Anomali_Durumu')
            if 'Mevsimsellik' in cols:
                cols.remove('Mevsimsellik')
                cols.insert(3, 'Mevsimsellik')
            if new_col in cols:
                cols.remove(new_col)
                cols.insert(cols.index(target_col) + 1, new_col)
            
            df_final[cols].to_excel(writer, sheet_name=sector, index=False)
            
            # İstatistikleri topla
            tot_obs = len(df_final)
            anom_obs = (df_final['Anomali_Durumu'] == 1).sum()
            norm_obs = tot_obs - anom_obs
            anomaly_sector_stats.append({
                "Sektör": sector,
                "Toplam Gözlem": tot_obs,
                "Normal Dönem Gözlem": norm_obs,
                "Anomali Dönem Gözlem": anom_obs,
                "Anomali Oranı (%)": f"{(anom_obs / tot_obs * 100):.2f}%"
            })

    # Görsel Rapor Oluştur (Anomali Zaman Çizelgesi + Tablo)
    try:
        # 1. Timeline Chart
        fig1, ax1 = plt.subplots(figsize=(15, 6))
        anom_plot_df = anom_df.sort_values('Dönem')
        colors = ['#2ECC71' if a == 0 else '#E74C3C' for a in anom_plot_df['Anomali']]
        
        bars = ax1.bar(anom_plot_df['Tarih'], [1]*len(anom_plot_df), color=colors, alpha=0.7, edgecolor='black', width=0.6)
        
        for bar, (_, row) in zip(bars, anom_plot_df.iterrows()):
            if row['Anomali'] == 1 and row['Açıklama']:
                ax1.text(bar.get_x() + bar.get_width()/2.0, 0.5, row['Açıklama'], 
                         ha='center', va='center', rotation=90, color='white', 
                         fontweight='bold', fontsize=9, bbox=dict(facecolor='black', alpha=0.6, boxstyle='round,pad=0.3'))
        
        ax1.set_title(f"Zaman Serisi Anomali Takvimi ({currency})", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Dönemler (Çeyrekler)", fontsize=11)
        ax1.set_ylabel("Anomali Durumu", fontsize=11)
        ax1.set_xticks(range(len(anom_plot_df['Tarih'])))
        ax1.set_xticklabels(anom_plot_df['Tarih'], rotation=45, ha='right')
        ax1.set_yticks([])
        ax1.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        img_path1 = os.path.join(img_dir, f"4_Anomali_Zaman_Cizelgesi_{currency}.png")
        plt.savefig(img_path1, dpi=200)
        plt.close()

        # 2. Table: Sektörel Dağılım Tablosu
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.axis('off')
        plt.title("SEKTÖRLERE GÖRE ANOMALİ GÖZLEM DAĞILIM TABLOSU", fontsize=14, fontweight='bold', pad=15)
        
        df_anom_stats = pd.DataFrame(anomaly_sector_stats)
        table = ax2.table(cellText=df_anom_stats.values, colLabels=df_anom_stats.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.0, 2.2)
        
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#E74C3C') # Kırmızı
            else:
                if c == 0: cell.set_facecolor('#FDEDEC')
                else: cell.set_facecolor('white')
                
        plt.tight_layout()
        img_path2 = os.path.join(img_dir, f"4_Anomali_Sektorel_Dagilim_Tablosu_{currency}.png")
        plt.savefig(img_path2, dpi=200)
        plt.close()
        
        print(f"[+] Anomali görselleri kaydedildi: {img_path1} ve {img_path2}")
    except Exception as e:
        print(f"Görsel oluşturma hatası: {e}")

    print(f"[+] Anomali entegre edilmiş veri kaydedildi: {os.path.basename(output_path)}")

if __name__ == "__main__":
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("3_Final_Filtreli_Veri_") and f.endswith(".xlsx")]
        for f_name in files:
            run_anomaly_integration(f_name)
