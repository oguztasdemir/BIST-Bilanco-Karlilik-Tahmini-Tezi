import pandas as pd
import os

# ============================================================
#   ADIM 2: BİLANÇO DOLARİZASYON (CURRENCY CONVERSION)
#   NOT: Bu adım artık 1. Klasör Adım 13'teki Denetlenmiş 
#   verileri (USD, EUR, TRY) alır ve hepsini Gerçek USD'ye çevirir.
# ============================================================

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# KUR VERİSİ
KUR_DOSYASI = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "1_Kur_Verileri", "doviz_ortalamalari.xlsx")
# KAYNAK: 1. Klasör Adım 13 (Denetlenmiş Çok Kurlu Klasör)
DATA_DIR = os.path.join(BASE_PATH, "1_Veri Manipulasyonu", "raporlar", "13_Cok_Kurlu")
# HEDEF: Dolarize edilmiş verilerin yeni yuvası
OUT_DIR = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "2_Dolarizasyon_Raporu")

os.makedirs(OUT_DIR, exist_ok=True)

def donem_to_ceyrek(donem_str):
    """'2016/12' veya '2016-12' formatını '2016/4' formatına çevirir"""
    try:
        # Önce / sonra - ile bölmeyi dene
        parts = str(donem_str).replace("/", "-").split("-")
        yil = parts[0]
        ay = int(parts[1])
        ceyrek = (ay + 2) // 3 # 1-3 -> 1, 4-6 -> 2, 7-9 -> 3, 10-12 -> 4
        return f"{yil}/{ceyrek}"
    except:
        return None

def bilancolari_dolarize_et():
    print("\n" + "="*70)
    print("   ADIM 2: DENETLENMİŞ VERİLERİN DOLARİZE EDİLMESİ")
    print("="*70)

    if not os.path.exists(KUR_DOSYASI):
        print("[!] HATA: Kur dosyası bulunamadı.")
        return

    # Kur Verilerini Yükle
    tl_kurları = pd.read_excel(KUR_DOSYASI, sheet_name="TL_CEYREK").set_index("Yıl / Dönem")
    eur_kurları = pd.read_excel(KUR_DOSYASI, sheet_name="EURO_CEYREK").set_index("Yıl / Dönem")

    # Dönüştürülecek Dosyalar (Adım 13'ten gelenler)
    # USD dosyası aslında TL verisi içerdiği için onu da TL kuruyla dönüştürüyoruz.
    conversion_map = {
        "TRY": {"rate_df": tl_kurları, "file": "Final_Veri_TRY.xlsx"},
        "EUR": {"rate_df": eur_kurları, "file": "Final_Veri_EUR.xlsx"},
        "USD": {"rate_df": tl_kurları, "file": "Final_Veri_USD.xlsx"}
    }

    for key, config in conversion_map.items():
        src_path = os.path.join(DATA_DIR, config["file"])
        if not os.path.exists(src_path):
            print(f"  [!] Atlanıyor: {config['file']} bulunamadı.")
            continue

        print(f"\n[{key}] İşleniyor: {config['file']}")
        xl = pd.ExcelFile(src_path)
        output_path = os.path.join(OUT_DIR, f"Final_Veri_{key}_USD.xlsx")
        
        # USD ise doğrudan kopyala (Zaten Dolar cinsinden)
        if key == "USD":
            import shutil
            shutil.copy2(src_path, output_path)
            print(f"  [+] USD dosyası zaten Dolar bazlı, 1-1 kopyalandı.")
            continue
        
        rates_df = config["rate_df"]
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sector in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sector)
                
                id_cols = ['Firma Adı', 'Dönem', 'Sektör']
                id_cols = [c for c in id_cols if c in df.columns]
                
                def convert_row(row):
                    ceyrek_key = donem_to_ceyrek(row['Dönem'])
                    if ceyrek_key in rates_df.index:
                        rate = rates_df.loc[ceyrek_key, 'Ortalama Değer ($)']
                        for col in df.columns:
                            if col not in id_cols and pd.api.types.is_numeric_dtype(df[col]):
                                row[col] = row[col] * rate
                    return row

                df_converted = df.apply(convert_row, axis=1)
                df_converted.to_excel(writer, sheet_name=sector, index=False)
                print(f"  > {sector} sektörü tamamlandı.")

        print(f"[+] Kaydedildi: {output_path}")

    # --- GÖRSELLEŞTİRME: ÖNCE / SONRA ANALİZİ ---
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Karşılaştırma için verileri hazırla (Örn: SANAYİ sektörü, ACSEL firması)
        sector = "SANAYİ_VE_İMALAT"
        company = "ACSEL"
        
        try_src = pd.read_excel(os.path.join(DATA_DIR, "Final_Veri_TRY.xlsx"), sheet_name=sector)
        usd_res = pd.read_excel(os.path.join(OUT_DIR, "Final_Veri_TRY_USD.xlsx"), sheet_name=sector)
        
        c_try = try_src[try_src["Firma Adı"] == company].sort_values("Dönem")
        c_usd = usd_res[usd_res["Firma Adı"] == company].sort_values("Dönem")
        
        if not c_try.empty:
            fig, ax1 = plt.subplots(figsize=(12, 6))
            
            # TL Ekseni
            color = 'tab:blue'
            ax1.set_xlabel('Dönem')
            ax1.set_ylabel('Orijinal (TRY)', color=color, fontweight='bold')
            ax1.plot(c_try["Dönem"], c_try["Net Dönem Karı/Zararı"], color=color, marker='o', label="TRY Bazlı")
            ax1.tick_params(axis='y', labelcolor=color)
            plt.xticks(rotation=45)
            
            # USD Ekseni (Sağ Taraf)
            ax2 = ax1.twinx()
            color = 'tab:green'
            ax2.set_ylabel('Normalize Edilmiş (USD)', color=color, fontweight='bold')
            ax2.plot(c_usd["Dönem"], c_usd["Net Dönem Karı/Zararı"], color=color, marker='s', linestyle='--', label="USD Bazlı")
            ax2.tick_params(axis='y', labelcolor=color)
            
            plt.title(f"Dolarizasyon Etkisi: {company} Net Kar Dönüşümü\n(Enflasyon ve Kur Etkisinden Arındırma)", fontsize=14, fontweight='bold')
            fig.tight_layout()
            
            IMG_DIR = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "görseller", "2_Dolarizasyon_Analizi")
            os.makedirs(IMG_DIR, exist_ok=True)
            img_path = os.path.join(IMG_DIR, "2_Dolarizasyon_Karsilastirma.png")
            plt.savefig(img_path, dpi=300)
            plt.close()
            print(f"\n[+] Karşılaştırma görseli oluşturuldu: {img_path}")
            
    except Exception as e:
        print(f"\n[!] Görselleştirme sırasında hata: {e}")

    print("\n" + "="*70)
    print("   DOLARİZASYON İŞLEMİ TAMAMLANDI")
    print("="*70)

if __name__ == "__main__":
    bilancolari_dolarize_et()
