import os
import sys
import shutil
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 2 (Hibrit En İyi/Kötü Yapboz Seçimi) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
input_file = os.path.join(ml_dir, "3_çıktılar", "1_Karsilastirma", f"1_V1_V2_Metrik_Karsilastirma_{currency}.xlsx")
output_dir = os.path.join(ml_dir, "3_çıktılar", "2_Hibrit_Karar_Matrisi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "2_Hibrit_Karar_Matrisi")

# Source model folders
modeller_v1_dir = os.path.abspath(os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1", "4_modeller"))
modeller_v2_dir = os.path.abspath(os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2", "4_modeller"))

# Destination model folders (organized under 2_Hibrit_Modeller)
dest_modeller_dir = os.path.join(ml_dir, "4_modeller")
dest_reg_dir = os.path.join(dest_modeller_dir, "2_Hibrit_Modeller", "3_Regresyon_Analizi")
dest_cls_dir = os.path.join(dest_modeller_dir, "2_Hibrit_Modeller", "4_Siniflandirma_Analizi")
dest_meta_dir = os.path.join(dest_modeller_dir, "2_Hibrit_Modeller", "9_Meta_Modelleme")

# Clean old top-level folders to keep structure neat
for old_folder in ["3_Regresyon_Analizi", "4_Siniflandirma_Analizi", "9_Meta_Modelleme"]:
    old_path = os.path.join(dest_modeller_dir, old_folder)
    if os.path.exists(old_path):
        shutil.rmtree(old_path)

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)
os.makedirs(dest_reg_dir, exist_ok=True)
os.makedirs(dest_cls_dir, exist_ok=True)
os.makedirs(dest_meta_dir, exist_ok=True)

# ── 1. VERİLERİ YÜKLEME ──────────────────────────────────────────────────────
if not os.path.exists(input_file):
    print(f"Hata: Karşılaştırma excel dosyası bulunamadı: {input_file}")
    sys.exit(1)

df_v1 = pd.read_excel(input_file, sheet_name="v1_Tum_Metrikler")
df_v2 = pd.read_excel(input_file, sheet_name="v2_Tum_Metrikler")

# Helper function to copy selected model files (.pkb/.pkl)
def copy_sector_models(sect, version, task):
    if version == "V1":
        src_dir_reg = os.path.join(modeller_v1_dir, "3_Regresyon_Analizi")
        src_dir_cls = os.path.join(modeller_v1_dir, "4_Siniflandirma_Analizi")
    else:
        src_dir_reg = os.path.join(modeller_v2_dir, "6_Regresyon_Analizi")
        src_dir_cls = os.path.join(modeller_v2_dir, "7_Siniflandirma_Analizi")
        src_dir_meta = os.path.join(modeller_v2_dir, "9_Meta_Modelleme")
        
    if task == "Reg":
        patterns = [
            os.path.join(src_dir_reg, f"champion_{sect}_{currency}.pkb"),
            os.path.join(src_dir_reg, f"champion_{sect}_{currency}.pkl")
        ]
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                shutil.copy(filepath, os.path.join(dest_reg_dir, os.path.basename(filepath)))
                
        if version == "V2":
            meta_patterns = [
                os.path.join(src_dir_meta, f"stacking_meta_{sect}_{currency}.pkl"),
                os.path.join(src_dir_meta, f"stacking_meta_{sect}_{currency}.pkb")
            ]
            for pattern in meta_patterns:
                for filepath in glob.glob(pattern):
                    shutil.copy(filepath, os.path.join(dest_meta_dir, os.path.basename(filepath)))
                    
    elif task == "Cls_KZ":
        patterns = [
            os.path.join(src_dir_cls, f"champion_{sect}_Kar_Zarar_Tahmini_{currency}.pkb"),
            os.path.join(src_dir_cls, f"champion_{sect}_Kar_Zarar_Tahmini_{currency}.pkl")
        ]
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                shutil.copy(filepath, os.path.join(dest_cls_dir, os.path.basename(filepath)))
                
    elif task == "Cls_Yön":
        patterns = [
            os.path.join(src_dir_cls, f"champion_{sect}_Yon_Tahmini_{currency}.pkb"),
            os.path.join(src_dir_cls, f"champion_{sect}_Yon_Tahmini_{currency}.pkl")
        ]
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                shutil.copy(filepath, os.path.join(dest_cls_dir, os.path.basename(filepath)))

# ── 2. YAPBOZ (JIGSAW) EN İYİ / EN KÖTÜ LOGİCİ ──────────────────────────────
best_rows = []
worst_rows = []

best_visual_data = []
worst_visual_data = []

hybrid_reg_list = []

for idx, row_v1 in df_v1.iterrows():
    sect = row_v1["Sektör"]
    row_v2 = df_v2[df_v2["Sektör"] == sect].iloc[0]
    
    # 1. Regresyon Sayısal Başarı (Reg_Skor)
    if row_v2["Reg_Skor"] >= row_v1["Reg_Skor"]:
        b_reg_num, w_reg_num = ("V2", row_v2["Reg_Skor"] * 100), ("V1", row_v1["Reg_Skor"] * 100)
        reg_ver = "V2"
        reg_mape = row_v2["MAPE"]
        reg_wmape = row_v2["WMAPE (%)"]
    else:
        b_reg_num, w_reg_num = ("V1", row_v1["Reg_Skor"] * 100), ("V2", row_v2["Reg_Skor"] * 100)
        reg_ver = "V1"
        reg_mape = row_v1["MAPE"]
        reg_wmape = row_v1["WMAPE (%)"]
        
    # Copy Regression Champion Models
    copy_sector_models(sect, reg_ver, "Reg")
        
    # 2. Regresyon Yön Başarısı
    if row_v2["Reg_Yön_Acc"] >= row_v1["Reg_Yön_Acc"]:
        b_reg_yon, w_reg_yon = ("V2", row_v2["Reg_Yön_Acc"]), ("V1", row_v1["Reg_Yön_Acc"])
    else:
        b_reg_yon, w_reg_yon = ("V1", row_v1["Reg_Yön_Acc"]), ("V2", row_v2["Reg_Yön_Acc"])
        
    # 3. Regresyon Kar-Zarar Başarısı
    if row_v2["Reg_KZ_Acc"] >= row_v1["Reg_KZ_Acc"]:
        b_reg_kz, w_reg_kz = ("V2", row_v2["Reg_KZ_Acc"]), ("V1", row_v1["Reg_KZ_Acc"])
    else:
        b_reg_kz, w_reg_kz = ("V1", row_v1["Reg_KZ_Acc"]), ("V2", row_v2["Reg_KZ_Acc"])
        
    # 4. Sınıflandırma Yön Başarısı
    if row_v2["Cls_Yon_Tahmini_Acc"] >= row_v1["Cls_Yon_Tahmini_Acc"]:
        b_cls_yon, w_cls_yon = ("V2", row_v2["Cls_Yon_Tahmini_Acc"]), ("V1", row_v1["Cls_Yon_Tahmini_Acc"])
        cls_yon_ver = "V2"
    else:
        b_cls_yon, w_cls_yon = ("V1", row_v1["Cls_Yon_Tahmini_Acc"]), ("V2", row_v2["Cls_Yon_Tahmini_Acc"])
        cls_yon_ver = "V1"
        
    # Copy Classification Yön Champion Models
    copy_sector_models(sect, cls_yon_ver, "Cls_Yön")
        
    # 5. Sınıflandırma Kar-Zarar Başarısı
    if row_v2["Cls_Kar_Zarar_Tahmini_Acc"] >= row_v1["Cls_Kar_Zarar_Tahmini_Acc"]:
        b_cls_kz, w_cls_kz = ("V2", row_v2["Cls_Kar_Zarar_Tahmini_Acc"]), ("V1", row_v1["Cls_Kar_Zarar_Tahmini_Acc"])
        cls_kz_ver = "V2"
    else:
        b_cls_kz, w_cls_kz = ("V1", row_v1["Cls_Kar_Zarar_Tahmini_Acc"]), ("V2", row_v2["Cls_Kar_Zarar_Tahmini_Acc"])
        cls_kz_ver = "V1"
        
    # Copy Classification Kar-Zarar Champion Models
    copy_sector_models(sect, cls_kz_ver, "Cls_KZ")
        
    best_rows.append({
        "Sektör": sect,
        "Reg_Sayısal_Versiyon": b_reg_num[0],
        "Reg_Sayısal_Skor (%)": b_reg_num[1],
        "Reg_Yön_Versiyon": b_reg_yon[0],
        "Reg_Yön_Skor (%)": b_reg_yon[1],
        "Reg_KZ_Versiyon": b_reg_kz[0],
        "Reg_KZ_Skor (%)": b_reg_kz[1],
        "Cls_Yön_Versiyon": b_cls_yon[0],
        "Cls_Yön_Skor (%)": b_cls_yon[1],
        "Cls_KZ_Versiyon": b_cls_kz[0],
        "Cls_KZ_Skor (%)": b_cls_kz[1]
    })
    
    worst_rows.append({
        "Sektör": sect,
        "Reg_Sayısal_Versiyon": w_reg_num[0],
        "Reg_Sayısal_Skor (%)": w_reg_num[1],
        "Reg_Yön_Versiyon": w_reg_yon[0],
        "Reg_Yön_Skor (%)": w_reg_yon[1],
        "Reg_KZ_Versiyon": w_reg_kz[0],
        "Reg_KZ_Skor (%)": w_reg_kz[1],
        "Cls_Yön_Versiyon": w_cls_yon[0],
        "Cls_Yön_Skor (%)": w_cls_yon[1],
        "Cls_KZ_Versiyon": w_cls_kz[0],
        "Cls_KZ_Skor (%)": w_cls_kz[1]
    })
    
    best_visual_data.append({
        "Sektör": sect,
        "Col1": b_reg_num, "Col2": b_reg_yon, "Col3": b_reg_kz, "Col4": b_cls_yon, "Col5": b_cls_kz
    })
    
    worst_visual_data.append({
        "Sektör": sect,
        "Col1": w_reg_num, "Col2": w_reg_yon, "Col3": w_reg_kz, "Col4": w_cls_yon, "Col5": w_cls_kz
    })
    
    hybrid_reg_list.append({
        "Sektör": sect,
        "Sektör_Etiketi": f"{sect}\n({reg_ver})",
        "MAPE": reg_mape,
        "WMAPE": reg_wmape
    })

df_best = pd.DataFrame(best_rows)
df_worst = pd.DataFrame(worst_rows)
df_hybrid_reg = pd.DataFrame(hybrid_reg_list)

# Calculate Column-wise Averages
def get_avg_row(df):
    avg_dict = {"Sektör": "ORTALAMA"}
    for col in df.columns:
        if col.endswith("(%)"):
            avg_dict[col] = df[col].mean()
        elif col != "Sektör":
            avg_dict[col] = "-"
    return avg_dict

best_avg = get_avg_row(df_best)
worst_avg = get_avg_row(df_worst)

df_best = pd.concat([df_best, pd.DataFrame([best_avg])], ignore_index=True)
df_worst = pd.concat([df_worst, pd.DataFrame([worst_avg])], ignore_index=True)

# Add average visual row info
best_avg_visual = {
    "Sektör": "ORTALAMA",
    "Col1": ("", best_avg["Reg_Sayısal_Skor (%)"]),
    "Col2": ("", best_avg["Reg_Yön_Skor (%)"]),
    "Col3": ("", best_avg["Reg_KZ_Skor (%)"]),
    "Col4": ("", best_avg["Cls_Yön_Skor (%)"]),
    "Col5": ("", best_avg["Cls_KZ_Skor (%)"])
}
worst_avg_visual = {
    "Sektör": "ORTALAMA",
    "Col1": ("", worst_avg["Reg_Sayısal_Skor (%)"]),
    "Col2": ("", worst_avg["Reg_Yön_Skor (%)"]),
    "Col3": ("", worst_avg["Reg_KZ_Skor (%)"]),
    "Col4": ("", worst_avg["Cls_Yön_Skor (%)"]),
    "Col5": ("", worst_avg["Cls_KZ_Skor (%)"])
}

best_visual_data.append(best_avg_visual)
worst_visual_data.append(worst_avg_visual)

# Açıklama Notları
notes_rows = []
for idx, r in enumerate(best_rows):
    sect = r["Sektör"]
    w_r = worst_rows[idx]
    note_text = (
        f"En İyi Yapboz Kombinasyonu: Sayısal reg için {r['Reg_Sayısal_Versiyon']} (%{r['Reg_Sayısal_Skor (%)']:.1f}), "
        f"Reg Yön için {r['Reg_Yön_Versiyon']} (%{r['Reg_Yön_Skor (%)']:.1f}), Cls Yön için {r['Cls_Yön_Versiyon']} (%{r['Cls_Yön_Skor (%)']:.1f}). "
        f"En Kötü Kombinasyon: Sayısal reg için {w_r['Reg_Sayısal_Versiyon']} (%{w_r['Reg_Sayısal_Skor (%)']:.1f}), "
        f"Reg Yön için {w_r['Reg_Yön_Versiyon']} (%{w_r['Reg_Yön_Skor (%)']:.1f}), Cls Yön için {w_r['Cls_Yön_Versiyon']} (%{w_r['Cls_Yön_Skor (%)']:.1f})."
    )
    notes_rows.append({
        "Sektör": sect,
        "Yapboz Akademik Raporu (En İyi vs En Kötü)": note_text
    })
df_notes = pd.DataFrame(notes_rows)

# Excel Kaydet
path_excel = os.path.join(output_dir, f"2_BIST_{currency}_Hibrit_Karar_Matrisi.xlsx")
with pd.ExcelWriter(path_excel, engine="xlsxwriter") as writer:
    df_best.to_excel(writer, sheet_name="En_Iyi_Yapboz_Matrisi", index=False)
    df_worst.to_excel(writer, sheet_name="En_Kotu_Yapboz_Matrisi", index=False)
    df_notes.to_excel(writer, sheet_name="Açıklama_Notları", index=False)

print(f"Excel Raporu Kaydedildi: {path_excel}")

# ── 3. YAPBOZ HARİTALARINI ÇİZME FONKSİYONU ──────────────────────────────────
def plot_jigsaw_map(data, title_suffix, filename):
    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-2.5, 7.5)
    ax.axis('off')
    
    # Title
    ax.text(2.5, 7.2, f"BIST Sektörel Hibrit Yapboz Karar Matrisi - {title_suffix} ({currency})", 
            fontsize=16, fontweight='bold', ha='center', color="#2c3e50")
    
    # Column headers
    cols = [
        "Regresyon\nSayısal Başarı", 
        "Regresyon\nYön Başarısı", 
        "Regresyon\nKar-Zarar Başarısı", 
        "Sınıflandırma\nYön Başarısı", 
        "Sınıflandırma\nKar-Zarar Başarısı"
    ]
    for c in range(5):
        ax.text(c + 0.5, 6.7, cols[c], fontsize=11, fontweight='bold', ha='center', va='center', color="#2c3e50")
        
    # Draw cells
    for r in range(8):
        sect_name = data[r]["Sektör"]
        is_avg = (sect_name == "ORTALAMA")
        
        label_color = "#e74c3c" if is_avg else "#2c3e50"
        ax.text(-0.2, 6 - r, sect_name, fontsize=11 if is_avg else 10, fontweight='bold', ha='right', va='center', color=label_color)
        
        col_keys = ["Col1", "Col2", "Col3", "Col4", "Col5"]
        for c in range(5):
            v_name, score = data[r][col_keys[c]]
            
            if is_avg:
                color = "#eaeded"
                edge_color = "#7f8c8d"
                text_content = f"%{score:.1f}"
            else:
                color = "#f5b7b1" if v_name == "V1" else "#aed6f1"
                edge_color = "#34495e"
                text_content = f"{v_name}\n%{score:.1f}"
            
            rect = patches.Rectangle((c + 0.08, 6 - r - 0.35), 0.84, 0.7, facecolor=color, edgecolor=edge_color, linewidth=2.0 if is_avg else 1.5)
            ax.add_patch(rect)
            
            ax.text(c + 0.5, 6 - r, text_content, fontsize=11, fontweight='bold', ha='center', va='center', color="#2c3e50")
            
    rect_v1 = patches.Rectangle((0.8, -2.0), 0.15, 0.12, facecolor="#f5b7b1", edgecolor="#34495e", linewidth=1.5)
    rect_v2 = patches.Rectangle((2.8, -2.0), 0.15, 0.12, facecolor="#aed6f1", edgecolor="#34495e", linewidth=1.5)
    rect_avg = patches.Rectangle((4.8, -2.0), 0.15, 0.12, facecolor="#eaeded", edgecolor="#7f8c8d", linewidth=2.0)
    
    ax.add_patch(rect_v1)
    ax.add_patch(rect_v2)
    ax.add_patch(rect_avg)
    
    ax.text(1.0, -1.94, "V1 Modeli (Ölçeklemesiz / VIF Seçimli)", fontsize=10, fontweight='bold', va='center', color="#2c3e50")
    ax.text(3.0, -1.94, "V2 Modeli (Ölçeklenmiş / RFE / Stacking)", fontsize=10, fontweight='bold', va='center', color="#2c3e50")
    ax.text(5.0, -1.94, "Ortalama", fontsize=10, fontweight='bold', va='center', color="#2c3e50")
    
    plt.tight_layout()
    g_path = os.path.join(gorseller_dir, filename)
    plt.savefig(g_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Yapboz Haritası kaydedildi: {g_path}")

plot_jigsaw_map(best_visual_data, "En İyi Kombinasyon", f"2_BIST_{currency}_Hibrit_Yapboz_Haritasi_En_Iyi.png")
plot_jigsaw_map(worst_visual_data, "En Kötü Kombinasyon", f"3_BIST_{currency}_Hibrit_Yapboz_Haritasi_En_Kotu.png")


# ── 4. HİBRİT REGRASYON MAPE VE WMAPE GÖRSELLEŞTİRMELERİ ───────────────────────
avg_hybrid_mape = df_hybrid_reg["MAPE"].mean()
avg_hybrid_wmape = df_hybrid_reg["WMAPE"].mean()

df_hybrid_reg_plot = pd.concat([
    df_hybrid_reg,
    pd.DataFrame([{
        "Sektör": "ORTALAMA",
        "Sektör_Etiketi": "ORTALAMA",
        "MAPE": avg_hybrid_mape,
        "WMAPE": avg_hybrid_wmape
    }])
], ignore_index=True)

# 4.1 Hybrid MAPE Bar Plot
plt.figure(figsize=(12, 6))
ax_mape = sns.barplot(data=df_hybrid_reg_plot, x="Sektör_Etiketi", y="MAPE", hue="Sektör_Etiketi", palette="Reds_r", legend=False)

for p in ax_mape.patches:
    h = p.get_height()
    if not np.isnan(h):
        ax_mape.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h),
                         ha='center', va='bottom', fontsize=10, fontweight='bold',
                         xytext=(0, 2), textcoords='offset points')
                         
