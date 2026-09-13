import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ── Para Birimi Parametresi ──────────────────────────────────────────────────
currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"Running Step 12 (Nihai Tez Sentezi ve Master Excel) for currency: {currency}")

# Add root folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

# ── Yol Tanımları ─────────────────────────────────────────────────────────────
ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
output_dir = os.path.join(ml_dir, "3_çıktılar", "12_Tez_Sentezi")
gorseller_dir = os.path.join(ml_dir, "2_gorseller", "12_Tez_Sentezi")

reg_output = os.path.join(ml_dir, "3_çıktılar", "6_Regresyon_Analizi", f"Model_Performansi_{currency}.xlsx")
clf_output = os.path.join(ml_dir, "3_çıktılar", "7_Siniflandirma_Analizi", f"Model_Performansi_Siniflandirma_{currency}.xlsx")
stack_output = os.path.join(ml_dir, "3_çıktılar", "9_Meta_Modelleme", f"Stacking_Performans_Raporu_{currency}.xlsx")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(gorseller_dir, exist_ok=True)

# Clear old outputs
for file in os.listdir(output_dir):
    try: os.remove(os.path.join(output_dir, file))
    except: pass
for file in os.listdir(gorseller_dir):
    try: os.remove(os.path.join(gorseller_dir, file))
    except: pass

# Load and parse regression report
df_reg = None
if os.path.exists(reg_output):
    try:
        df_sheet = pd.read_excel(reg_output, sheet_name="Genel Özet", header=None)
        # Find where "B) Test Tablosu" starts
        test_indices = df_sheet[df_sheet[0] == "B) Test Tablosu"].index
        if len(test_indices) > 0:
            test_start = test_indices[0]
            # Read from there
            df_reg_raw = pd.read_excel(reg_output, sheet_name="Genel Özet", skiprows=test_start + 1)
            # Find next title "C) MAPE Tablosu" to crop
            mape_indices = df_reg_raw[df_reg_raw.iloc[:, 0] == "C) MAPE Tablosu"].index
            if len(mape_indices) > 0:
                df_reg = df_reg_raw.iloc[:mape_indices[0] - 1].copy()
            else:
                df_reg = df_reg_raw.copy()
            # Keep only first 7 columns to prevent any index or empty column mismatch
            df_reg = df_reg.iloc[:, :7]
            # Drop rows where first column is NaN
            df_reg = df_reg.dropna(subset=[df_reg.columns[0]]).reset_index(drop=True)
            # Rename columns
            df_reg.columns = ["Sektör", "Gözlem Sayısı", "Kar-Zarar Başarısı (%)", "Yön Başarısı (%)", "MAPE (%)", "Başarı Skoru", "En Başarılı Model"]
    except Exception as e:
        print(f"Error parsing Regresson report: {e}")

# Load classification report
df_clf = None
if os.path.exists(clf_output):
    try:
        df_clf = pd.read_excel(clf_output, sheet_name="Genel_Ozet")
    except Exception as e:
        print(f"Error loading Classification report: {e}")

# Load Stacking report
df_stack = None
if os.path.exists(stack_output):
    try:
        df_stack = pd.read_excel(stack_output, sheet_name="Genel_Stacking_Ozet")
    except Exception as e:
        print(f"Error loading Stacking report: {e}")

# Save Master Synthesis Excel
master_path = os.path.join(output_dir, f"12_BIST_{currency}_Master_Sentez.xlsx")
writer = pd.ExcelWriter(master_path, engine="xlsxwriter")

if df_reg is not None:
    df_reg.to_excel(writer, sheet_name="Regresyon_Ozet", index=False)
if df_clf is not None:
    df_clf.to_excel(writer, sheet_name="Siniflandirma_Ozet", index=False)
if df_stack is not None:
    df_stack.to_excel(writer, sheet_name="Stacking_Ozet", index=False)

