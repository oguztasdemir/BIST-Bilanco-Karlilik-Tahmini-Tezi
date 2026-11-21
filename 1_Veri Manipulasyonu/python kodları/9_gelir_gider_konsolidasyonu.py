import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import textwrap

# --- YOLLAR ---
BASE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")

import sys
CURRENCY = ""
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.upper() in ["USD", "EUR", "TRY"]:
            CURRENCY = arg.upper()
            break

temp_data_path = os.path.join(BASE_PATH, "raporlar", "7_Final_Veri", f"Veri_Havuzu_{CURRENCY}.xlsx" if CURRENCY else "Veri_Havuzu.xlsx")
if os.path.exists(temp_data_path):
    INPUT_XLSX = temp_data_path
else:
    # Fallback
    INPUT_XLSX = os.path.join(BASE_PATH, "raporlar", "7_Final_Veri", "Final_Veri_Havuzu.xlsx")

SUSPECT_XLSX = os.path.join(BASE_PATH, "raporlar", "8_Dogrulama_Analizi", "8_Supheli_Benzerlik_Listesi.xlsx")

OUT_DIR = os.path.join(BASE_PATH, "raporlar", "9_Gelir_Gider_Konsolidasyonu")
IMG_DIR = os.path.join(BASE_PATH, "görseller", "9_Konsolidasyon")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def wrap_text(text, width=20):
    return textwrap.fill(str(text), width)

def shorten_name(col1, col2, op):
    c1, c2 = str(col1), str(col2)
    words1, words2 = c1.split(), c2.split()
    common = []
    for w1, w2 in zip(words1, words2):
        if w1 == w2: common.append(w1)
        else: break
    if common:
        prefix = " ".join(common)
        return f"{prefix} {words1[len(common)] if len(words1)>len(common) else ''} {op} {words2[len(common)] if len(words2)>len(common) else ''}"
    return f"{c1[:15]}.. {op} {c2[:15]}.."

def save_df_as_image(df, title, path):
    if df.empty: return
    plot_df = df.copy()
    for col in plot_df.columns:
        if plot_df[col].dtype == 'object':
            plot_df[col] = plot_df[col].apply(lambda x: wrap_text(x, width=20))
    fig_height = len(plot_df) * 1.5 + 2
    plt.figure(figsize=(24, fig_height))
    plt.axis('off')
    plt.title(title, fontsize=24, fontweight='bold', pad=50)
    table = plt.table(cellText=plot_df.values, colLabels=plot_df.columns, cellLoc='center', loc='center',
                      colColours=["#212F3D"]*len(plot_df.columns), cellColours=[["#FBFCFC"]*len(plot_df.columns)]*len(plot_df))
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 5.5)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()