plt.xlabel("Sektör (Seçilen Versiyon)", fontweight='bold', fontsize=12)
plt.ylabel("Hata Oranı (MAPE %)", fontweight='bold', fontsize=12)
plt.title(f"Sektörel Regresyon Tahmin Zorluğu (En Başarılı Hibrit MAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
plt.xticks(rotation=45, ha="right")

for spine in ax_mape.spines.values():
    spine.set_visible(True)
    spine.set_color('black')
    spine.set_linewidth(1.0)
    
plt.tight_layout()
gorsel_mape = os.path.join(gorseller_dir, f"4_BIST_{currency}_Hibrit_MAPE_Bar.png")
plt.savefig(gorsel_mape, dpi=300)
plt.close()
print(f"Hibrit MAPE Bar Grafiği kaydedildi: {gorsel_mape}")

# 4.2 Hybrid WMAPE Bar Plot
plt.figure(figsize=(12, 6))
ax_wmape = sns.barplot(data=df_hybrid_reg_plot, x="Sektör_Etiketi", y="WMAPE", hue="Sektör_Etiketi", palette="Reds_r", legend=False)

for p in ax_wmape.patches:
    h = p.get_height()
    if not np.isnan(h):
        ax_wmape.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h),
                         ha='center', va='bottom', fontsize=10, fontweight='bold',
                         xytext=(0, 2), textcoords='offset points')
                         
plt.xlabel("Sektör (Seçilen Versiyon)", fontweight='bold', fontsize=12)
plt.ylabel("Hata Oranı (WMAPE %)", fontweight='bold', fontsize=12)
plt.title(f"Sektörel Regresyon Tahmin Zorluğu (En Başarılı Hibrit WMAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
plt.xticks(rotation=45, ha="right")

for spine in ax_wmape.spines.values():
    spine.set_visible(True)
    spine.set_color('black')
    spine.set_linewidth(1.0)
    
plt.tight_layout()
gorsel_wmape = os.path.join(gorseller_dir, f"5_BIST_{currency}_Hibrit_WMAPE_Bar.png")
plt.savefig(gorsel_wmape, dpi=300)
plt.close()
print(f"Hibrit WMAPE Bar Grafiği kaydedildi: {gorsel_wmape}")

print("Step 2 completed successfully!")