# Create overview sheet
overview_rows = []
if df_reg is not None and df_stack is not None:
    for idx, row in df_reg.iterrows():
        sect = row["Sektör"]
        best_reg = row["En Başarılı Model"]
        r2_reg = row["Başarı Skoru"] # Since we don't have R2 in the summary directly, use Başarı Skoru
        mape_reg = row["MAPE (%)"]
        
        stack_match = df_stack[df_stack["Sektör"] == sect]
        if not stack_match.empty:
            r2_stack = stack_match["R2 (Stacking)"].values[0]
            mape_stack = stack_match["MAPE (Stacking)"].values[0]
            dir_acc_stack = stack_match["Yön Doğruluğu (Stacking)"].values[0]
            best_single_r2 = stack_match["R2 (Best Single)"].values[0]
        else:
            r2_stack, mape_stack, dir_acc_stack, best_single_r2 = np.nan, np.nan, np.nan, np.nan
            
        # Compute Tekil WMAPE
        wmape_reg = np.nan
        xls_v2_path = os.path.join(ml_dir, "3_çıktılar", "6_Regresyon_Analizi", f"Yontem_Bazli_Basari_Analizi_{currency}.xlsx")
        if os.path.exists(xls_v2_path):
            def norm(n):
                return "".join([c for c in n.replace("İ","I").replace("Ş","S").replace("Ç","C").replace("Ö","O").replace("Ü","U").replace("Ğ","G").upper() if c.isalnum()])
            try:
                xl_v2 = pd.ExcelFile(xls_v2_path)
                matching_sheet = [s for s in xl_v2.sheet_names if norm(s) == norm(sect)]
                if matching_sheet:
                    df_sheet = pd.read_excel(xls_v2_path, sheet_name=matching_sheet[0])
                    y_true = df_sheet.iloc[:, 3].values # t+1 gerçek kar
                    pred_col = [col for col in df_sheet.columns if col.startswith(best_reg) or (best_reg == "RF" and col.startswith("RF ")) or (best_reg == "Extra_Trees" and "Extra_Trees" in col)]
                    if pred_col:
                        y_pred = df_sheet[pred_col[0]].values
                        wmape_reg = (np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true))) * 100
            except Exception as e:
                print("Error calculating Tekil WMAPE:", e)
                
        # Compute Stacking WMAPE
        wmape_stack = np.nan
        xls_stack_path = os.path.join(ml_dir, "3_çıktılar", "9_Meta_Modelleme", f"Stacking_Performans_Raporu_{currency}.xlsx")
        if os.path.exists(xls_stack_path):
            def norm(n):
                return "".join([c for c in n.replace("İ","I").replace("Ş","S").replace("Ç","C").replace("Ö","O").replace("Ü","U").replace("Ğ","G").upper() if c.isalnum()])
            try:
                xl_stack = pd.ExcelFile(xls_stack_path)
                matching_sheet = [s for s in xl_stack.sheet_names if norm(s) == norm(sect)]
                if matching_sheet:
                    df_sheet = pd.read_excel(xls_stack_path, sheet_name=matching_sheet[0])
                    y_true = df_sheet['Gerçek'].values
                    y_pred = df_sheet['Tahmin_Stacking'].values
                    wmape_stack = (np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true))) * 100
            except Exception as e:
                print("Error calculating Stacking WMAPE:", e)
            
        overview_rows.append({
            "Sektör": sect,
            "Tekil Model Şampiyonu": best_reg,
            "Tekil R2 (Best Single)": best_single_r2,
            "Tekil MAPE (%)": mape_reg,
            "Tekil WMAPE (%)": wmape_reg,
            "Stacking R2": r2_stack,
            "Stacking MAPE (%)": mape_stack,
            "Stacking WMAPE (%)": wmape_stack,
            "Stacking Yön Başarısı (%)": dir_acc_stack
        })
    df_overview = pd.DataFrame(overview_rows)
    df_overview.to_excel(writer, sheet_name="Genel_Yonetici_Ozeti", index=False)

writer.close()
print(f"Master Synthesis Excel saved to: {master_path}")

