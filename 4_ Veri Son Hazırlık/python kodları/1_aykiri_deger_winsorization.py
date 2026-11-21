import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats.mstats import winsorize

# --- YOLLAR ---
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PHASE3_DATA_DIR = os.path.join(BASE_PATH, "3_Özellik Seçimi", "raporlar", "6_Kur_Senkronizasyonu")
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")

OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "1_Adim_Aykiri_Temizlik")
IMG_DIR = os.path.join(PHASE4_BASE, "görseller")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def run_winsorization(input_file_name="6_Final_Veri_USD_Synced.xlsx"):
    currency = input_file_name.split("_")[3]
    
    input_path = os.path.join(PHASE3_DATA_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, "1_Aykiri_Temiz_Veri_" + currency + ".xlsx")
    report_path = os.path.join(OUT_DIR, "1_Aykiri_Deger_Raporu_" + currency + ".xlsx")

    print(f"\n[>>>] Aykırı Değer Temizliği Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    all_reports = []
    anomaly_summary = []
    outlier_details = []
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - İşleniyor: {sector}")
            df = pd.read_excel(xl, sector)
            
            id_cols = ['Dönem', 'Firma Adı']
            target_col = 'Net Dönem Karı/Zararı'
            feature_cols = [c for c in df.columns if c not in id_cols and c != target_col and pd.api.types.is_numeric_dtype(df[c])]
            
            total_obs = len(df)
            total_affected = 0
            df_cleaned = df.copy()
            
            for col in feature_cols:
                lower_limit = df[col].quantile(0.01)
                upper_limit = df[col].quantile(0.99)
                
                outlier_mask = (df[col] < lower_limit) | (df[col] > upper_limit)
                outlier_count = outlier_mask.sum()
                total_affected += outlier_count
                
                df_cleaned[col] = df[col].clip(lower=lower_limit, upper=upper_limit)
                
                all_reports.append({
                    "Sektör": sector,
                    "Özellik": col,
                    "Toplam Gözlem": total_obs,
                    "Aykırı Adet": outlier_count,
                    "Anomali Oranı (%)": round((outlier_count / total_obs) * 100, 2)
                })

                # Detaylı Değişim Logu (Eski vs Yeni Değerler)
                if outlier_count > 0:
                    outlier_df = df[outlier_mask].copy()
                    for idx, row in outlier_df.iterrows():
                        outlier_details.append({
                            "Sektör": sector,
                            "Firma Adı": row['Firma Adı'],
                            "Dönem": row['Dönem'],
                            "Özellik": col,
                            "Eski Değer": row[col],
                            "Yeni Değer": lower_limit if row[col] < lower_limit else upper_limit,
                            "Sınır": "Alt (%1)" if row[col] < lower_limit else "Üst (%99)"
                        })
            
            # Sektör özeti (Hücre bazlı)
            total_cells = total_obs * len(feature_cols)
            anomaly_summary.append({
                "Sektör": sector,
                "Toplam Hücre": total_cells,
                "Etkilenen Hücre": total_affected,
                "Ort. Anomali Oranı": f"{(total_affected / total_cells * 100):.2f}%"
            })
            
            df_cleaned.to_excel(writer, sheet_name=sector, index=False)

    # Raporu profesyonel çoklu sayfa formatında kaydet
    with pd.ExcelWriter(report_path, engine='openpyxl') as report_writer:
        # 1. Sayfa: Sektörel Özet (Hücre Bazlı)
        pd.DataFrame(anomaly_summary).to_excel(report_writer, sheet_name="Sektörel Özet", index=False)
        
        # 2. Sayfa: Detaylı Değişim Logu (Aykırı Değerlerin Eski-Yeni Halleri)
        if outlier_details:
            pd.DataFrame(outlier_details).to_excel(report_writer, sheet_name="Değişim Logu (Önce-Sonra)", index=False)
        else:
            pd.DataFrame([{"Bilgi": "Hiç aykırı değer bulunamadı."}]).to_excel(report_writer, sheet_name="Değişim Logu (Önce-Sonra)", index=False)
            
        # 3. Sayfa: Özellik Bazlı Detay
        pd.DataFrame(all_reports).to_excel(report_writer, sheet_name="Özellik Detayları", index=False)
    
    # --- GÖRSELLEŞTİRME (8 FARKLI GÖRSEL) ---
    STEP1_IMG_DIR = os.path.join(IMG_DIR, currency, "1_Aykiri_Temizlik")
    os.makedirs(STEP1_IMG_DIR, exist_ok=True)
    
    CUR_IMG_DIR = os.path.join(STEP1_IMG_DIR, "1_Aykiri_Raporlari")
    os.makedirs(CUR_IMG_DIR, exist_ok=True)
    
    # 1-7: Sektörel Özellik Bazlı Raporlar
    df_all = pd.DataFrame(all_reports)
    for i, sector in enumerate(xl.sheet_names, 1):
        df_sec = df_all[df_all["Sektör"] == sector][["Özellik", "Toplam Gözlem", "Aykırı Adet", "Anomali Oranı (%)"]]
        
        # Eğer çok fazla özellik varsa görseli uzat
        fig_height = len(df_sec) * 0.4 + 2
        fig, ax = plt.subplots(figsize=(12, fig_height))
        ax.axis('off')
        
        plt.title(f"AYKIRI DEĞER DETAY RAPORU: {sector} ({currency})", fontsize=14, fontweight='bold', pad=20)
        
        table = ax.table(cellText=df_sec.values, colLabels=df_sec.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.8)
        
        # Stil
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#2E86C1')
            else:
                cell.set_facecolor('#FBFCFC' if r % 2 == 0 else 'white')

        plt.tight_layout()
        plt.savefig(os.path.join(CUR_IMG_DIR, f"1_{i}_{sector}_Detay.png"), dpi=150, bbox_inches='tight')
        plt.close()

    # 8: Sektörel Özet Raporu (Hücre Bazlı)
    df_sum = pd.DataFrame(anomaly_summary)
    
    # Genel Toplam Satırı
    total_h = df_sum["Toplam Hücre"].sum()
    total_e = df_sum["Etkilenen Hücre"].sum()
    avg_anom = f"{(total_e / total_h * 100):.2f}%"
    
    new_row = pd.DataFrame([{"Sektör": "GENEL TOPLAM", "Toplam Hücre": total_h, "Etkilenen Hücre": total_e, "Ort. Anomali Oranı": avg_anom}])
    df_sum = pd.concat([df_sum, new_row], ignore_index=True)

    # 1. Bar Chart: Sektörlere Göre Aykırı Değer Oranları
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    df_plot_anom = pd.DataFrame(anomaly_summary)
    df_plot_anom['Rate'] = df_plot_anom['Ort. Anomali Oranı'].str.replace('%','').astype(float)
    
    sns.barplot(data=df_plot_anom, x='Sektör', y='Rate', palette='Blues_d', ax=ax1)
    ax1.set_title(f"Sektörlere Göre Hücre Bazlı Ortalama Aykırı Değer Oranı (%) - {currency}", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Sektör", fontsize=11)
    ax1.set_ylabel("Ortalama Aykırı Oranı (%)", fontsize=11)
    ax1.set_xticklabels(df_plot_anom['Sektör'], rotation=15, ha='right')
    ax1.grid(True, axis='y', linestyle='--', alpha=0.5)
    for p in ax1.patches:
        val = p.get_height()
        if pd.notna(val):
            ax1.annotate(f"{val:.2f}%", (p.get_x() + p.get_width() / 2., val),
                         ha='center', va='bottom', xytext=(0, 3), textcoords='offset points', fontsize=10, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(STEP1_IMG_DIR, "1_Aykiri_Sektorel_Oranlari.png"), dpi=200, bbox_inches='tight')
    plt.close()

    # 2. Table: Aykırı Değer Sektörel Özet Tablosu
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.axis('off')
    plt.title(f"AYKIRI DEĞER SEKTÖREL ÖZET RAPORU ({currency})", fontsize=14, fontweight='bold', pad=20)
    
    table = ax2.table(cellText=df_sum.values, colLabels=df_sum.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 2.2)
    
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#1B4F72')
        elif r == len(df_sum): # Genel Toplam
            cell.set_text_props(weight='bold')
            cell.set_facecolor('#D4E6F1')
        else:
            cell.set_facecolor('white')

    # Alt Not
    note_text = "NOT: Aykırı değerler %1 alt ve %99 üst eşik değerleri ile sınırlandırılarak (Winsorization) veri seti stabilize edilmiştir.\nBu işlem veri silmez, uç değerleri eşik değerlere çeker. %10 sınırının çok altında kalınmıştır."
    plt.figtext(0.5, 0.05, note_text, ha="center", fontsize=11, fontstyle='italic', color='#5D6D7E',
                bbox={"facecolor":"white", "alpha":0.8, "pad":5, "edgecolor":"#1B4F72", "linewidth":1})

    plt.savefig(os.path.join(STEP1_IMG_DIR, "1_Aykiri_Sektorel_Ozet_Raporu.png"), dpi=200, bbox_inches='tight')
    plt.close()

    print(f"[+] 8 Adet durum raporu görseli oluşturuldu: {CUR_IMG_DIR}")

    print(f"[+] Temiz veri kaydedildi: {os.path.basename(output_path)}")
    print(f"[+] Aykırı değer raporu oluşturuldu: {os.path.basename(report_path)}")

if __name__ == "__main__":
    # Tüm para birimleri için çalıştır
    currencies = ["USD", "TRY", "EUR"]
    for curr in currencies:
        file_name = f"6_Final_Veri_{curr}_Synced.xlsx"
        run_winsorization(file_name)
