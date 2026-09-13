import pandas as pd
import numpy as np
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
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "6_Adim_Kumulatif_Sektor_Kiyaslamasi")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "7_Adim_Cari_Donem_Sektor_Kiyaslamasi")
os.makedirs(OUT_DIR, exist_ok=True)

def run_current_period_sector_comparison(input_file_name):
    currency = input_file_name.split("_")[-1].replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, f"7_Final_Cari_Donem_Sektor_Kiyaslamasi_{currency}.xlsx")

    print(f"\n[>>>] 7. Adım: Cari Dönem Sektörel Görece Durum Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    
    # Görselleştirme Klasörünü Hazırla
    img_dir = os.path.join(PHASE4_BASE, "görseller", currency, "7_Cari_Sektor")
    os.makedirs(img_dir, exist_ok=True)

    all_sector_z_scores = []

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - İşleniyor (Cari Dönem Kıyaslama): {sector}")
            df = pd.read_excel(xl, sector)
            
            df.columns = [c.strip() for c in df.columns]
            
            f_col = 'Firma Adı' if 'Firma Adı' in df.columns else [c for c in df.columns if 'FIRMA' in c.upper()][0]
            d_col = 'Dönem' if 'Dönem' in df.columns else [c for c in df.columns if 'DONEM' in c.upper()][0]
            p_col = 'Net Dönem Karı/Zararı' if 'Net Dönem Karı/Zararı' in df.columns else [c for c in df.columns if 'KAR' in c.upper() or 'ZARAR' in c.upper()][0]
            
            df = df.sort_values(by=[f_col, d_col]).reset_index(drop=True)
            
            # 1. Cari dönemde diğer firmaların ortalama karı (Leave-One-Out Mean)
            period_totals = df.groupby(d_col)[p_col].transform('sum')
            period_counts = df.groupby(d_col)[f_col].transform('count')
            
            df['Sektor_Ort_Cari_Kar'] = np.where(
                period_counts > 1,
                (period_totals - df[p_col]) / (period_counts - 1),
                df[p_col]
            )
            
            # 2. Makro şoklara karşı çok daha dirençli olan Sektör Medyanı ve IQR hesaplaması
            df['Sektor_Medyan_Cari_Kar'] = df.groupby(d_col)[p_col].transform('median')
            q75 = df.groupby(d_col)[p_col].transform(lambda x: x.quantile(0.75) if len(x) > 2 else x.max())
            q25 = df.groupby(d_col)[p_col].transform(lambda x: x.quantile(0.25) if len(x) > 2 else x.min())
            df['Sektor_IQR_Cari_Kar'] = q75 - q25
            
            iqr_safe = np.where(df['Sektor_IQR_Cari_Kar'] == 0, 1, df['Sektor_IQR_Cari_Kar'])
            
            # 3. Görece Oranlar ve Z-Skoru
            df['Sektorel_Cari_Gorece_Kar'] = (df[p_col] - df['Sektor_Ort_Cari_Kar']) / (df['Sektor_Ort_Cari_Kar'].abs() + 1)
            df['Sektorel_Cari_Z_Skoru'] = (df[p_col] - df['Sektor_Medyan_Cari_Kar']) / (abs(iqr_safe) + 1)
            
            # Z-skor verilerini topla
            z_df = df[['Sektorel_Cari_Z_Skoru']].copy()
            z_df['Sektör'] = sector
            all_sector_z_scores.append(z_df)

            # --- KOLON SIRALAMASI REVİZYONU ---
            cols = list(df.columns)
            target_curr = p_col
            target_lead = 'Net Dönem Karı (t+1)' if 'Net Dönem Karı (t+1)' in df.columns else None
            
            if target_curr in cols: cols.remove(target_curr)
            if target_lead and target_lead in cols: cols.remove(target_lead)
            
            cols.append(target_curr)
            if target_lead:
                cols.append(target_lead)
                
            df = df[cols]
            df.to_excel(writer, sheet_name=sector, index=False)

    # Görsel Rapor Oluştur (Z-Skor Dağılım Kutusu + Tablo)
    try:
        combined_z_df = pd.concat(all_sector_z_scores)
        
        # Calculate stats for the table
        z_stats = []
        for sec in combined_z_df['Sektör'].unique():
            df_sec = combined_z_df[combined_z_df['Sektör'] == sec]['Sektorel_Cari_Z_Skoru']
            desc = df_sec.describe()
            z_stats.append({
                "Sektör": sec,
                "Min Z-Skor": f"{desc['min']:.4f}",
                "25% Kartil": f"{desc['25%']:.4f}",
                "Medyan (50%)": f"{desc['50%']:.4f}",
                "75% Kartil": f"{desc['75%']:.4f}",
                "Maks Z-Skor": f"{desc['max']:.4f}"
            })
        df_z_stats = pd.DataFrame(z_stats)
        
        # 1. Box plot
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        sns.boxplot(data=combined_z_df, x='Sektör', y='Sektorel_Cari_Z_Skoru', palette='Set3', ax=ax1)
        ax1.set_title(f"Sektörlere Göre Cari Görece Kâr Z-Skor Dağılımları ({currency})", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Sektör", fontsize=11)
        ax1.set_ylabel("Sektörel Z-Skoru (Normalleştirilmiş)", fontsize=11)
        ax1.set_xticklabels(combined_z_df['Sektör'].unique(), rotation=15, ha='right')
        ax1.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        img_path1 = os.path.join(img_dir, f"7_Sektorel_Z_Skor_Dagilimi_{currency}.png")
        plt.savefig(img_path1, dpi=200)
        plt.close()
        
        # 2. Stats Table
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.axis('off')
        plt.title("SEKTÖREL Z-SKOR DAĞILIM İSTATİSTİKLERİ TABLOSU", fontsize=14, fontweight='bold', pad=15)
        
        table = ax2.table(cellText=df_z_stats.values, colLabels=df_z_stats.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.0, 2.2)
        
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#2471A3')
            else:
                if c == 0: cell.set_facecolor('#EBF5FB')
                elif c == 3: cell.set_facecolor('#FCF3CF') # yellow for median
                else: cell.set_facecolor('white')
                
        plt.tight_layout()
        img_path2 = os.path.join(img_dir, f"7_Sektorel_Z_Skor_İstatistik_Tablosu_{currency}.png")
        plt.savefig(img_path2, dpi=200)
        plt.close()
        
        print(f"[+] Z-skor görselleri kaydedildi: {img_path1} ve {img_path2}")
    except Exception as e:
        print(f"Z-skor görseli oluşturma hatası: {e}")
            
    print(f"[+] 7. Adım tamamlandı ve kaydedildi: {os.path.basename(output_path)}")

if __name__ == "__main__":
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("6_Final_Kumulatif_Sektor_Kiyaslamasi_") and f.endswith(".xlsx")]
        if not files:
            print("Uyarı: İşlenecek veri dosyası bulunamadı!")
        else:
            for f_name in files:
                try:
                    run_current_period_sector_comparison(f_name)
                except Exception as e:
                    print(f"Hata ({f_name}): {e}")
    else:
        print(f"Hata: Giriş klasörü bulunamadı: {INPUT_DIR}")