# ── NİHAİ GÖRSELLER (ZORUNLU) ────────────────────────────────────────────────
# 1. Şampiyon Modeller Donut Grafiği
if df_reg is not None:
    plt.figure(figsize=(8, 8))
    champ_counts = df_reg["En Başarılı Model"].value_counts()
    colors = ['#3498db', '#2ecc71', '#e74c3c', '#f1c40f', '#9b59b6', '#34495e']
    plt.pie(champ_counts, labels=champ_counts.index, autopct='%1.1f%%', startangle=90, colors=colors[:len(champ_counts)],
            wedgeprops=dict(width=0.4, edgecolor='white'))
    plt.title(f"Sektörel Regresyon Şampiyon Modellerinin Dağılımı ({currency})", fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    gorsel_donut = os.path.join(gorseller_dir, f"12_Champion_Models_Donut_{currency}.png")
    plt.savefig(gorsel_donut, dpi=300)
    plt.close()
    print(f"Donut grafiği kaydedildi: {gorsel_donut}")

# 2. Sektörel Tahmin Başarısı Isı Haritası (Heatmap)
if df_reg is not None and df_clf is not None:
    # Extract classification targets
    def extract_cls_acc(df, target):
        sub = df[df["Hedef Değişken"] == target][["Sektör", "Test Accuracy (%)"]].copy()
        sub.columns = ["Sektör", f"Cls_{target}_Acc"]
        return sub
    
    df_cls_kz = extract_cls_acc(df_clf, "Kar_Zarar_Tahmini")
    df_cls_yon = extract_cls_acc(df_clf, "Yon_Tahmini")
    
    # Merge with regression metrics
    df_heatmap_data = df_reg[["Sektör", "Başarı Skoru", "Yön Başarısı (%)", "Kar-Zarar Başarısı (%)"]].copy()
    df_heatmap_data["Reg_Sayisal_Basari"] = df_heatmap_data["Başarı Skoru"] * 100
    
    df_heatmap_data = pd.merge(df_heatmap_data, df_cls_kz, on="Sektör", how="left")
    df_heatmap_data = pd.merge(df_heatmap_data, df_cls_yon, on="Sektör", how="left")
    
    heatmap_df = df_heatmap_data.set_index("Sektör")[
        ["Reg_Sayisal_Basari", "Yön Başarısı (%)", "Kar-Zarar Başarısı (%)", "Cls_Yon_Tahmini_Acc", "Cls_Kar_Zarar_Tahmini_Acc"]
    ].copy().astype(float)
    
    heatmap_df.columns = [
        "Regresyon\nSayısal Başarı", 
        "Regresyon\nYön Başarısı", 
        "Regresyon\nKar Zarar Başarısı", 
        "Sınıflandırma\nYön Başarısı", 
        "Sınıflandırma\nKar Zarar Başarısı"
    ]
    
    plt.figure(figsize=(12, 6))
    sns.heatmap(heatmap_df, annot=True, fmt=".1f", cmap="YlGnBu", cbar_kws={'label': 'Başarı Oranı (%)'}, linewidths=1, annot_kws={"size": 10, "weight": "bold"})
    plt.title(f"Sektörel Tahmin Başarısı Isı Haritası ({currency})", fontsize=14, fontweight='bold', pad=20)
    plt.ylabel("Sektör", fontsize=12, fontweight='bold')
    plt.xticks(rotation=30, ha='right', fontsize=10, fontweight='bold')
    plt.yticks(rotation=0, fontsize=10)
    plt.tight_layout()
    gorsel_heatmap = os.path.join(gorseller_dir, f"12_Sektorel_R2_Heatmap_{currency}.png")
    plt.savefig(gorsel_heatmap, dpi=300)
    plt.close()
    print(f"Heatmap grafiği kaydedildi: {gorsel_heatmap}")

# 3. Sektörel Regresyon Tahmin Zorluğu (Ortalama MAPE - USD)
if df_reg is not None and df_stack is not None:
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=df_overview, x="Sektör", y="Stacking MAPE (%)", hue="Sektör", palette="Reds_r", legend=False)
    
    # Annotate values with 1 decimal place matching v1
    for p in ax.patches:
        h = p.get_height()
        if not np.isnan(h):
            ax.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h),
                        ha='center', va='bottom', fontsize=10, fontweight='bold',
                        xytext=(0, 2), textcoords='offset points')
                        
    plt.xlabel("Sektör Adı", fontweight='bold', fontsize=12)
    plt.ylabel("Hata Oranı (MAPE %)", fontweight='bold', fontsize=12)
    plt.title(f"Sektörel Regresyon Tahmin Zorluğu (Ortalama MAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
    plt.xticks(rotation=45, ha="right")
    
    # Ensure all borders (spines) are visible and black to match v1
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(1.0)
        
    plt.tight_layout()
    gorsel_bar = os.path.join(gorseller_dir, f"12_Stacking_MAPE_Comparison_{currency}.png")
    plt.savefig(gorsel_bar, dpi=300)
    plt.close()
    print(f"Bar grafiği kaydedildi: {gorsel_bar}")

# 4. Sektörel Regresyon Tahmin Zorluğu (Ortalama WMAPE - USD)
if df_reg is not None and df_stack is not None and "Stacking WMAPE (%)" in df_overview.columns:
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(data=df_overview, x="Sektör", y="Stacking WMAPE (%)", hue="Sektör", palette="Reds_r", legend=False)
    
    # Annotate values with 1 decimal place matching v1
    for p in ax.patches:
        h = p.get_height()
        if not np.isnan(h):
            ax.annotate(f"{h:.1f}%", (p.get_x() + p.get_width() / 2., h),
                        ha='center', va='bottom', fontsize=10, fontweight='bold',
                        xytext=(0, 2), textcoords='offset points')
                        
    plt.xlabel("Sektör Adı", fontweight='bold', fontsize=12)
    plt.ylabel("Hata Oranı (WMAPE %)", fontweight='bold', fontsize=12)
    plt.title(f"Sektörel Regresyon Tahmin Zorluğu (Ortalama WMAPE - {currency})", fontsize=14, fontweight='bold', pad=15)
    plt.xticks(rotation=45, ha="right")
    
    # Ensure all borders (spines) are visible and black to match v1
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(1.0)
        
    plt.tight_layout()
    gorsel_bar_w = os.path.join(gorseller_dir, f"12_Stacking_WMAPE_Comparison_{currency}.png")
    plt.savefig(gorsel_bar_w, dpi=300)
    plt.close()
    print(f"WMAPE Bar grafiği kaydedildi: {gorsel_bar_w}")

print("Step 12 Thesis Synthesis and Graphic Center completed successfully!")
