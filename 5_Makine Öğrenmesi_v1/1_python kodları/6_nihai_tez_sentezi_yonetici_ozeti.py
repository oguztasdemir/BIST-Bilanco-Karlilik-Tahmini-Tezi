import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 6 (Sentez) for currency: {currency}")

# Add root folder to sys.path to import kullanici.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1")
output_dir    = os.path.join(ml_dir, "3_çıktılar", "6_Nihai_Sentez")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "6_Nihai_Sentez")

reg_path    = os.path.join(ml_dir, "3_çıktılar", "3_Regresyon_Analizi",     f"Model_Performansi_{currency}.xlsx")
cls_path    = os.path.join(ml_dir, "3_çıktılar", "4_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

print("Clearing old outputs for Step 6 (Sentez)...")
for f in os.listdir(output_dir):
    try: os.remove(os.path.join(output_dir, f))
    except: pass
for f in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, f))
    except: pass

print("Loading performance reports...")
# Regresyon çıktısı (Test_Ozeti olarak değiştirilmiş genel özetten okuyalım)
# 3. Adımda isimleri değiştirdik, "sektör adı", "Ortalama Yön Bilme yüzdesi" vb. oldu.
df_reg = pd.read_excel(reg_path, sheet_name="Genel Özet", skiprows=10) # B) Test Tablosu 10. satırda başlar (0-indexed)
# Wait, let's read the specific columns directly from sheet to avoid parsing issues
# Because we combined them into Genel Özet, we should probably read the individual sheets or parse it carefully.
# Let's read Test Tablosu directly by finding where it is.
df_genel = pd.read_excel(reg_path, sheet_name="Genel Özet", header=None)
test_start = df_genel[df_genel[0] == "B) Test Tablosu"].index[0] + 1
df_reg = pd.read_excel(reg_path, sheet_name="Genel Özet", skiprows=test_start)
# We only need the first 7 columns for test table
df_reg = df_reg.iloc[:7, :7].copy() # Assuming 7 sectors
df_reg.columns = ["Sektör", "Veri Adet", "Reg_KZ_Acc", "Reg_Yön_Acc", "MAPE", "Reg_Skor", "Reg_Model"]

df_cls = pd.read_excel(cls_path, sheet_name="Genel_Ozet")

# ── Sınıflandırma ─────────────────────────────────────────────────────────────
def extract_cls(df_cls, hedef):
    sub = df_cls[df_cls["Hedef Değişken"] == hedef][
        ["Sektör", "En İyi Model", "Test Accuracy (%)", "Test F1-Score (%)"]].copy()
    sub.columns = ["Sektör", f"Cls_{hedef}_Model", f"Cls_{hedef}_Acc", f"Cls_{hedef}_F1"]
    return sub

df_cls_kz = extract_cls(df_cls, "Kar_Zarar_Tahmini")
df_cls_yon = extract_cls(df_cls, "Yon_Tahmini")

# ── Birleştir ─────────────────────────────────────────────────────────────────
df_sentez = df_reg.copy()
for df_extra in [df_cls_kz, df_cls_yon]:
    df_sentez = pd.merge(df_sentez, df_extra, on="Sektör", how="left")

# WMAPE Hesaplama
wmapes_v1 = []
xls_v1_path = os.path.join(ml_dir, "3_çıktılar", "3_Regresyon_Analizi", f"Yontem_Bazli_Basari_Analizi_{currency}.xlsx")
if os.path.exists(xls_v1_path):
    xl_v1 = pd.ExcelFile(xls_v1_path)
    for sheet_name in xl_v1.sheet_names:
        df_sheet = pd.read_excel(xls_v1_path, sheet_name=sheet_name)
        # Normalize sheet_name to compare
        def norm(n):
            return "".join([c for c in n.replace("İ","I").replace("Ş","S").replace("Ç","C").replace("Ö","O").replace("Ü","U").replace("Ğ","G").upper() if c.isalnum()])
        
        # Find matching sector in df_sentez
        matching_row = df_sentez[df_sentez["Sektör"].apply(norm) == norm(sheet_name)]
        if len(matching_row) > 0:
            sector_name = matching_row.iloc[0]["Sektör"]
            best_model_name = matching_row.iloc[0]["Reg_Model"]
            y_true = df_sheet.iloc[:, 3].values # t+1 gerçek kar
            
            # Find column starting with best_model_name
            pred_col = [col for col in df_sheet.columns if col.startswith(best_model_name) or (best_model_name == "RF" and col.startswith("RF ")) or (best_model_name == "Extra_Trees" and "Extra_Trees" in col)]
            if len(pred_col) > 0:
                y_pred = df_sheet[pred_col[0]].values
                wmape = (np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true))) * 100
                wmapes_v1.append({"Sektör": sector_name, "WMAPE": wmape})

