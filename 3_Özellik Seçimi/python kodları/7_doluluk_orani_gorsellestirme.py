import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import textwrap

# ============================================================
#   ADIM 7: VERİ DOLULUK ORANI VE KALİTE DENETİMİ
#   NOT: Tüm sektörlerin doluluk oranlarını görselleştirir.
# ============================================================

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PHASE2_DATA = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "3_Zaman_Serisi_Final", "Final_Veri_USD_USD_Indexed.xlsx")
PHASE3_BASE = os.path.join(BASE_PATH, "3_Özellik Seçimi")

OUT_DIR = os.path.join(PHASE3_BASE, "raporlar", "7_Doluluk_Analizi")
IMG_DIR = os.path.join(PHASE3_BASE, "görseller", "7_Doluluk_Orani")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def wrap_labels(labels, width=35):
    return [textwrap.fill(str(label), width=width) for label in labels]

def run_completeness_analysis():
    print("\n" + "="*70)
    print("   ADIM 7: VERİ DOLULUK ORANI VE KALİTE DENETİMİ")
    print("="*70)

    if not os.path.exists(PHASE2_DATA):
        print(f"Hata: Veri dosyası bulunamadı! ({PHASE2_DATA})")
        return

    xl = pd.ExcelFile(PHASE2_DATA)
    summary_data = []

    for sector in xl.sheet_names:
        print(f"\nİşleniyor: {sector}")
        df = pd.read_excel(xl, sector)
        
        # Sütun bazlı doluluk oranlarını hesapla
        null_counts = df.isnull().mean() * 100
        completeness = 100 - null_counts
        
        comp_df = pd.DataFrame({
            'Özellik': completeness.index,
            'Doluluk (%)': completeness.values
        }).sort_values('Doluluk (%)', ascending=True)

        # --- GÖRSELLEŞTİRME ---
        # Sadece en az doluluk oranına sahip (veya tüm) sütunları göster
        # Eğer çok fazla sütun varsa en düşük 40 taneyi gösterelim
        plot_df = comp_df.head(40) if len(comp_df) > 40 else comp_df
        
        plt.figure(figsize=(14, len(plot_df) * 0.4 + 2))
        
        # Renk paleti (Dolu olanlar yeşil, boşluk varsa turuncu/kırmızı)
        colors = ['#27AE60' if x == 100 else '#E67E22' for x in plot_df['Doluluk (%)']]
        
        ax = sns.barplot(x='Doluluk (%)', y='Özellik', data=plot_df, palette=colors, edgecolor='black')
        
        # % Değerlerini çubukların üzerine yaz
        for p in ax.patches:
            width = p.get_width()
            ax.annotate(f'%{width:.1f}', (width, p.get_y() + p.get_height() / 2.), 
                        ha='left', va='center', fontsize=10, xytext=(5, 0), textcoords='offset points')

        plt.axvline(x=100, color='red', linestyle='--', alpha=0.3)
        plt.xlim(0, 115) # Etiketler için boşluk
        
        plt.title(f"{sector} Sektörü Veri Doluluk Analizi\n(Medyan Dolgusu Sonrası Denetim)", fontsize=16, fontweight='bold', pad=20)
        plt.xlabel("Doluluk Oranı (%)", fontsize=12)
        plt.ylabel("Özellik Adı", fontsize=12)
        
        # Etiketleri sar
        plt.gca().set_yticklabels(wrap_labels(plot_df["Özellik"]))
        
        plt.tight_layout()
        img_path = os.path.join(IMG_DIR, f"7_Doluluk_{sector}.png")
        plt.savefig(img_path, dpi=200)
        plt.close()
        
        print(f"  [+] Görsel oluşturuldu: {img_path}")
        
        # Özet veriye ekle
        summary_data.append({
            "Sektör": sector,
            "Sütun Sayısı": len(df.columns),
            "Satır Sayısı": len(df),
            "Ortalama Doluluk": f"%{completeness.mean():.2f}"
        })

    # Merkezi Rapor
    pd.DataFrame(summary_data).to_excel(os.path.join(OUT_DIR, "7_Doluluk_Ozet_Raporu.xlsx"), index=False)
    print(f"\n[+] Merkezi özet rapor oluşturuldu: {OUT_DIR}")

    print("\n" + "="*70)
    print("ADIM 7: VERİ KALİTE DENETİMİ TAMAMLANDI")
    print("="*70)

if __name__ == "__main__":
    run_completeness_analysis()
