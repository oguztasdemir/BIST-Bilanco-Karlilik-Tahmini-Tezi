import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns

# --- YOLLAR ---
BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection\1_Veri Manipulasyonu"

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break

OUT_DIR = os.path.join(BASE_PATH, "raporlar", "12_Feature_Takip")
IMG_DIR = os.path.join(BASE_PATH, "görseller", "12_Feature_Takip")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# Karşılaştırılacak Dosyalar
STEPS = [
    {"Ad": "1. Ham Veri", "Yol": os.path.join(BASE_PATH, "0_Datasetler", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu.xlsx")},
    {"Ad": "2. Birleştirilmiş", "Yol": os.path.join(BASE_PATH, "raporlar", "3_Veri Birlestirme", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu.xlsx")},
    {"Ad": "3. Filtrelenmiş (%70)", "Yol": os.path.join(BASE_PATH, "raporlar", "7_Final_Veri", f"Final_Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Final_Veri_Havuzu.xlsx")},
    {"Ad": "4. Konsolide (Final)", "Yol": os.path.join(BASE_PATH, "raporlar", "9_Gelir_Gider_Konsolidasyonu", f"9_Gelir_Gider_Birlesik_Havuz_{CURRENCY}.xlsx" if CURRENCY else "9_Gelir_Gider_Birlesik_Havuz.xlsx")}
]

def is_id_col(col_name):
    n = str(col_name).upper()
    keywords = ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY']
    return any(k in n for k in keywords)

def run_feature_tracking():
    print("\n" + "="*60)
    print("   ADIM 12: FEATURE (ÖZELLİK) TAKİP VE ELEME RAPORU")
    print("="*60)

    all_data = []

    for step in STEPS:
        name = step["Ad"]
        path = step["Yol"]
        
        if not os.path.exists(path):
            print(f"  [!] Uyarı: {name} dosyası henüz oluşturulmamış, atlanıyor.")
            continue
            
        print(f"  Analiz Ediliyor: {name}")
        xl = pd.ExcelFile(path)
        for sector in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sector)
            # ID olmayan sütunları say
            features = [c for c in df.columns if not is_id_col(c)]
            feature_count = len(features)
            
            all_data.append({
                "Aşama": name,
                "Sektör": sector,
                "Feature Sayısı": feature_count
            })

    if not all_data:
        print("Hata: Hiçbir veri toplanamadı.")
        return

    df_report = pd.DataFrame(all_data)
    
    # 1. EXCEL RAPORU
    report_name = f"12_Feature_Degisim_Raporu_{CURRENCY}.xlsx" if CURRENCY else "12_Feature_Degisim_Raporu.xlsx"
    report_path = os.path.join(OUT_DIR, report_name)
    df_report.pivot(index="Sektör", columns="Aşama", values="Feature Sayısı").to_excel(report_path)
    print(f"\n[+] Excel Raporu Kaydedildi: {report_path}")

    # 2. GÖRSELLEŞTİRME (Sektör Bazlı Değişim)
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(15, 8))
    
    # Çizgi Grafiği (Trend)
    ax = sns.lineplot(data=df_report, x="Aşama", y="Feature Sayısı", hue="Sektör", marker="o", linewidth=3, markersize=10)
    
    plt.title("Aşamalara Göre Özellik (Feature) Sayısındaki Değişim", fontsize=16, fontweight='bold', pad=20)
    plt.ylabel("Özellik Sayısı", fontsize=12)
    plt.xlabel("İşlem Aşamaları", fontsize=12)
    plt.legend(title="Sektörler", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Değerleri noktalara yaz
    for i in range(len(df_report)):
        plt.text(df_report.iloc[i]["Aşama"], df_report.iloc[i]["Feature Sayısı"] + 2, 
                 str(df_report.iloc[i]["Feature Sayısı"]), ha='center', fontsize=9, fontweight='bold')

    plt.tight_layout()
    img_name = f"12_Feature_Degisim_Trendi_{CURRENCY}.png" if CURRENCY else "12_Feature_Degisim_Trendi.png"
    img_path = os.path.join(IMG_DIR, img_name)
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Trend Grafiği Oluşturuldu: {img_path}")

    print("\n" + "="*60)
    print("ADIM 12 TAMAMLANDI")
    print("="*60)

if __name__ == "__main__":
    run_feature_tracking()
