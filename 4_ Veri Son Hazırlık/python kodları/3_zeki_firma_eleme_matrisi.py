import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# --- YOLLAR ---
BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection"
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "2_Adim_Hedef_Kaydirma")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "3_Adim_Zeki_Eleme")
IMG_DIR = os.path.join(PHASE4_BASE, "görseller")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def run_firm_filtering(input_file_name="2_Hedef_Kaydirilmis_Veri_USD.xlsx"):
    currency = input_file_name.split("_")[4].replace(".xlsx", "")
    
    # Alt klasör yolları (sadece görseller için)
    CUR_IMG_DIR = os.path.join(IMG_DIR, currency, "3_Zeki_Eleme")
    os.makedirs(CUR_IMG_DIR, exist_ok=True)
    
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, "3_Final_Filtreli_Veri_" + currency + ".xlsx")
    
    print(f"\n[>>>] Zeki Firma Eleme Karar Destek Matrisi Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    thresholds = [4, 8, 12, 16, 20, 24, 28, 32]
    
    matrix_data = []
    sector_optimal_thresholds = {}
    
    all_sector_dfs = {}
    
    # Toplamları tutmak için
    total_sil = {t: 0 for t in thresholds}
    total_kal = {t: 0 for t in thresholds}
    grand_total_firms = 0

    for sector in xl.sheet_names:
        df = pd.read_excel(xl, sector)
        all_sector_dfs[sector] = df
        
        firm_counts = df.groupby('Firma Adı')['Dönem'].count()
        total_firms_start = len(firm_counts)
        grand_total_firms += total_firms_start
        
        row = {"Sektör (Başlangıç)": f"{sector}\n({total_firms_start} Firma)"}
        
        best_score = -1
        optimal_t = thresholds[0]
        
        for t in thresholds:
            keep_firms = firm_counts[firm_counts >= t].index
            sil_count = total_firms_start - len(keep_firms)
            kal_count = len(keep_firms)
            
            row[f"{t} Dönem\n[SİL | KAL]"] = f"{sil_count}  |  {kal_count}"
            
            # Toplamlara ekle
            total_sil[t] += sil_count
            total_kal[t] += kal_count
            
            score = kal_count * (t ** 1.2)
            if score >= best_score:
                best_score = score
                optimal_t = t
        
        matrix_data.append(row)
        sector_optimal_thresholds[sector] = optimal_t

    # --- TOPLAM SATIRI EKLE (8. SATIR) ---
    total_row = {"Sektör (Başlangıç)": f"GENEL TOPLAM\n({grand_total_firms} Firma)"}
    for t in thresholds:
        col_name = f"{t} Dönem\n[SİL | KAL]"
        total_row[col_name] = f"{total_sil[t]}  |  {total_kal[t]}"
    matrix_data.append(total_row)

    # Karma Optimal Hesapla
    karma_sil = 0
    karma_kal = 0
    for sector, t_opt in sector_optimal_thresholds.items():
        df = all_sector_dfs[sector]
        f_counts = df.groupby('Firma Adı')['Dönem'].count()
        total_firms_s = len(f_counts)
        k_firms = f_counts[f_counts >= t_opt].index
        karma_sil += (total_firms_s - len(k_firms))
        karma_kal += len(k_firms)

    # --- KARMA OPTİMAL SATIRI EKLE (9. SATIR) ---
    karma_row = {"Sektör (Başlangıç)": "KARMA OPTİMAL TOPLAM\n(Sarı Hücrelerin Toplamı)"}
    for t in thresholds[:-1]:
        karma_row[f"{t} Dönem\n[SİL | KAL]"] = "-"
    karma_row[f"{thresholds[-1]} Dönem\n[SİL | KAL]"] = f"{karma_sil}  |  {karma_kal}"
    matrix_data.append(karma_row)

    # --- MATRİS GÖRSELLEŞTİRME ---
    df_matrix = pd.DataFrame(matrix_data)
    
    # 1. Bar Chart: Karma Optimal Seçim Sonuçları
    fig1, ax1 = plt.subplots(figsize=(15, 8))
    optimal_plot_data = []
    for sector, t_opt in sector_optimal_thresholds.items():
        df_sec = all_sector_dfs[sector]
        f_counts = df_sec.groupby('Firma Adı')['Dönem'].count()
        tot_start = len(f_counts)
        keep = len(f_counts[f_counts >= t_opt])
        deleted = tot_start - keep
        optimal_plot_data.append({
            "Sektör": sector,
            "Kalan": keep,
            "Giden": deleted,
            "Eşik (Dönem)": t_opt
        })
    df_opt = pd.DataFrame(optimal_plot_data)
    
    bars_keep = ax1.bar(df_opt['Sektör'], df_opt['Kalan'], label='Kalan Firmalar (Filtreyi Geçen)', color='#27AE60', alpha=0.8)
    bars_gid = ax1.bar(df_opt['Sektör'], df_opt['Giden'], bottom=df_opt['Kalan'], label='Giden Firmalar (Elenen)', color='#E74C3C', alpha=0.8)
    
    ax1.set_title(f"Sektörlere Göre Karma Optimal Seçim Sonuçları (Kalan vs Giden Firmalar) - {currency}", fontsize=15, fontweight='bold', pad=15)
    ax1.set_xlabel("Sektör", fontsize=12)
    ax1.set_ylabel("Firma Sayısı", fontsize=12)
    ax1.set_xticklabels(df_opt['Sektör'], rotation=15, ha='right', fontsize=10)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    for bk, bg, (_, r_data) in zip(bars_keep, bars_gid, df_opt.iterrows()):
        hk = bk.get_height()
        hg = bg.get_height()
        ax1.annotate(f"{int(hk)}", (bk.get_x() + bk.get_width() / 2., hk / 2),
                     ha='center', va='center', color='white', fontweight='bold', fontsize=10)
        ax1.annotate(f"{int(hg)}", (bg.get_x() + bg.get_width() / 2., hk + hg / 2),
                     ha='center', va='center', color='white', fontweight='bold', fontsize=10)
        ax1.annotate(f"Eşik: {r_data['Eşik (Dönem)']} Dönem\nToplam: {int(hk+hg)}", 
                     (bk.get_x() + bk.get_width() / 2., hk + hg),
                     ha='center', va='bottom', color='black', fontweight='bold', fontsize=10, xytext=(0, 5), textcoords='offset points')
                     
    plt.tight_layout()
    img_path1 = os.path.join(CUR_IMG_DIR, "3_Zeki_Eleme_Kalan_Giden_" + currency + ".png")
    plt.savefig(img_path1, dpi=200, bbox_inches='tight')
    plt.close()

    # 2. Table: Zeki Firma Eleme Karar Destek Matrisi
    fig2, ax2 = plt.subplots(figsize=(24, 18))
    ax2.axis('off')
    plt.title(f"ZEKİ FİRMA ELEME KARAR DESTEK MATRİSİ ({currency})", fontsize=28, fontweight='bold', pad=60)
    
    table = ax2.table(cellText=df_matrix.values, colLabels=df_matrix.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.0, 4.5) 
    
    row_count = len(df_matrix)
    col_count = len(df_matrix.columns)
    
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=14)
            cell.set_facecolor('#2C3E50')
            txt = cell.get_text().get_text()
            if "SİL | KAL" in txt:
                cell.get_text().set_text(txt.replace("SİL | KAL", "GİDEN | KALAN"))
        elif r == 8:
            cell.set_text_props(weight='bold', color='white', fontsize=13)
            cell.set_facecolor('#34495E')
        elif r == 9:
            if c == 0 or c == col_count - 1:
                cell.set_text_props(weight='bold', color='black', fontsize=14)
                cell.set_facecolor('#F1C40F') 
            else:
                cell.set_facecolor('#FEF9E7')
        else:
            if c == 0:
                cell.set_text_props(weight='bold', fontsize=11)
                cell.set_facecolor('#ECF0F1')
            elif c > 0:
                sector_label = df_matrix.iloc[r-1, 0].split("\n")[0]
                if sector_label in sector_optimal_thresholds:
                    threshold_val = int(df_matrix.columns[c].split(" ")[0])
                    if sector_optimal_thresholds[sector_label] == threshold_val:
                        cell.set_facecolor('#F1C40F')
                    else:
                        cell.set_facecolor('white')
                else:
                    cell.set_facecolor('white')

    footer_box_text = f"KARMA OPTİMAL SEÇİM ÖZETİ\nToplam Giden: {karma_sil} Firma  |  Toplam Kalan: {karma_kal} Firma"
    plt.figtext(0.5, 0.05, footer_box_text, ha="center", fontsize=18, fontweight='bold', 
                bbox={"facecolor":"#FEF9E7", "alpha":1, "pad":15, "edgecolor":"#F1C40F", "linewidth":2})

    plt.tight_layout()
    img_path2 = os.path.join(CUR_IMG_DIR, "3_Zeki_Firma_Eleme_Matrisi_" + currency + ".png")
    plt.savefig(img_path2, dpi=200, bbox_inches='tight')
    plt.close()
    
    # --- FİLTRELENMİŞ VERİYİ KAYDET ---
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector, df in all_sector_dfs.items():
            t = sector_optimal_thresholds[sector]
            firm_counts = df.groupby('Firma Adı')['Dönem'].count()
            keep_firms = firm_counts[firm_counts >= t].index
            
            df_filtered = df[df['Firma Adı'].isin(keep_firms)]
            df_filtered.to_excel(writer, sheet_name=sector, index=False)

    print(f"[+] Zeki Eleme Matrisi oluşturuldu: {os.path.basename(img_path2)}")
    print(f"[+] Final filtrelenmiş veri kaydedildi: {os.path.basename(output_path)}")

if __name__ == "__main__":
    run_firm_filtering()
