import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from openpyxl.utils import get_column_letter

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
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "8_Adim_Mevsimsel_Gecmis_Sektor_Kiyaslamasi")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "9_Adim_Sektorel_Akran_Kiyaslama")
os.makedirs(OUT_DIR, exist_ok=True)

def run_peer_benchmarking(input_file_name):
    currency = input_file_name.split("_")[-1].replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, f"9_Final_Sektorel_Akran_Kiyaslama_{currency}.xlsx")
    separate_summary_path = os.path.join(OUT_DIR, f"Veri_Kumesi_Genel_Ozeti_{currency}.xlsx")

    print(f"\n[>>>] 9. Adım: Sektörel Akran Kıyaslama Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    
    # Görselleştirme Klasörünü Hazırla
    img_dir = os.path.join(PHASE4_BASE, "görseller", currency, "9_Akran_Kiyas")
    os.makedirs(img_dir, exist_ok=True)

    sector_dfs = {}
    summary_rows = []
    plot_data_list = []
    
    # 1. Her Sektörü Oku ve İşle
    for sector in xl.sheet_names:
        print(f"  - İşleniyor (Akran Kıyaslama): {sector}")
        df = pd.read_excel(xl, sector)
        
        df.columns = [c.strip() for c in df.columns]
        
        f_col = 'Firma Adı' if 'Firma Adı' in df.columns else [c for c in df.columns if 'FIRMA' in c.upper()][0]
        d_col = 'Dönem' if 'Dönem' in df.columns else [c for c in df.columns if 'DONEM' in c.upper()][0]
        p_col = 'Net Dönem Karı/Zararı' if 'Net Dönem Karı/Zararı' in df.columns else [c for c in df.columns if 'KAR' in c.upper() or 'ZARAR' in c.upper()][0]
        new_col = 'Net Dönem Karı (t+1)' if 'Net Dönem Karı (t+1)' in df.columns else [c for c in df.columns if 't+1' in c.lower()][0]

        # Sadece o döneme (t) ait sektörel akran karşılaştırmaları eklenir. Gelecek (t+1) verisi eklenmez.
        df['Sektör Medyan Gerçek Net Kârı'] = df.groupby(d_col)[p_col].transform('median')
        df['Sektör Üstü Performans (Gerçek)'] = (df[p_col] > df['Sektör Medyan Gerçek Net Kârı']).astype(int)
        
        # Kolon Sıralaması Revizyonu: Net Dönem Karı ve t+1 en sağda olmalı
        cols = list(df.columns)
        target_curr = p_col
        target_lead = new_col
        
        if target_curr in cols: cols.remove(target_curr)
        if target_lead and target_lead in cols: cols.remove(target_lead)
        
        cols.append(target_curr)
        if target_lead:
            cols.append(target_lead)
            
        df = df[cols]
        sector_dfs[sector] = df
        
        # Özet Raporu İstatistikleri
        unique_firms = df[f_col].nunique()
        total_rows = len(df)
        min_period = df[d_col].min()
        max_period = df[d_col].max()
        outperform_pct = df['Sektör Üstü Performans (Gerçek)'].mean() * 100
        
        summary_rows.append({
            'Sektör Adı': sector,
            'Benzersiz Firma Sayısı': unique_firms,
            'Toplam Gözlem (Satır)': total_rows,
            'Başlangıç Dönemi': f"{min_period}. Dönem",
            'Bitiş Dönemi': f"{max_period}. Dönem",
            'Sektör Üstü Performans Oranı (%)': round(outperform_pct, 2)
        })

        # Görsel Grafik İçin Performans Verisi Topla
        p_counts = df['Sektör Üstü Performans (Gerçek)'].value_counts().reset_index()
        p_counts.columns = ['Durum', 'Adet']
        p_counts['Durum'] = p_counts['Durum'].map({0: 'Sektör Altı / Eşit', 1: 'Sektör Üstü Performans'})
        p_counts['Sektör'] = sector
        plot_data_list.append(p_counts)

    # 2. Genel Özet Veri Çerçevesini Oluştur
    summary_df = pd.DataFrame(summary_rows)
    
    # Toplam Satırı Ekle
    total_row = pd.DataFrame([{
        'Sektör Adı': 'TOPLAM / ORTALAMA',
        'Benzersiz Firma Sayısı': summary_df['Benzersiz Firma Sayısı'].sum(),
        'Toplam Gözlem (Satır)': summary_df['Toplam Gözlem (Satır)'].sum(),
        'Başlangıç Dönemi': '-',
        'Bitiş Dönemi': '-',
        'Sektör Üstü Performans Oranı (%)': round(summary_df['Sektör Üstü Performans Oranı (%)'].mean(), 2)
    }])
    summary_df = pd.concat([summary_df, total_row], ignore_index=True)

    # Ayrı Excel Dosyasına Yaz (Sadece Özet Raporu)
    with pd.ExcelWriter(separate_summary_path, engine='openpyxl') as summary_writer:
        summary_df.to_excel(summary_writer, sheet_name='Veri Kümesi Genel Özeti', index=False)
        worksheet = summary_writer.sheets['Veri Kümesi Genel Özeti']
        for col in worksheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
            worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 3. Excel Dosyasına Kaydet (Sadece Sektör Sayfaları)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sektörel Sayfalar
        for sector, df in sector_dfs.items():
            df.to_excel(writer, sheet_name=sector, index=False)
            
        # Sütun Genişliklerini Otomatik Ayarla
        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            for col in worksheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # 4. Görsel Rapor Oluştur (Sektörel Akran Karşılaştırma Dağılımı + Tablo)
    try:
        plot_df = pd.concat(plot_data_list)
        
        # 1. Bar plot
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        sns.barplot(data=plot_df, x='Sektör', y='Adet', hue='Durum', palette='Set1', ax=ax1)
        
        # Barların üzerine tam sayısal değerleri ekle
        for p in ax1.patches:
            height = p.get_height()
            if pd.notna(height) and height > 0:
                ax1.annotate(f"{int(height)}", 
                            (p.get_x() + p.get_width() / 2., height),
                            ha='center', va='center', 
                            xytext=(0, 6), 
                            textcoords='offset points', 
                            fontsize=9, fontweight='bold', color='black')
        
        ax1.set_title(f"Sektörlere Göre Akran Üstü Performans Dağılımları ({currency})", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Sektör", fontsize=11)
        ax1.set_ylabel("Gözlem (Satır) Sayısı", fontsize=11)
        ax1.set_xticklabels(plot_df['Sektör'].unique(), rotation=15, ha='right')
        ax1.legend(title='Durum Raporu')
        ax1.grid(True, axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        img_path1 = os.path.join(img_dir, f"9_Akran_Performans_Dagilimi_{currency}.png")
        plt.savefig(img_path1, dpi=200)
        plt.close()
        
        # 2. Summary Table
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.axis('off')
        plt.title("VERİ KÜMESİ GENEL ÖZETİ VE AKRAN PERFORMANS TABLOSU", fontsize=14, fontweight='bold', pad=15)
        
        table = ax2.table(cellText=summary_df.values, colLabels=summary_df.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.0, 2.0)
        
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#A93226')
            elif r == len(summary_df): # Total/Average row
                cell.set_text_props(weight='bold')
                cell.set_facecolor('#F2D7D5')
            else:
                if c == 0: cell.set_facecolor('#FDEDEC')
                else: cell.set_facecolor('white')
                
        plt.tight_layout()
        img_path2 = os.path.join(img_dir, f"9_Akran_Performans_Ozet_Tablosu_{currency}.png")
        plt.savefig(img_path2, dpi=200)
        plt.close()
        
        print(f"[+] Akran kıyas görselleri kaydedildi: {img_path1} ve {img_path2}")
    except Exception as e:
        print(f"Akran kıyas görseli oluşturma hatası: {e}")
            
    print(f"[+] 9. Adım tamamlandı ve özet kapak sayfasıyla kaydedildi: {os.path.basename(output_path)}")
    print(f"[+] Bağımsız genel özet dosyası kaydedildi: {os.path.basename(separate_summary_path)}")

if __name__ == "__main__":
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("8_Final_Mevsimsel_Gecmis_Sektor_Kiyaslamasi_") and f.endswith(".xlsx")]
        if not files:
            print("Uyarı: İşlenecek veri dosyası bulunamadı!")
        else:
            for f_name in files:
                try:
                    run_peer_benchmarking(f_name)
                except Exception as e:
                    print(f"Hata ({f_name}): {e}")
