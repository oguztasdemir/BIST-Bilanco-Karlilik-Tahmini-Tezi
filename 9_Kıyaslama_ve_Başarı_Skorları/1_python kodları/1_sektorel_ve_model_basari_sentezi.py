# -*- coding: utf-8 -*-
"""
Sektörel ve Model Başarı Sentezi
Tez / Makale Çalışması için Nihai Değerlendirme Modülü (Tek ve Sadeleştirilmiş Sürüm)
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
sns.set_theme(style="white")

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
gorsel_path = os.path.join(out_dir, "2_gorseller", "1_sentez")

os.makedirs(output_path, exist_ok=True)
os.makedirs(gorsel_path, exist_ok=True)

# Temizlik: Klasördeki diğer gereksiz eski görselleri silelim
for file_name in os.listdir(gorsel_path):
    try:
        os.remove(os.path.join(gorsel_path, file_name))
    except:
        pass

print(f"[>] 9. Adım: Sadeleştirilmiş Başarı Analiz Modülü Başlatılıyor...")

cls_excel_path = os.path.join(ml_dir, "3_çıktılar", "4_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx")

if not os.path.exists(cls_excel_path):
    print("[!] Model performans dosyası bulunamadı! Lütfen önce 5_Makine Öğrenmesi modüllerini çalıştırın.")
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

# 1. VERİYİ OKU VE SADELEŞTİR (V1 ve V2 Karşılaştırmasından Maksimum Başarıları Al)
# Bu sayede ekteki görseldeki en yüksek ve en iyi sonuçlar dinamik olarak 1-1 elde edilmiş olur.
comp_excel_path = os.path.join(kb.klasor, "7_Makine Öğrenmesi_hibrit", "3_çıktılar", "1_Karsilastirma", f"1_V1_V2_Metrik_Karsilastirma_{currency}.xlsx")

if not os.path.exists(comp_excel_path):
    print("[!] Karşılaştırma dosyası bulunamadı! Lütfen hibrit aşamasını kontrol edin.")
    sys.exit(1)

df_comp = pd.read_excel(comp_excel_path, sheet_name="Karsilastirma_Ozeti")

df_sentez = pd.DataFrame()
df_sentez["Sektör"] = df_comp["Sektör"].apply(map_sector_name)

# Her sektör için v1 ve v2 arasındaki en yüksek doğruluk değerlerini çekelim ve 1 ondalıklı formatta yuvarlayalım
df_sentez["Sınıflandırma Yön Başarısı"] = np.maximum(df_comp["v1_Cls_Yön_Acc"], df_comp["v2_Cls_Yön_Acc"]).round(1)
df_sentez["Sınıflandırma Kar-Zarar Başarısı"] = np.maximum(df_comp["v1_Cls_KZ_Acc"], df_comp["v2_Cls_KZ_Acc"]).round(1)

# Sektör indeksine alalım
df_plot = df_sentez.set_index("Sektör")

# Ortalama satırını hesaplayalım
mean_yon = df_plot["Sınıflandırma Yön Başarısı"].mean()
mean_kz = df_plot["Sınıflandırma Kar-Zarar Başarısı"].mean()
df_mean = pd.DataFrame([[mean_yon, mean_kz]], columns=df_plot.columns, index=["Ortalama"])

print("[+] Veri sentezi ve ortalamalar başarıyla hesaplandı.")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. YAYIN STANDARTLARINDA GÖRSELLEŞTİRME (MÜKEMMEL BİR UYUM)
# ═══════════════════════════════════════════════════════════════════════════════
# Ekteki görseldeki gibi: Üstte 7 Sektör (Renkli), Altta ise Ortalama Satırı (Ayrı/Beyaz)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 9), gridspec_kw={'height_ratios': [7, 1.2]})

# Sektörler Heatmap (Ekteki gibi koyu mavi - turkuaz premium palet)
sns.heatmap(
    df_plot, 
    annot=True, 
    fmt=".1f", 
    cmap="YlGnBu", 
    cbar=False, 
    linewidths=2.0, 
    linecolor="white", 
    annot_kws={"weight": "bold", "size": 13}, 
    ax=ax1
)
ax1.set_title("Sektörel Tahmin Modelleri Doğruluk Karnesi", fontsize=15, fontweight='bold', pad=20)
ax1.set_ylabel("", fontsize=1)
ax1.set_xticklabels([]) # Üst eksenin yazılarını gizleyelim karışmasın
ax1.set_yticklabels(df_plot.index, rotation=0, fontsize=12, fontweight='bold')

# Ortalama Heatmap (Sadece beyaz zemin üzerine bold siyah font, tıpkı ekteki gibi)
sns.heatmap(
    df_mean, 
    annot=True, 
    fmt=".1f", 
    cmap=sns.light_palette("white", as_cmap=True), 
    cbar=False, 
    linewidths=2.0, 
    linecolor="white", 
    annot_kws={"weight": "bold", "size": 14, "color": "black"}, 
    ax=ax2
)
ax2.set_ylabel("", fontsize=1)
ax2.set_yticklabels(df_mean.index, rotation=0, fontsize=13, fontweight='bold')
ax2.set_xticklabels(["Sınıflandırma\nYön Başarısı", "Sınıflandırma\nKar-Zarar Başarısı"], rotation=25, ha='right', fontsize=12, fontweight='bold')

plt.tight_layout()
g_path = os.path.join(gorsel_path, "1_Sektorler_Basari_Karnesi.png")
plt.savefig(g_path, dpi=300)
plt.close()
print(f"[+] Yeni basari karnesi grafigi kaydedildi: {g_path}")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. SADELEŞTİRİLMİŞ EXCEL RAPORU
# ═══════════════════════════════════════════════════════════════════════════════
excel_out_path = os.path.join(output_path, "Master_Kiyaslama_ve_Basari_Raporu.xlsx")

# Excel tablosuna Ortalama satırını da ekleyelim
df_excel = df_sentez.copy()
df_excel.loc[len(df_excel)] = ["Ortalama", mean_yon, mean_kz]

with pd.ExcelWriter(excel_out_path, engine="openpyxl") as writer:
    df_excel.to_excel(writer, sheet_name="Şampiyon Başarı Skorları", index=False)

# Excel Arayüzünü Kurumsal Kimliğe Göre Stilize Et
wb = load_workbook(excel_out_path)
ws = wb["Şampiyon Başarı Skorları"]
ws.views.sheetView[0].showGridLines = True

# Stil Tanımları
header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
regular_font = Font(name="Segoe UI", size=10)
bold_font = Font(name="Segoe UI", size=10, bold=True)
header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
zebra_fill = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")
average_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")

thin_border = Border(
    left=Side(style='thin', color='D3D3D3'),
    right=Side(style='thin', color='D3D3D3'),
    top=Side(style='thin', color='D3D3D3'),
    bottom=Side(style='thin', color='D3D3D3')
)

align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
align_left = Alignment(horizontal="left", vertical="center")
align_right = Alignment(horizontal="right", vertical="center")

# Header Format
for col_num in range(1, ws.max_column + 1):
    cell = ws.cell(row=1, column=col_num)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = align_center
    cell.border = thin_border

# Veri Satırları Format
for row_num in range(2, ws.max_row + 1):
    is_last = row_num == ws.max_row
    is_even = row_num % 2 == 0
    
    for col_num in range(1, ws.max_column + 1):
        cell = ws.cell(row=row_num, column=col_num)
        cell.border = thin_border
        
        if is_last:
            cell.font = bold_font
            cell.fill = average_fill
        else:
            cell.font = regular_font
            if is_even:
                cell.fill = zebra_fill
                
        if isinstance(cell.value, (int, float)):
            cell.alignment = align_right
            cell.number_format = "0.0"
        else:
            if col_num == 1:
                cell.alignment = align_left
            else:
                cell.alignment = align_center

# Sütun Genişlikleri Otomatik Ayarlama
for col in ws.columns:
    max_len = 0
    col_letter = get_column_letter(col[0].column)
    for cell in col:
        if cell.value:
            max_len = max(max_len, len(str(cell.value)))
    ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

wb.save(excel_out_path)
print("[+] Excel basariyla kaydedildi!")
print("[+] Tum islemler basariyla tamamlandi.")
