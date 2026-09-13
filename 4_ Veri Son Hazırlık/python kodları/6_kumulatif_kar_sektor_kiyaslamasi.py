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
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "5_Adim_Mevsimsellik_Entegrasyonu")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "6_Adim_Kumulatif_Sektor_Kiyaslamasi")
os.makedirs(OUT_DIR, exist_ok=True)

def run_cumulative_sector_comparison(input_file_name):
    currency = input_file_name.split("_")[-1].replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, f"6_Final_Kumulatif_Sektor_Kiyaslamasi_{currency}.xlsx")

    print(f"\n[>>>] 6. Adım: Kümülatif Net Kar ve Sektor Kıyaslaması Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    
    # Görselleştirme Klasörünü Hazırla
    img_dir = os.path.join(PHASE4_BASE, "görseller", currency, "6_Kumulatif_Kar")
    os.makedirs(img_dir, exist_ok=True)

    all_sector_trends = []

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - İşleniyor (Kümülatif Kıyaslama): {sector}")
            df = pd.read_excel(xl, sector)
            
            df.columns = [c.strip() for c in df.columns]
            
            f_col = 'Firma Adı' if 'Firma Adı' in df.columns else [c for c in df.columns if 'FIRMA' in c.upper()][0]
            d_col = 'Dönem' if 'Dönem' in df.columns else [c for c in df.columns if 'DONEM' in c.upper()][0]
            p_col = 'Net Dönem Karı/Zararı' if 'Net Dönem Karı/Zararı' in df.columns else [c for c in df.columns if 'KAR' in c.upper() or 'ZARAR' in c.upper()][0]
            
            df = df.sort_values(by=[f_col, d_col]).reset_index(drop=True)
            
            # 1. Firmanın o döneme kadarki tüm dönemlerinin net karını toplayalım (expanding cumsum)
            df['Firma_Kum_Kar'] = df.groupby(f_col)[p_col].cumsum()
            
            # 2. O sektördeki diğer firmaların o döneme kadarki kümülatif karlarının ortalamasını alalım (Leave-One-Out Mean)
            period_totals = df.groupby(d_col)['Firma_Kum_Kar'].transform('sum')
            period_counts = df.groupby(d_col)[f_col].transform('count')
            
            df['Sektor_Ort_Kum_Kar'] = np.where(
                period_counts > 1,
                (period_totals - df['Firma_Kum_Kar']) / (period_counts - 1),
                df['Firma_Kum_Kar']
            )
            
            # 3. Firmamızın sektöre göre büyüklüğünü ve etkilenmesini ölçen oransal/fark özniteliği
            df['Sektorel_Kumulatif_Gorece_Kar'] = (df['Firma_Kum_Kar'] - df['Sektor_Ort_Kum_Kar']) / (df['Sektor_Ort_Kum_Kar'].abs() + 1)
            
            # Trend Verisi Topla (Grafik İçin Sektör Ortalama Kümülatif Kâr)
            trend = df.groupby(d_col)['Firma_Kum_Kar'].mean().reset_index()
            trend['Sektör'] = sector
            all_sector_trends.append(trend)

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

    cumulative_sector_stats = []
    for trend in all_sector_trends:
        sec_name = trend.iloc[0]['Sektör']
        start_val = trend.iloc[0]['Firma_Kum_Kar']
        end_val = trend.iloc[-1]['Firma_Kum_Kar']
        growth = ((end_val - start_val) / (abs(start_val) + 1e-5)) * 100
        cumulative_sector_stats.append({
            "Sektör": sec_name,
            "Başlangıç Dönemi": f"{trend.iloc[0][d_col]}. Dönem",
            "Bitiş Dönemi": f"{trend.iloc[-1][d_col]}. Dönem",
            "İlk Ort. Küm. Kâr": f"{start_val:,.2f}",
            "Son Ort. Küm. Kâr": f"{end_val:,.2f}",
            "Toplam Kümülatif Büyüme (%)": f"{growth:.2f}%"
        })

    # Görsel Rapor Oluştur (Kümülatif Sektörel Kâr Trendi + Tablo)
    try:
        combined_trends = pd.concat(all_sector_trends)
        
        # 1. Line plot
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        sns.lineplot(data=combined_trends, x=d_col, y='Firma_Kum_Kar', hue='Sektör', marker='o', linewidth=2, ax=ax1)
        ax1.set_title(f"Sektör Bazında Ortalama Kümülatif Kâr Trendi ({currency})", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Dönemler (Çeyrekler)", fontsize=11)
        ax1.set_ylabel(f"Ortalama Kümülatif Kâr ({currency})", fontsize=11)
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(title='Sektörler', loc='upper left')
        
        # Annotate last point of each line
        for sec in combined_trends['Sektör'].unique():
            df_sec = combined_trends[combined_trends['Sektör'] == sec]
            last_row = df_sec.iloc[-1]
            ax1.annotate(f"{last_row['Firma_Kum_Kar']:,.0f}", 
                          (last_row[d_col], last_row['Firma_Kum_Kar']),
                          textcoords="offset points", 
                          xytext=(10,-5), 
                          ha='left', 
                          fontsize=8, 
                          fontweight='bold')
        plt.tight_layout()
        img_path1 = os.path.join(img_dir, f"6_Kumulatif_Sektor_Kar_Trendi_{currency}.png")
        plt.savefig(img_path1, dpi=200)
        plt.close()
        
        # 2. Stats Table
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.axis('off')
        plt.title("SEKTÖRLERE GÖRE KÜMÜLATİF KÂR BÜYÜME İSTATİSTİKLERİ", fontsize=14, fontweight='bold', pad=15)
        
        df_cum_stats = pd.DataFrame(cumulative_sector_stats)
        table = ax2.table(cellText=df_cum_stats.values, colLabels=df_cum_stats.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.0, 2.2)
        
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#2E4053')
            else:
                if c == 0: cell.set_facecolor('#EAECEE')
                elif c == 5: cell.set_facecolor('#D5F5E3') # light green for growth rate
                else: cell.set_facecolor('white')
                
        plt.tight_layout()
        img_path2 = os.path.join(img_dir, f"6_Kumulatif_Kar_Buyume_Tablosu_{currency}.png")
        plt.savefig(img_path2, dpi=200)
        plt.close()
        
        print(f"[+] Kümülatif kâr görselleri kaydedildi: {img_path1} ve {img_path2}")
    except Exception as e:
        print(f"Kümülatif kâr görseli oluşturma hatası: {e}")
            
    print(f"[+] 6. Adım tamamlandı ve kaydedildi: {os.path.basename(output_path)}")

if __name__ == "__main__":
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("5_Final_Mevsimsellik_Entegre_Veri_") and f.endswith(".xlsx")]
        if not files:
            print("Uyarı: İşlenecek veri dosyası bulunamadı!")
        else:
            for f_name in files:
                try:
                    run_cumulative_sector_comparison(f_name)
                except Exception as e:
                    print(f"Hata ({f_name}): {e}")
    else:
        print(f"Hata: Giriş klasörü bulunamadı: {INPUT_DIR}")
