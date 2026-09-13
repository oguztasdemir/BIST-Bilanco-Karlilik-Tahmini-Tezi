import os
import sys
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ============================================================
#   ADIM 8: OTONOM ÖZELLİK SEÇİM ZİNCİRİ VE ANALİTİK RAPORLAMA
# ============================================================

BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection\3_Özellik Seçimi"
PHASE2_OUT_DIR = r"c:\Users\User\Desktop\Tez Feature Selection\2_Kur Hesaplama ve Veriyi Hazırlama\çıktılar\3_Zaman_Serisi_Final"
SCRIPTS_DIR = os.path.join(BASE_PATH, "python kodları")
OUT_DIR = os.path.join(BASE_PATH, "raporlar", "8_Feature_Selection_Analizi")
IMG_DIR = os.path.join(BASE_PATH, "görseller", "8_Analiz_Grafikleri")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def run_script(script_name):
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    print(f"\n  [>>>] Başlatılıyor: {script_name}")
    result = subprocess.run([sys.executable, script_path])
    return result.returncode == 0

def generate_master_reporting():
    print("\n" + "="*70)
    print("   ADIM 8: OTONOM ÖZELLİK SEÇİM ZİNCİRİ VE ANALİTİK RAPORLAMA")
    print("="*70)

    # 1. Verileri Topla (Adım 1, 2, 3 raporlarından)
    # Not: Bu aşamada raporların var olduğunu varsayıyoruz
    steps = {
        "Başlangıç": os.path.join(PHASE2_OUT_DIR, "Final_Veri_USD_USD_Indexed.xlsx"),
        "Varyans Filtresi": os.path.join(BASE_PATH, "raporlar", "1_Varyans_Filtresi", "1_Varyans_Filtreli_Veri.xlsx"),
        "Pearson Filtresi": os.path.join(BASE_PATH, "raporlar", "2_Pearson_Analizleri", "2_Pearson_Filtreli_Veri.xlsx"),
        "VIF (Final)": os.path.join(BASE_PATH, "raporlar", "3_VIF_Analizleri", "3_VIF_Filtreli_Veri.xlsx")
    }

    feature_counts = []
    sector_feature_map = {} # Sektör -> Set(Features)

    for step_name, path in steps.items():
        if os.path.exists(path):
            xl = pd.ExcelFile(path)
            counts = []
            for sheet in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet)
                # ID kolonlarını çıkar
                cols = [c for c in df.columns if not any(k in str(c).upper() for k in ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY'])]
                counts.append(len(cols))
                
                if step_name == "VIF (Final)":
                    sector_feature_map[sheet] = set(cols)
            
            feature_counts_by_sector = [] # List of dicts: {Sektör, Aşama, Sayı}
    sector_final_features = {} # Sektör -> List(Final Features)

    for step_name, path in steps.items():
        if os.path.exists(path):
            xl = pd.ExcelFile(path)
            for sheet in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet)
                cols = [c for c in df.columns if not any(k in str(c).upper() for k in ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY'])]
                
                feature_counts_by_sector.append({
                    "Sektör": sheet,
                    "Aşama": step_name,
                    "Sayı": len(cols)
                })
                
                if step_name == "VIF (Final)":
                    sector_final_features[sheet] = cols

    # --- 1. SEKTÖR BAZLI TREND GRAFİKLERİ ---
    df_trends = pd.DataFrame(feature_counts_by_sector)
    for sector in df_trends["Sektör"].unique():
        sector_df = df_trends[df_trends["Sektör"] == sector]
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=sector_df, x="Aşama", y="Sayı", palette="viridis")
        plt.title(f"{sector} Sektörü Özellik Eleme Süreci", fontsize=14, fontweight='bold')
        for p in ax.patches:
            ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', fontsize=12, color='black', xytext=(0, 5), textcoords='offset points')
        plt.tight_layout()
        plt.savefig(os.path.join(IMG_DIR, f"8_Trend_{sector}.png"), dpi=300)
        plt.close()

    # --- 2. SEKTÖR BAZLI ÖZELLİK TABLOLARI (GÖRSEL) ---
    for sector, features in sector_final_features.items():
        if not features: continue
        
        # Özellikleri listele
        f_df = pd.DataFrame(features, columns=["Seçilen Özellikler (Final)"])
        
        fig, ax = plt.subplots(figsize=(8, len(features)*0.3 + 1))
        ax.axis('off')
        table = ax.table(cellText=f_df.values, colLabels=f_df.columns, loc='center', cellLoc='left')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)
        
        # Başlık sütununu renklendir
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#2E86C1')
        
        plt.title(f"{sector} Sektörü Final Özellik Listesi", fontsize=14, fontweight='bold', pad=20)
        plt.savefig(os.path.join(IMG_DIR, f"8_Tablo_{sector}.png"), dpi=300, bbox_inches='tight')
        plt.close()

    # --- 3. MASTER ISI HARİTASI (ÖNCEKİ MANTIK) ---
    all_final_features = sorted(list(set().union(*sector_final_features.values())))
    matrix_data = []
    for sector, features in sector_final_features.items():
        row = {"Sektör": sector}
        for f in all_final_features:
            row[f] = 1 if f in features else 0
        matrix_data.append(row)
    
    df_matrix = pd.DataFrame(matrix_data).set_index("Sektör")
    df_matrix.to_excel(os.path.join(OUT_DIR, "8_Sektorel_Ozellik_Matrisi.xlsx"))

    plt.figure(figsize=(24, 12))
    sns.heatmap(df_matrix, cmap="YlGnBu", cbar=False, linewidths=0.5, linecolor='lightgray')
    plt.title("Sektör Bazlı Kullanılan Özellikler Matrisi (Final)", fontsize=18, fontweight='bold', pad=20)
    plt.xticks(rotation=90, ha='center', fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, "8_Master_Heatmap.png"), dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n[+] Sektörel Analizler ve Tablolar Tamamlandı: {IMG_DIR}")

def main():
    # 1-6 arasındaki tüm adımları sırasıyla çalıştır (Otomasyon)
    scripts = [
        "1_varyans_esigi_filtresi.py",
        "2_hedef_pearson_filtresi.py",
        "3_coklu_dogrusallik_vif_filtresi.py",
        "4_final_ozellik_sozlugu.py",
        "5_final_tablo_gorsellestirme.py",
        "6_kur_oznitelik_senkronizasyonu.py",
        "7_doluluk_orani_gorsellestirme.py"
    ]

    print("\n>>> ÖZELLİK SEÇİMİ OTOMASYON ZİNCİRİ BAŞLATILIYOR <<<")
    for s in scripts:
        if not run_script(s):
            print(f"\n[!] Durduruldu: {s} başarısız.")
            return

    # Master Raporlamayı Yap
    generate_master_reporting()

if __name__ == "__main__":
    main()