def run_step9_rich_viz():
    print("\n" + "="*60)
    print("   STEP 9: ZENGİN GÖRSELLEŞTİRME VE KONSOLİDASYON")
    print("="*60)

    suspect_df = pd.read_excel(SUSPECT_XLSX)
    xl = pd.ExcelFile(INPUT_XLSX)
    
    INC_WORDS = ['GELIR', 'HASILAT', 'KAR', 'SATIS']
    EXP_WORDS = ['GIDER', 'MALIYET', 'ZARAR']
    EXC_WORDS = ['DONEN', 'DURAN']

    consolidation_results = []
    sector_comparison = []

    out_file_name = f"9_Gelir_Gider_Birlesik_Havuz_{CURRENCY}.xlsx" if CURRENCY else "9_Gelir_Gider_Birlesik_Havuz.xlsx"
    final_writer_path = os.path.join(OUT_DIR, out_file_name)

    with pd.ExcelWriter(final_writer_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"Sektör: {sector}")
            df = pd.read_excel(xl, sheet_name=sector)
            
            # --- ÖNCESİ ---
            before_fr = (df.notna().sum().sum() / df.size) * 100
            
            sector_suspects = suspect_df[suspect_df['Sektör'] == sector]
            for _, row in sector_suspects.iterrows():
                col1, col2 = row['Özellik 1'], row['Özellik 2']
                if col1 not in df.columns or col2 not in df.columns: continue
                
                c1_up, c2_up = str(col1).upper(), str(col2).upper()
                if any(w in c1_up or w in c2_up for w in (INC_WORDS + EXP_WORDS)) and not any(w in c1_up or w in c2_up for w in EXC_WORDS):
                    is_c1_exp = any(w in c1_up for w in EXP_WORDS)
                    is_c2_exp = any(w in c2_up for w in EXP_WORDS)
                    
                    if is_c1_exp and not is_c2_exp:
                        combined = df[col2].fillna(0) - df[col1].fillna(0); op = "-"
                    elif is_c2_exp and not is_c1_exp:
                        combined = df[col1].fillna(0) - df[col2].fillna(0); op = "-"
                    else:
                        # Eğer her ikisi de kâr/gelir ise (Örn: Sürdürülen + Durdurulan) topla
                        combined = df[col1].fillna(0) + df[col2].fillna(0); op = "+"
                    
                    combined.loc[df[col1].isna() & df[col2].isna()] = np.nan
                    real_new_name = f"{col1} {op} {col2} NET"
                    df[real_new_name] = combined
                    
                    fr1, fr2 = round(df[col1].notna().mean() * 100, 1), round(df[col2].notna().mean() * 100, 1)
                    fr_new = round(df[real_new_name].notna().mean() * 100, 1)
                    
                    consolidation_results.append({
                        "Sektör": sector.replace('_', ' '),
                        "Yeni Kalem": shorten_name(col1, col2, op),
                        "Kalem 1": col1, "Kalem 2": col2,
                        "K1 %": fr1, "K2 %": fr2, "Yeni %": fr_new
                    })
                    df.drop([col1, col2], axis=1, inplace=True)

            # --- SONRASI ---
            after_fr = (df.notna().sum().sum() / df.size) * 100
            sector_comparison.append({"Sektör": sector, "Zaman": "Öncesi", "Doluluk": before_fr})
            sector_comparison.append({"Sektör": sector, "Zaman": "Sonrası", "Doluluk": after_fr})
            df.to_excel(writer, sheet_name=sector, index=False)
            
    # --- YENİ: HIZLANDIRILMIŞ HÜCRE BOYAMA (SARI) ---
    print("  [!] Konsolide edilen hücreler hızla sarıya boyanıyor...")
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill
    yellow_fill = PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid")
    
    wb = load_workbook(final_writer_path)
    for sector in xl.sheet_names:
        ws = wb[sector]
        headers = [c.value for c in ws[1]]
        # Hangi sütunlar "NET" takısı almışsa (Adım 9'da oluşturulanlar) o sütunları boya
        for c_idx, header in enumerate(headers, 1):
            if " NET" in str(header):
                # Sütundaki tüm dolu hücreleri boya (Daha hızlı)
                for r_idx in range(2, ws.max_row + 1):
                    cell = ws.cell(row=r_idx, column=c_idx)
                    if cell.value is not None:
                        cell.fill = yellow_fill
    wb.save(final_writer_path)

    # --- GÖRSEL 1: TABLO ---
    report_df = pd.DataFrame(consolidation_results)
    save_df_as_image(report_df, "Step 9: Gelir-Gider Konsolidasyon Analizi", os.path.join(IMG_DIR, f"9_Birlestirme_Tablo_Gorsel_{CURRENCY}.png" if CURRENCY else "9_Birlestirme_Tablo_Gorsel.png"))

    # --- GÖRSEL 2: SEKTÖREL ÖNCESİ-SONRASI ---
    plt.figure(figsize=(14, 8))
    sns.set_style("whitegrid")
    comp_df = pd.DataFrame(sector_comparison)
    ax = sns.barplot(data=comp_df, x="Sektör", y="Doluluk", hue="Zaman", palette={"Öncesi": "#BDC3C7", "Sonrası": "#27AE60"})
    plt.title("Sektör Bazlı Genel Doluluk Oranı Değişimi", fontsize=18, fontweight='bold')
    plt.xticks(rotation=25, ha='right')
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}%', (p.get_x() + p.get_width() / 2., p.get_height()), ha='center', va='center', xytext=(0, 9), textcoords='offset points', fontsize=10, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, "9_Sektorel_Kiyas_Genel.png"), dpi=300)
    plt.close()

    # --- GÖRSEL 3: ÇİFT BAZLI KAZANÇ (BONUS) ---
    if not report_df.empty:
        plt.figure(figsize=(16, 10))
        # Her birleşen çift için K1, K2 ve Yeni Dolulukları kıyasla
        melted_df = report_df.melt(id_vars=["Yeni Kalem"], value_vars=["K1 %", "K2 %", "Yeni %"], var_name="Tip", value_name="Doluluk")
        ax = sns.barplot(data=melted_df, x="Yeni Kalem", y="Doluluk", hue="Tip", palette="viridis")
        plt.title("Kalem Bazlı Konsolidasyon Kazanç Analizi", fontsize=18, fontweight='bold')
        plt.xticks(rotation=35, ha='right')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(os.path.join(IMG_DIR, "9_Kalem_Bazli_Kazanc.png"), dpi=300)
        plt.close()

    # --- GÖRSEL 4: SEKTÖREL BİRLEŞME SAYILARI ---
    plt.figure(figsize=(10, 6))
    report_df["Sektör"].value_vars = report_df["Sektör"].value_counts().plot(kind='pie', autopct='%1.1f%%', colors=sns.color_palette("pastel"), shadow=True, startangle=140)
    plt.title("Sektörlere Göre Konsolide Edilen Kalem Dağılımı", fontsize=16, fontweight='bold')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig(os.path.join(IMG_DIR, "9_Sektorel_Dagitim_Pie.png"), dpi=300)
    plt.close()

    print("\n" + "="*80)
    print("Zengin görselleştirme tamamlandı. 4 farklı grafik oluşturuldu.")
    print("="*80)

if __name__ == "__main__":
    run_step9_rich_viz()
