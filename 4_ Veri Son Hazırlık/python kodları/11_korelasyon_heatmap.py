import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

# --- YOLLAR ---
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "9_Adim_Sektorel_Akran_Kiyaslama")
IMG_BASE = os.path.join(PHASE4_BASE, "görseller")

# Faz 4'te türetilen 12 öznitelik + 2 hedef değişken
OZNITELIKLER = [
    "Anomali_Durumu",
    "Mevsimsellik",
    "Firma_Kum_Kar",
    "Sektor_Ort_Kum_Kar",
    "Sektorel_Kumulatif_Gorece_Kar",
    "Sektorel_Cari_Z_Skoru",
    "Sektorel_Cari_Gorece_Kar",
    "Mevsimsel_YoY_Kar_Büyümesi",
    "Sektor_Mevsimsel_Gecmis_Ort_Kar",
    "Sektorel_Mevsimsel_Gorece_Kar",
    "Sektör Üstü Performans (Gerçek)",   # Sınıflandırma hedefi
    "Net Dönem Karı (t+1)",              # Regresyon hedefi
    "Net Dönem Karı/Zararı",             # Cari dönem kâr (referans)
]

# Sütun kısaltmaları (grafik okunurluğu için)
KISALTMALAR = {
    "Anomali_Durumu":                      "Anomali",
    "Mevsimsellik":                        "Mevsim",
    "Firma_Kum_Kar":                       "Küm. Kâr",
    "Sektor_Ort_Kum_Kar":                  "Sek. Küm. Ort.",
    "Sektorel_Kumulatif_Gorece_Kar":       "Küm. Görece",
    "Sektorel_Cari_Z_Skoru":              "Cari Z-Skor",
    "Sektorel_Cari_Gorece_Kar":           "Cari Görece",
    "Mevsimsel_YoY_Kar_Büyümesi":         "YoY Büyüme",
    "Sektor_Mevsimsel_Gecmis_Ort_Kar":    "Sek. YoY Ort.",
    "Sektorel_Mevsimsel_Gorece_Kar":      "Mev. Görece",
    "Sektör Üstü Performans (Gerçek)":    "Hedef (Sınıf)",
    "Net Dönem Karı (t+1)":               "Hedef (t+1)",
    "Net Dönem Karı/Zararı":              "Net Kâr (t)",
}

def load_full_df(input_file):
    """Tüm sektörleri tek bir DataFrame'e birleştirir."""
    xl = pd.ExcelFile(input_file)
    frames = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet)
        df.columns = [c.strip() for c in df.columns]
        df["Sektör"] = sheet
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