df_wmape = pd.DataFrame(wmapes_v1)
if not df_wmape.empty:
    df_sentez = pd.merge(df_sentez, df_wmape, on="Sektör", how="left")
else:
    df_sentez["WMAPE"] = np.nan

# ═══════════════════════════════════════════════════════════════════════════════
# DOSYA 1: Master_Sentez_Raporu_{cur}.xlsx
# ═══════════════════════════════════════════════════════════════════════════════
path1 = os.path.join(output_dir, f"Master_Sentez_Raporu_{currency}.xlsx")
with pd.ExcelWriter(path1, engine="xlsxwriter") as w:
    df_sentez.to_excel(w, sheet_name="Master_Sentez", index=False)
print(f"Dosya 1 kaydedildi: {path1}")

# ═══════════════════════════════════════════════════════════════════════════════
# GÖRSEL 1: Performans Isı Haritası (Heatmap)
# ═══════════════════════════════════════════════════════════════════════════════
sns.set_theme(style="white")
plt.rcParams['font.family'] = 'DejaVu Sans'

df_sentez["Reg_Sayisal_Basari"] = df_sentez["Reg_Skor"] * 100

heatmap_data = df_sentez.set_index("Sektör")[
    ["Reg_Sayisal_Basari", "Reg_Yön_Acc", "Reg_KZ_Acc", "Cls_Yon_Tahmini_Acc", "Cls_Kar_Zarar_Tahmini_Acc"]
].copy().astype(float)
heatmap_data.columns = [
    "Regresyon\nSayısal Başarı", "Regresyon\nYön Başarısı", "Regresyon\nKar Zarar Başarısı", 
    "Sınıflandırma\nYön Başarısı", "Sınıflandırma\nKar Zarar Başarısı"
]

