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
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "7_Adim_Cari_Donem_Sektor_Kiyaslamasi")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "8_Adim_Mevsimsel_Gecmis_Sektor_Kiyaslamasi")
os.makedirs(OUT_DIR, exist_ok=True)

def run_seasonal_history_sector_comparison(input_file_name):
    currency = input_file_name.split("_")[-1].replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, f"8_Final_Mevsimsel_Gecmis_Sektor_Kiyaslamasi_{currency}.xlsx")

    print(f"\n[>>>] 8. Adım: Mevsimsel Geçmiş ve Sektörel Mevsimsel Kıyas Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    
    # Görselleştirme Klasörünü Hazırla
    img_dir = os.path.join(PHASE4_BASE, "görseller", currency, "8_Mevsimsel_Gecmis")
    os.makedirs(img_dir, exist_ok=True)

    yoy_growth_stats = []

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - İşleniyor (Mevsimsel Geçmiş Kıyaslama): {sector}")
            df = pd.read_excel(xl, sector)
            
            df.columns = [c.strip() for c in df.columns]
            
            f_col = 'Firma Adı' if 'Firma Adı' in df.columns else [c for c in df.columns if 'FIRMA' in c.upper()][0]
            d_col = 'Dönem' if 'Dönem' in df.columns else [c for c in df.columns if 'DONEM' in c.upper()][0]
            p_col = 'Net Dönem Karı/Zararı' if 'Net Dönem Karı/Zararı' in df.columns else [c for c in df.columns if 'KAR' in c.upper() or 'ZARAR' in c.upper()][0]
            
            if 'Mevsimsellik' not in df.columns:
                df['Mevsimsellik'] = ((df[d_col] - 1) % 4) + 1
                
            df = df.sort_values(by=[f_col, d_col]).reset_index(drop=True)
            
            # --- 1. FİRMANIN MEVSİMSEL GEÇMİŞİ ---
            df['Firma_Gecen_Yil_Ayni_Ceyrek_Kar'] = df.groupby(f_col)[p_col].shift(4)
            
            def expanding_seasonal_mean(s):
                return s.expanding().mean().shift(1)
                
            df['Firma_Mevsimsel_Gecmis_Ort_Kar'] = df.groupby([f_col, 'Mevsimsellik'])[p_col].transform(expanding_seasonal_mean)
            
            # --- 2. SEKTÖRÜN MEVSİMSEL GEÇMİŞİ ---
            s_ort_col = 'Sektor_Ort_Cari_Kar' if 'Sektor_Ort_Cari_Kar' in df.columns else p_col
            
            df['Sektor_Gecen_Yil_Ayni_Ceyrek_Ort_Kar'] = df.groupby(f_col)[s_ort_col].shift(4)
            df['Sektor_Mevsimsel_Gecmis_Ort_Kar'] = df.groupby([f_col, 'Mevsimsellik'])[s_ort_col].transform(expanding_seasonal_mean)
            
            # --- 3. EKSİK VERİ (NaN) YÖNETİMİ ---
            df['Firma_Gecen_Yil_Ayni_Ceyrek_Kar'] = df['Firma_Gecen_Yil_Ayni_Ceyrek_Kar'].fillna(df[p_col])
            df['Firma_Mevsimsel_Gecmis_Ort_Kar'] = df['Firma_Mevsimsel_Gecmis_Ort_Kar'].fillna(df[p_col])
            df['Sektor_Gecen_Yil_Ayni_Ceyrek_Ort_Kar'] = df['Sektor_Gecen_Yil_Ayni_Ceyrek_Ort_Kar'].fillna(df[s_ort_col])
            df['Sektor_Mevsimsel_Gecmis_Ort_Kar'] = df['Sektor_Mevsimsel_Gecmis_Ort_Kar'].fillna(df[s_ort_col])
            
            # --- 4. GÖRECE MOMENTUM ÖZNİTELİKLERİ ---
            df['Mevsimsel_YoY_Kar_Büyümesi'] = (df[p_col] - df['Firma_Gecen_Yil_Ayni_Ceyrek_Kar']) / (df['Firma_Gecen_Yil_Ayni_Ceyrek_Kar'].abs() + 1)
            df['Sektorel_Mevsimsel_Gorece_Kar'] = (df['Firma_Mevsimsel_Gecmis_Ort_Kar'] - df['Sektor_Mevsimsel_Gecmis_Ort_Kar']) / (df['Sektor_Mevsimsel_Gecmis_Ort_Kar'].abs() + 1)
            
            # YoY Büyüme Değerlerini Topla
            yoy_col = df['Mevsimsel_YoY_Kar_Büyümesi']
            avg_yoy = yoy_col.mean()
            min_yoy = yoy_col.min()
            max_yoy = yoy_col.max()
            std_yoy = yoy_col.std()
            yoy_growth_stats.append({
                'Sektör': sector,
                'Ortalama YoY Büyüme': avg_yoy,
                'Min YoY Büyüme': min_yoy,
                'Maks YoY Büyüme': max_yoy,
                'Standart Sapma': std_yoy
            })

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

    # Görsel Rapor Oluştur (Mevsimsel YoY Büyüme + Tablo)
    try:
        growth_df = pd.DataFrame(yoy_growth_stats)
        
        # 1. Bar plot
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        colors = ['#2ECC71' if x >= 0 else '#E74C3C' for x in growth_df['Ortalama YoY Büyüme']]
        sns.barplot(data=growth_df, x='Sektör', y='Ortalama YoY Büyüme', palette=colors, ax=ax1)
        
        # Barların üzerine tam sayısal değerleri ekle
        for p in ax1.patches:
            val = p.get_height()
            if pd.notna(val):
                va_dir = 'bottom' if val < 0 else 'top'
                offset = -14 if val < 0 else 6
                ax1.annotate(f"{val:.4f}", 
                            (p.get_x() + p.get_width() / 2., val),
                            ha='center', va=va_dir, 
                            xytext=(0, offset), 
                            textcoords='offset points', 
                            fontsize=9, fontweight='bold', color='black')
        
        ax1.set_title(f"Sektörlere Göre Ortalama Mevsimsel YoY Kâr Büyümesi ({currency})", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Sektör", fontsize=11)
        ax1.set_ylabel("Ortalama YoY Büyüme Oranı", fontsize=11)
        ax1.set_xticklabels(growth_df['Sektör'].unique(), rotation=15, ha='right')
        ax1.grid(True, axis='y', linestyle='--', alpha=0.5)
        ax1.axhline(0, color='black', linewidth=1, linestyle='-')
        plt.tight_layout()
        img_path1 = os.path.join(img_dir, f"8_Sektorel_Mevsimsel_YoY_Büyüme_{currency}.png")
        plt.savefig(img_path1, dpi=200)
        plt.close()
        
        # 2. Stats Table
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.axis('off')
        plt.title("SEKTÖREL MEVSİMSEL YOY BÜYÜME İSTATİSTİKLERİ TABLOSU", fontsize=14, fontweight='bold', pad=15)
        
        # Format table data
        df_table_data = growth_df.copy()
        for col in ['Ortalama YoY Büyüme', 'Min YoY Büyüme', 'Maks YoY Büyüme', 'Standart Sapma']:
            df_table_data[col] = df_table_data[col].apply(lambda x: f"{x:.4f}")
            
        table = ax2.table(cellText=df_table_data.values, colLabels=df_table_data.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.0, 2.2)
        
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#27AE60')
            else:
                if c == 0: cell.set_facecolor('#EAF2F8')
                elif c == 1:
                    val_yoy = float(df_table_data.iloc[r-1, 1])
                    cell.set_facecolor('#EAFAF1' if val_yoy >= 0 else '#FDEDEC') # green/red depending on value
                else: cell.set_facecolor('white')
                
        plt.tight_layout()
        img_path2 = os.path.join(img_dir, f"8_Sektorel_Mevsimsel_YoY_Tablosu_{currency}.png")
        plt.savefig(img_path2, dpi=200)
        plt.close()
        
        print(f"[+] Mevsimsel YoY görselleri kaydedildi: {img_path1} ve {img_path2}")
    except Exception as e:
        print(f"Mevsimsel YoY görseli oluşturma hatası: {e}")
            
    print(f"[+] 8. Adım tamamlandı ve kaydedildi: {os.path.basename(output_path)}")

if __name__ == "__main__":
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("7_Final_Cari_Donem_Sektor_Kiyaslamasi_") and f.endswith(".xlsx")]
        if not files:
            print("Uyarı: İşlenecek veri dosyası bulunamadı!")
        else:
            for f_name in files:
                try:
                    run_seasonal_history_sector_comparison(f_name)
                except Exception as e:
                    print(f"Hata ({f_name}): {e}")
    else:
        print(f"Hata: Giriş klasörü bulunamadı: {INPUT_DIR}")