def run_heatmap(input_file_name):
    currency = input_file_name.replace("9_Final_Sektorel_Akran_Kiyaslama_", "").replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)

    print(f"\n[>>>] Korelasyon Heatmap Oluşturuluyor: {currency}")

    df_all = load_full_df(input_path)

    # Mevcut sütunlarla kesişim
    mevcut = [c for c in OZNITELIKLER if c in df_all.columns]
    eksik = [c for c in OZNITELIKLER if c not in df_all.columns]
    if eksik:
        print(f"  [!] Bulunamayan sütunlar (atlandı): {eksik}")

    df_corr_raw = df_all[mevcut].copy()

    # Sayısal olmayan sütunları çıkar
    df_corr_raw = df_corr_raw.select_dtypes(include=[np.number])

    corr = df_corr_raw.corr()

    # Kısa ad etiketleri
    labels = [KISALTMALAR.get(c, c) for c in corr.columns]

    # ---- 1. GÖRSEL: TAM KORELASYOn HEATMAP ----
    img_dir = os.path.join(IMG_BASE, currency, "10_Korelasyon")
    os.makedirs(img_dir, exist_ok=True)

    n = len(corr)
    fig, ax = plt.subplots(figsize=(max(10, n * 0.9), max(8, n * 0.8)))

    mask = np.triu(np.ones_like(corr, dtype=bool))  # Üst üçgen gizle

    sns.heatmap(
        corr,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="RdYlGn",
        center=0,
        vmin=-1, vmax=1,
        linewidths=0.5,
        linecolor="#cccccc",
        annot_kws={"size": 9, "weight": "bold"},
        ax=ax,
        cbar_kws={"shrink": 0.8, "label": "Pearson r"}
    )

    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(labels, rotation=0, fontsize=10)
    ax.set_title(
        f"Türetilen Öznitelikler — Korelasyon Matrisi ({currency})\n"
        f"(Yeşil=Pozitif, Kırmızı=Negatif, Değerler: Pearson r)",
        fontsize=13, fontweight="bold", pad=15
    )
    plt.tight_layout()

    img_path1 = os.path.join(img_dir, f"10_Korelasyon_Heatmap_{currency}.png")
    plt.savefig(img_path1, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"  [+] Heatmap kaydedildi: {img_path1}")

    # ---- 2. GÖRSEL: HEDEF DEĞİŞKEN İLE KORELASYon (Bar Chart) ----
    hedef_cols = ["Sektör Üstü Performans (Gerçek)", "Net Dönem Karı (t+1)"]
    hedef_mevcut = [c for c in hedef_cols if c in corr.columns]

    if hedef_mevcut:
        fig2, axes = plt.subplots(1, len(hedef_mevcut), figsize=(7 * len(hedef_mevcut), 6))
        if len(hedef_mevcut) == 1:
            axes = [axes]

        for ax2, hedef in zip(axes, hedef_mevcut):
            hedef_corr = corr[hedef].drop(index=hedef, errors="ignore").sort_values()
            colors = ["#E74C3C" if v < 0 else "#2ECC71" for v in hedef_corr.values]
            kisa_idx = [KISALTMALAR.get(c, c) for c in hedef_corr.index]

            bars = ax2.barh(kisa_idx, hedef_corr.values, color=colors, edgecolor="white", alpha=0.85)

            # Değer etiketleri
            for bar, val in zip(bars, hedef_corr.values):
                x_pos = val + (0.01 if val >= 0 else -0.01)
                ha = "left" if val >= 0 else "right"
                ax2.text(x_pos, bar.get_y() + bar.get_height() / 2,
                         f"{val:.3f}", va="center", ha=ha,
                         fontsize=9, fontweight="bold", color="black")

            ax2.axvline(0, color="black", linewidth=1.2, linestyle="--")
            ax2.set_xlim(-1.1, 1.1)
            ax2.set_xlabel("Pearson r", fontsize=11)
            ax2.set_title(
                f"Hedef: {KISALTMALAR.get(hedef, hedef)} ({currency})\n"
                f"(Pozitif=Güçlü Artış, Negatif=Ters İlişki)",
                fontsize=12, fontweight="bold"
            )
            ax2.grid(axis="x", linestyle="--", alpha=0.4)

        plt.suptitle(
            f"Özniteliklerin Hedef Değişkenlerle Korelasyonu ({currency})",
            fontsize=13, fontweight="bold", y=1.02
        )
        plt.tight_layout()

        img_path2 = os.path.join(img_dir, f"10_Hedef_Korelasyon_Bar_{currency}.png")
        plt.savefig(img_path2, dpi=200, bbox_inches="tight")
        plt.close()
        print(f"  [+] Hedef korelasyon barı kaydedildi: {img_path2}")

    # ---- 3. EXCEL: Korelasyon Tablosu ----
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "10_Adim_Korelasyon")
    os.makedirs(OUT_DIR, exist_ok=True)
    excel_path = os.path.join(OUT_DIR, f"10_Korelasyon_Matrisi_{currency}.xlsx")
    corr_labeled = corr.copy()
    corr_labeled.index = labels
    corr_labeled.columns = labels

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        corr_labeled.round(4).to_excel(writer, sheet_name="Korelasyon Matrisi")

        # Hedef korelasyonları özet sayfası
        if hedef_mevcut:
            rows = []
            for hedef in hedef_mevcut:
                for oznitelik in corr.index:
                    if oznitelik != hedef:
                        rows.append({
                            "Öznitelik": KISALTMALAR.get(oznitelik, oznitelik),
                            "Hedef": KISALTMALAR.get(hedef, hedef),
                            "Pearson r": round(corr.loc[oznitelik, hedef], 4),
                            "Yön": "Pozitif" if corr.loc[oznitelik, hedef] > 0 else "Negatif",
                        })
            pd.DataFrame(rows).sort_values("Pearson r", key=abs, ascending=False) \
              .to_excel(writer, sheet_name="Hedef Korelasyon Özeti", index=False)

    print(f"  [+] Korelasyon Excel kaydedildi: {excel_path}")


if __name__ == "__main__":
    files = [f for f in os.listdir(INPUT_DIR)
             if f.startswith("9_Final_Sektorel_Akran_Kiyaslama_") and f.endswith(".xlsx")]

    if not files:
        print("Hata: Adım 9 çıktı dosyası bulunamadı!")
    else:
        for f_name in sorted(files):
            run_heatmap(f_name)
        print("\n[+] Tüm korelasyon görselleri tamamlandı.")