plt.figure(figsize=(12, 6))
ax = sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlGnBu", cbar_kws={'label': 'Başarı Oranı (%)'}, linewidths=1)
plt.title(f"Sektörel Tahmin Başarısı Isı Haritası ({currency})", fontsize=14, fontweight='bold', pad=20)
plt.ylabel("Sektör", fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

g1 = os.path.join(gorseller_dir, f"1_Performans_Isi_Haritasi_{currency}.png")
plt.savefig(g1, dpi=300)
plt.close()
print(f"Görsel 1 kaydedildi: {g1}")

# ═══════════════════════════════════════════════════════════════════════════════
# GÖRSEL 2: Şampiyon Algoritmalar Dağılımı (Donut Chart)
# ═══════════════════════════════════════════════════════════════════════════════
all_models = pd.concat([
    df_sentez["Reg_Model"], 
    df_sentez["Cls_Kar_Zarar_Tahmini_Model"], 
    df_sentez["Cls_Yon_Tahmini_Model"]
])
model_counts = all_models.value_counts()

plt.figure(figsize=(8, 8))
colors = sns.color_palette("Set2", len(model_counts))
wedges, texts, autotexts = plt.pie(
    model_counts, labels=model_counts.index, autopct='%1.1f%%', 
    startangle=140, colors=colors, pctdistance=0.85,
    textprops=dict(color="w", weight="bold", fontsize=10)
)
for text in texts:
    text.set_color('black')
    text.set_fontsize(11)

# Draw circle in the center to make it a donut
centre_circle = plt.Circle((0,0),0.70,fc='white')
fig = plt.gcf()
fig.gca().add_artist(centre_circle)

plt.title("Şampiyon Modellerin Genel Dağılımı (K/Z, Yön ve Regresyon Toplamı)", fontsize=14, fontweight='bold')
plt.tight_layout()

g2 = os.path.join(gorseller_dir, f"2_Sampiyon_Algoritmalar_Donut_{currency}.png")
plt.savefig(g2, dpi=300)
plt.close()
print(f"Görsel 2 kaydedildi: {g2}")

# ═══════════════════════════════════════════════════════════════════════════════
# GÖRSEL 3: Regresyon vs Sınıflandırma Kıyaslama Grafiği (Grouped Bar Chart)
# ═══════════════════════════════════════════════════════════════════════════════
plot_data = df_sentez[["Sektör", "Reg_Yön_Acc", "Cls_Yon_Tahmini_Acc", "Reg_KZ_Acc", "Cls_Kar_Zarar_Tahmini_Acc"]].copy()
plot_data.columns = [
    "Sektör",
    "Regresyon Yön Başarısı",
    "Sınıflandırma Yön Başarısı",
    "Regresyon K/Z Başarısı",
    "Sınıflandırma K/Z Başarısı"
]

melted = plot_data.melt(id_vars="Sektör", var_name="Model & Hedef", value_name="Başarı Oranı (%)")

plt.figure(figsize=(14, 7))
ax = sns.barplot(data=melted, x="Sektör", y="Başarı Oranı (%)", hue="Model & Hedef", palette="Spectral")

for p in ax.patches:
    h = p.get_height()
    if not np.isnan(h) and h > 0.01:
        ax.annotate(f"{h:.1f}",
                    (p.get_x() + p.get_width() / 2., h),
                    ha='center', va='bottom', fontsize=8, fontweight='bold',
                    xytext=(0, 2), textcoords='offset points')

plt.title(f"Regresyon vs Sınıflandırma Başarı Kıyaslaması ({currency})", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Sektör Adı", fontsize=12, fontweight='bold')
plt.ylabel("Test Başarı Oranı (%)", fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.ylim(0, 110)
plt.legend(fontsize=10, loc='lower right', ncol=2)
plt.tight_layout()

g3 = os.path.join(gorseller_dir, f"3_Reg_vs_Cls_Kiyaslama_Bar_{currency}.png")
plt.savefig(g3, dpi=300)
plt.close()
print(f"Görsel 3 kaydedildi: {g3}")

# ═══════════════════════════════════════════════════════════════════════════════
# GÖRSEL 4: Sektörel MAPE Dağılımı (Bar Plot)
# ═══════════════════════════════════════════════════════════════════════════════
plt.figure(figsize=(12, 6))
# MAPE is read from test summary
ax = sns.barplot(data=df_sentez, x="Sektör", y="MAPE", hue="Sektör", palette="Reds_r", legend=False)

for p in ax.patches:
    h = p.get_height()
    if not np.isnan(h):
        ax.annotate(f"{h:.1f}%",
                    (p.get_x() + p.get_width() / 2., h),
                    ha='center', va='bottom', fontsize=10, fontweight='bold',
                    xytext=(0, 2), textcoords='offset points')

plt.title(f"Sektörel Regresyon Tahmin Zorluğu (Ortalama MAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Sektör Adı", fontsize=12, fontweight='bold')
plt.ylabel("Hata Oranı (MAPE %)", fontsize=12, fontweight='bold')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()

g4 = os.path.join(gorseller_dir, f"4_Sektorel_MAPE_Bar_{currency}.png")
plt.savefig(g4, dpi=300)
plt.close()
print(f"Görsel 4 kaydedildi: {g4}")

# ═══════════════════════════════════════════════════════════════════════════════
# GÖRSEL 5: Sektörel WMAPE Dağılımı (Bar Plot)
# ═══════════════════════════════════════════════════════════════════════════════
if "WMAPE" in df_sentez.columns:
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=df_sentez, x="Sektör", y="WMAPE", hue="Sektör", palette="Reds_r", legend=False)
    
    for p in ax.patches:
        h = p.get_height()
        if not np.isnan(h):
            ax.annotate(f"{h:.1f}%",
                        (p.get_x() + p.get_width() / 2., h),
                        ha='center', va='bottom', fontsize=10, fontweight='bold',
                        xytext=(0, 2), textcoords='offset points')
    
    plt.title(f"Sektörel Regresyon Tahmin Zorluğu (Ortalama WMAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Sektör Adı", fontsize=12, fontweight='bold')
    plt.ylabel("Hata Oranı (WMAPE %)", fontsize=12, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    
    # Ensure all borders (spines) are visible and black to match
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(1.0)
        
    plt.tight_layout()
    g5 = os.path.join(gorseller_dir, f"5_Sektorel_WMAPE_Bar_{currency}.png")
    plt.savefig(g5, dpi=300)
    plt.close()
    print(f"Görsel 5 (WMAPE) kaydedildi: {g5}")

print("Step 6 Thesis Synthesis completed successfully!")
