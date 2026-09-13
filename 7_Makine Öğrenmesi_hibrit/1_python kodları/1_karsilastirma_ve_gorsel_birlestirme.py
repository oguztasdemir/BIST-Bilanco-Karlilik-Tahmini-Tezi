import os
import sys
import shutil
import pandas as pd
import numpy as np
from PIL import Image

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 1 (Veri Taşıma ve Yan Yana Karşılaştırma) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
v1_src = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1")
v2_src = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")

v1_dest = os.path.join(ml_dir, "3_çıktılar", "00_dataset", "v1_dataset")
v2_dest = os.path.join(ml_dir, "3_çıktılar", "00_dataset", "v2_dataset")
output_dir = os.path.join(ml_dir, "3_çıktılar", "1_Karsilastirma")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "1_Karsilastirma")

os.makedirs(v1_dest, exist_ok=True)
os.makedirs(v2_dest, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# ── 1. VERİ SETLERİNİ VE METRİK RAPORLARINI TAŞIMA ───────────────────────────
print("Veri setleri kopyalanıyor...")
# v1 datasets
shutil.copy(os.path.join(v1_src, "00_dataset", "islenmis_dataset", f"2_BIST_{currency}_VIF.xlsx"), 
            os.path.join(v1_dest, f"2_BIST_{currency}_VIF.xlsx"))
# v2 datasets
shutil.copy(os.path.join(v2_src, "00_dataset", "islenmis_dataset", f"5_BIST_{currency}_Scaled.xlsx"), 
            os.path.join(v2_dest, f"5_BIST_{currency}_Scaled.xlsx"))

print("Rapor dosyaları kopyalanıyor...")
# regression reports
shutil.copy(os.path.join(v1_src, "3_çıktılar", "3_Regresyon_Analizi", f"Model_Performansi_{currency}.xlsx"), 
            os.path.join(v1_dest, f"Model_Performansi_{currency}.xlsx"))
shutil.copy(os.path.join(v2_src, "3_çıktılar", "6_Regresyon_Analizi", f"Model_Performansi_{currency}.xlsx"), 
            os.path.join(v2_dest, f"Model_Performansi_{currency}.xlsx"))
# classification reports
shutil.copy(os.path.join(v1_src, "3_çıktılar", "4_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx"), 
            os.path.join(v1_dest, f"Model_Performansi_Siniflandirma_{currency}.xlsx"))
shutil.copy(os.path.join(v2_src, "3_çıktılar", "7_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx"), 
            os.path.join(v2_dest, f"Model_Performansi_Siniflandirma_{currency}.xlsx"))
# master synthesis reports
shutil.copy(os.path.join(v1_src, "3_çıktılar", "6_Nihai_Sentez", f"Master_Sentez_Raporu_{currency}.xlsx"), 
            os.path.join(v1_dest, f"Master_Sentez_Raporu_{currency}.xlsx"))
shutil.copy(os.path.join(v2_src, "3_çıktılar", "12_Tez_Sentezi", f"12_BIST_{currency}_Master_Sentez.xlsx"), 
            os.path.join(v2_dest, f"12_BIST_{currency}_Master_Sentez.xlsx"))

# Helper for stitching images side-by-side
def stitch_images(path1, path2, dest_name):
    if not os.path.exists(path1) or not os.path.exists(path2):
        print(f"Hata: {path1} veya {path2} bulunamadı!")
        return False
    try:
        img1 = Image.open(path1)
        img2 = Image.open(path2)
        
        # Match heights
        min_height = min(img1.height, img2.height)
        width1 = int(img1.width * (min_height / img1.height))
        width2 = int(img2.width * (min_height / img2.height))
        
        img1_res = img1.resize((width1, min_height), Image.Resampling.LANCZOS)
        img2_res = img2.resize((width2, min_height), Image.Resampling.LANCZOS)
        
        combined = Image.new("RGB", (width1 + width2, min_height))
        combined.paste(img1_res, (0, 0))
        combined.paste(img2_res, (width1, 0))
        
        dest_path = os.path.join(gorseller_dir, f"{dest_name}_{currency}.png")
        combined.save(dest_path)
        print(f"Görsel birleştirildi ve kaydedildi: {dest_path}")
        return True
    except Exception as e:
        print(f"Görsel birleştirilirken hata oluştu ({dest_name}): {e}")
        return False

# ── 2. TÜM GÖRSELLERİ YAN YANA BİRLEŞTİRME ──────────────────────────────────
# 2.1 Heatmaps
v1_heatmap = os.path.join(v1_src, "2_gorseller", "6_Nihai_Sentez", f"1_Performans_Isi_Haritasi_{currency}.png")
v2_heatmap = os.path.join(v2_src, "2_gorseller", "12_Tez_Sentezi", f"12_Sektorel_R2_Heatmap_{currency}.png")
stitch_images(v1_heatmap, v2_heatmap, "1_V1_V2_Isi_Haritalari_Yan_Yana")

# 2.2 MAPE Bar Charts
v1_mape = os.path.join(v1_src, "2_gorseller", "6_Nihai_Sentez", f"4_Sektorel_MAPE_Bar_{currency}.png")
v2_mape = os.path.join(v2_src, "2_gorseller", "12_Tez_Sentezi", f"12_Stacking_MAPE_Comparison_{currency}.png")
stitch_images(v1_mape, v2_mape, "2_V1_V2_MAPE_Yan_Yana")

# 2.3 Donut Charts
v1_donut = os.path.join(v1_src, "2_gorseller", "6_Nihai_Sentez", f"2_Sampiyon_Algoritmalar_Donut_{currency}.png")
v2_donut = os.path.join(v2_src, "2_gorseller", "12_Tez_Sentezi", f"12_Champion_Models_Donut_{currency}.png")
stitch_images(v1_donut, v2_donut, "3_V1_V2_Donut_Yan_Yana")

# 2.4 WMAPE Bar Charts
v1_wmape = os.path.join(v1_src, "2_gorseller", "6_Nihai_Sentez", f"5_Sektorel_WMAPE_Bar_{currency}.png")
v2_wmape = os.path.join(v2_src, "2_gorseller", "12_Tez_Sentezi", f"12_Stacking_WMAPE_Comparison_{currency}.png")
stitch_images(v1_wmape, v2_wmape, "4_V1_V2_WMAPE_Yan_Yana")


# ── 3. METRİKLERİ YAN YANA BİRLEŞTİREREK EXCEL RAPORU OLUŞTURMA ────────────
print("Metrikler birleştirilerek karşılaştırma raporu oluşturuluyor...")
def load_and_parse(v_folder):
    reg_path = os.path.join(v1_dest if v_folder == "v1" else v2_dest, f"Model_Performansi_{currency}.xlsx")
    cls_path = os.path.join(v1_dest if v_folder == "v1" else v2_dest, f"Model_Performansi_Siniflandirma_{currency}.xlsx")
    
    # Regresyon Test Tablosu
    df_genel = pd.read_excel(reg_path, sheet_name="Genel Özet", header=None)
    test_start = df_genel[df_genel[0] == "B) Test Tablosu"].index[0] + 1
    df_reg = pd.read_excel(reg_path, sheet_name="Genel Özet", skiprows=test_start)
    df_reg = df_reg.iloc[:7, :7].copy()
    df_reg.columns = ["Sektör", "Veri_Adet", "Reg_KZ_Acc", "Reg_Yön_Acc", "MAPE", "Reg_Skor", "Reg_Model"]
    
    # Sınıflandırma
    df_cls = pd.read_excel(cls_path, sheet_name="Genel_Ozet")
    def extract_cls(df, target):
        sub = df[df["Hedef Değişken"] == target][["Sektör", "En İyi Model", "Test Accuracy (%)"]].copy()
        sub.columns = ["Sektör", f"Cls_{target}_Model", f"Cls_{target}_Acc"]
        return sub
    df_cls_kz = extract_cls(df_cls, "Kar_Zarar_Tahmini")
    df_cls_yon = extract_cls(df_cls, "Yon_Tahmini")
    
    # Merge
    df_m = df_reg.copy()
    df_m = pd.merge(df_m, df_cls_kz, on="Sektör", how="left")
    df_m = pd.merge(df_m, df_cls_yon, on="Sektör", how="left")
    
    # Load WMAPE from Master files
    if v_folder == "v1":
        master_path = os.path.join(v1_dest, f"Master_Sentez_Raporu_{currency}.xlsx")
        if os.path.exists(master_path):
            df_master = pd.read_excel(master_path, sheet_name="Master_Sentez")
            df_m = pd.merge(df_m, df_master[["Sektör", "WMAPE"]], on="Sektör", how="left")
            df_m.rename(columns={"WMAPE": "WMAPE (%)"}, inplace=True)
        else:
            df_m["WMAPE (%)"] = np.nan
    else:
        master_path = os.path.join(v2_dest, f"12_BIST_{currency}_Master_Sentez.xlsx")
        if os.path.exists(master_path):
            df_master = pd.read_excel(master_path, sheet_name="Genel_Yonetici_Ozeti")
            df_m = pd.merge(df_m, df_master[["Sektör", "Stacking WMAPE (%)"]], on="Sektör", how="left")
            df_m.rename(columns={"Stacking WMAPE (%)": "WMAPE (%)"}, inplace=True)
        else:
            df_m["WMAPE (%)"] = np.nan
            
    return df_m

df_v1_metrics = load_and_parse("v1")
df_v2_metrics = load_and_parse("v2")

# Yan yana sütun bazlı karşılaştırma DF'i
df_compare = pd.DataFrame()
df_compare["Sektör"] = df_v1_metrics["Sektör"]
df_compare["v1_Reg_Model"] = df_v1_metrics["Reg_Model"]
df_compare["v2_Reg_Model"] = df_v2_metrics["Reg_Model"]
df_compare["v1_Reg_KZ_Acc"] = df_v1_metrics["Reg_KZ_Acc"]
df_compare["v2_Reg_KZ_Acc"] = df_v2_metrics["Reg_KZ_Acc"]
df_compare["v1_Reg_Yön_Acc"] = df_v1_metrics["Reg_Yön_Acc"]
df_compare["v2_Reg_Yön_Acc"] = df_v2_metrics["Reg_Yön_Acc"]
df_compare["v1_Reg_MAPE"] = df_v1_metrics["MAPE"]
df_compare["v2_Reg_MAPE"] = df_v2_metrics["MAPE"]
df_compare["v1_Reg_WMAPE"] = df_v1_metrics["WMAPE (%)"]
df_compare["v2_Reg_WMAPE"] = df_v2_metrics["WMAPE (%)"]
df_compare["v1_Reg_Skor"] = df_v1_metrics["Reg_Skor"]
df_compare["v2_Reg_Skor"] = df_v2_metrics["Reg_Skor"]
df_compare["v1_Cls_KZ_Acc"] = df_v1_metrics["Cls_Kar_Zarar_Tahmini_Acc"]
df_compare["v2_Cls_KZ_Acc"] = df_v2_metrics["Cls_Kar_Zarar_Tahmini_Acc"]
df_compare["v1_Cls_Yön_Acc"] = df_v1_metrics["Cls_Yon_Tahmini_Acc"]
df_compare["v2_Cls_Yön_Acc"] = df_v2_metrics["Cls_Yon_Tahmini_Acc"]

# Kaydet
path_excel = os.path.join(output_dir, f"1_V1_V2_Metrik_Karsilastirma_{currency}.xlsx")
with pd.ExcelWriter(path_excel, engine="xlsxwriter") as writer:
    df_v1_metrics.to_excel(writer, sheet_name="v1_Tum_Metrikler", index=False)
    df_v2_metrics.to_excel(writer, sheet_name="v2_Tum_Metrikler", index=False)
    df_compare.to_excel(writer, sheet_name="Karsilastirma_Ozeti", index=False)

print(f"Karşılaştırma Excel Raporu Kaydedildi: {path_excel}")
print("Step 1 (Taşıma ve Yan Yana Karşılaştırma) başarıyla tamamlandı!")
