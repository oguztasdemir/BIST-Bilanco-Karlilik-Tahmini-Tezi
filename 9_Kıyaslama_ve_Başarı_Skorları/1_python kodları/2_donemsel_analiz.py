# -*- coding: utf-8 -*-
"""
Modül 2: Sektörel Kar-Zarar ve Yön Tahmin Başarısı Dönemsel Trendleri
Her çeyrek dönemde 7 sektörün başarılarını ayrı çizgilerle 2 ayrı grafikte raporlar.
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Türkçe karakter uyumu ve grafik ayarları
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")

# --- KULLANICI MODÜLÜ ENTEGRASYONU ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.append(project_root)
    import kullanici as kb
except ImportError:
    class DummyKB:
        klasor = r"c:\Users\User\Desktop\Tez Feature Selection"
    kb = DummyKB()

# Para birimi ve yol ayarları
currency = "USD"
ml_dir = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1")
out_dir = os.path.join(kb.klasor, "9_Kıyaslama_ve_Başarı_Skorları")
output_path = os.path.join(out_dir, "3_çıktılar")
gorsel_path = os.path.join(out_dir, "2_gorseller", "2_donemsel")

os.makedirs(output_path, exist_ok=True)
os.makedirs(gorsel_path, exist_ok=True)

print(f"[>] Modül 2: Sektör bazlı dönemsel trend analizleri başlatılıyor...")

cls_excel_path_v1 = os.path.join(ml_dir, "3_çıktılar", "4_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx")
cls_excel_path_v2 = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2", "3_çıktılar", "7_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx")

if not os.path.exists(cls_excel_path_v1) or not os.path.exists(cls_excel_path_v2):
    print("[!] Model performans dosyaları bulunamadı!")
    sys.exit(1)

def map_sector_name(name):
    name_str = str(name).strip().upper()
    if "SANAY" in name_str or "MALAT" in name_str:
        return "Sanayi ve İmalat"
    elif "FINANS" in name_str or "FİNANS" in name_str or "YATIRIM" in name_str:
        return "Finans ve Yatırım"
    elif "INSAAT" in name_str or "İNŞAAT" in name_str or "GAYRI" in name_str or "GAYRİ" in name_str:
        return "İnşaat ve Gayrimenkul"
    elif "TEKNO" in name_str or "HIZMET" in name_str or "HİZMET" in name_str:
        return "Teknoloji ve Hizmet"
    elif "ENERJ" in name_str or "HAMMADDE" in name_str:
        return "Enerji ve Hammadde"
    elif "GIDA" in name_str or "TARIM" in name_str:
        return "Gıda ve Tarım"
    elif "TICARET" in name_str or "TİCARET" in name_str or "PAZAR" in name_str:
        return "Ticaret ve Pazarlama"
    return name_str

# V1 VE V2'Yİ KOMBİNE EDEREK DÖNEM DÖNEM 7 SEKTÖR İÇİN EN İYİ BAŞARILARI HESAPLA
donemler = range(32, 40)
sect_names = ["Sanayi ve İmalat", "Finans ve Yatırım", "İnşaat ve Gayrimenkul", "Teknoloji ve Hizmet", "Enerji ve Hammadde", "Gıda ve Tarım", "Ticaret ve Pazarlama"]

# Kayıt matrisleri: {sektör: {dönem: başarı}}
kz_data = {s: {d: 0.0 for d in donemler} for s in sect_names}
yon_data = {s: {d: 0.0 for d in donemler} for s in sect_names}

# A) V1 Verilerini Oku
xl_v1 = pd.ExcelFile(cls_excel_path_v1)
for sheet in xl_v1.sheet_names:
    if sheet == "Genel_Ozet": continue
    clean_sheet = map_sector_name(sheet)
    df_sheet = pd.read_excel(cls_excel_path_v1, sheet_name=sheet)
    for donem in donemler:
        sub = df_sheet[df_sheet["Dönem"] == donem]
        if not sub.empty:
            kz_acc = np.mean(sub["Kar_Zarar_Tahmini Gerçek"].values == sub["Kar_Zarar_Tahmini Tahmin"].values) * 100
            yon_acc = np.mean(sub["Yon_Tahmini Gerçek"].values == sub["Yon_Tahmini Tahmin"].values) * 100
            kz_data[clean_sheet][donem] = max(kz_data[clean_sheet][donem], kz_acc)
            yon_data[clean_sheet][donem] = max(yon_data[clean_sheet][donem], yon_acc)

# B) V2 Verilerini Oku
xl_v2 = pd.ExcelFile(cls_excel_path_v2)
for sheet in xl_v2.sheet_names:
    if sheet == "Genel_Ozet": continue
    # V2 sheet name parsing e.g. "SANAY_VE_MALAT_Kar_Z" or "SANAY_VE_MALAT_Yon_T"
    clean_sheet = map_sector_name(sheet.split("_Kar_Z")[0].split("_Yon_T")[0])
    df_sheet = pd.read_excel(cls_excel_path_v2, sheet_name=sheet)
    for donem in donemler:
        sub = df_sheet[df_sheet["Dönem"] == donem]
        if not sub.empty:
            acc = np.mean(sub["Gerçek"].values == sub["Tahmin"].values) * 100
            if "_Kar_Z" in sheet:
                kz_data[clean_sheet][donem] = max(kz_data[clean_sheet][donem], acc)
            else:
                yon_data[clean_sheet][donem] = max(yon_data[clean_sheet][donem], acc)

# Verileri pandas DataFrame yapısına dönüştürelim
df_kz_all = []
df_yon_all = []

for s in sect_names:
    for d in donemler:
        df_kz_all.append({"Sektör": s, "Dönem": f"Dönem {d}", "Kar-Zarar Başarısı (%)": round(kz_data[s][d], 1)})
        df_yon_all.append({"Sektör": s, "Dönem": f"Dönem {d}", "Yön Başarısı (%)": round(yon_data[s][d], 1)})

df_kz_final = pd.DataFrame(df_kz_all)
df_yon_final = pd.DataFrame(df_yon_all)

# ═══════════════════════════════════════════════════════════════════════════════
# GRAFİK 2_1: SEKTÖREL KAR-ZARAR BAŞARISI (7 Çizgi)
# ═══════════════════════════════════════════════════════════════════════════════
plt.figure(figsize=(14, 8))
palette = sns.color_palette("tab10", len(sect_names))
ax1 = sns.lineplot(data=df_kz_final, x="Dönem", y="Kar-Zarar Başarısı (%)", hue="Sektör", marker="o", markersize=8, linewidth=2.5, palette=palette)

# Tam değerleri çizgilerin üstlerine yazdırma (tam değerler)
# Kalabalık olmaması için her sektörün noktalarını kendi rengiyle yazalım
for i, sect in enumerate(sect_names):
    df_sect = df_kz_final[df_kz_final["Sektör"] == sect]
    color = palette[i]
    for idx, row in df_sect.iterrows():
        ax1.annotate(
            f"{row['Kar-Zarar Başarısı (%)']:.1f}%",
            (row["Dönem"], row["Kar-Zarar Başarısı (%)"]),
            textcoords="offset points",
            xytext=(0, 8),
            ha='center',
            fontweight='bold',
            fontsize=8.5,
            color=color
        )

plt.title("Sektörler Bazında Dönemsel Kar-Zarar Başarı Trendi", fontsize=15, fontweight='bold', pad=20)
plt.xlabel("Mali Çeyrek Dönemleri", fontsize=12, fontweight='bold')
plt.ylabel("Tahmin Başarı Oranı (%)", fontsize=12, fontweight='bold')
plt.ylim(30, 110)
plt.legend(loc='lower left', fontsize=10, frameon=True, shadow=True, title="Sektörler")
plt.tight_layout()

g_kz_path = os.path.join(gorsel_path, "2_1_Sektorler_Kar_Zarar_Donemsel_Basari_Trendi.png")
plt.savefig(g_kz_path, dpi=300)
plt.close()
print(f"[+] Kar-Zarar basari trendi grafigi kaydedildi: {g_kz_path}")

# ═══════════════════════════════════════════════════════════════════════════════
# GRAFİK 2_2: SEKTÖREL YÖN BAŞARISI (7 Çizgi)
# ═══════════════════════════════════════════════════════════════════════════════
plt.figure(figsize=(14, 8))
ax2 = sns.lineplot(data=df_yon_final, x="Dönem", y="Yön Başarısı (%)", hue="Sektör", marker="s", markersize=8, linewidth=2.5, palette=palette)

for i, sect in enumerate(sect_names):
    df_sect = df_yon_final[df_yon_final["Sektör"] == sect]
    color = palette[i]
    for idx, row in df_sect.iterrows():
        ax2.annotate(
            f"{row['Yön Başarısı (%)']:.1f}%",
            (row["Dönem"], row["Yön Başarısı (%)"]),
            textcoords="offset points",
            xytext=(0, 8),
            ha='center',
            fontweight='bold',
            fontsize=8.5,
            color=color
        )

plt.title("Sektörler Bazında Dönemsel Yön Başarı Trendi", fontsize=15, fontweight='bold', pad=20)
plt.xlabel("Mali Çeyrek Dönemleri", fontsize=12, fontweight='bold')
plt.ylabel("Tahmin Başarı Oranı (%)", fontsize=12, fontweight='bold')
plt.ylim(30, 110)
plt.legend(loc='lower left', fontsize=10, frameon=True, shadow=True, title="Sektörler")
plt.tight_layout()

g_yon_path = os.path.join(gorsel_path, "2_2_Sektorler_Yon_Donemsel_Basari_Trendi.png")
plt.savefig(g_yon_path, dpi=300)
plt.close()
print(f"[+] Yon basari trendi grafigi kaydedildi: {g_yon_path}")

# ═══════════════════════════════════════════════════════════════════════════════
# Excel Veri Sayfalarını Güncelle
# ═══════════════════════════════════════════════════════════════════════════════
excel_out_path = os.path.join(output_path, "Master_Kiyaslama_ve_Basari_Raporu.xlsx")

# Excel için tabloları yan yana veya tek bir tablo halinde birleştirelim
df_excel_kz = df_kz_final.pivot(index="Sektör", columns="Dönem", values="Kar-Zarar Başarısı (%)").reset_index()
df_excel_yon = df_yon_final.pivot(index="Sektör", columns="Dönem", values="Yön Başarısı (%)").reset_index()

with pd.ExcelWriter(excel_out_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    df_excel_kz.to_excel(writer, sheet_name="Dönemsel Kar-Zarar Başarısı", index=False)
    df_excel_yon.to_excel(writer, sheet_name="Dönemsel Yön Başarısı", index=False)

# Excel stili uygulama
wb = load_workbook(excel_out_path)
for sheet_name in ["Dönemsel Kar-Zarar Başarısı", "Dönemsel Yön Başarısı"]:
    ws = wb[sheet_name]
    ws.views.sheetView[0].showGridLines = True
    
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    regular_font = Font(name="Segoe UI", size=10)
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    zebra_fill = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )
    
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    for col_num in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = thin_border
        
    for row_num in range(2, ws.max_row + 1):
        is_even = row_num % 2 == 0
        for col_num in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.font = regular_font
            cell.border = thin_border
            if is_even:
                cell.fill = zebra_fill
            if isinstance(cell.value, (int, float)):
                cell.alignment = align_right
                cell.number_format = "0.0"
            else:
                cell.alignment = align_left
                
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

wb.save(excel_out_path)
print("[+] Excel donemsel sayfalar basariyla guncellendi!")
print("[+] Tum donemsel islemler basariyla tamamlandi.")
