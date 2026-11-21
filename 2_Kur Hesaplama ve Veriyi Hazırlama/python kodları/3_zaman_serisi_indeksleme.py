import pandas as pd
import os

# ============================================================
#   ADIM 3: ZAMAN SERİSİ İNDEKSLEME (TIME-SERIES ENCODING)
#   NOT: Dönemleri (2016/1) numerik sıralı sayılara çevirir.
# ============================================================

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DATA_DIR = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "2_Dolarizasyon_Raporu")
OUT_DIR = os.path.join(BASE_PATH, "2_Kur Hesaplama ve Veriyi Hazırlama", "çıktılar", "3_Zaman_Serisi_Final")

os.makedirs(OUT_DIR, exist_ok=True)

def zaman_indeksle():
    print("\n" + "="*70)
    print("   ADIM 3: ZAMAN SERİSİ NUMARALANDIRMA (ORDINAL ENCODING)")
    print("="*70)

    # İşlenecek Dolarize Dosyalar
    files = ["Final_Veri_TRY_USD.xlsx", "Final_Veri_EUR_USD.xlsx", "Final_Veri_USD_USD.xlsx"]
    
    # 1. Tüm dosyalardan tüm benzersiz dönemleri topla (Kronolojik sıra için)
    all_periods = set()
    for f in files:
        path = os.path.join(DATA_DIR, f)
        if os.path.exists(path):
            xl = pd.ExcelFile(path)
            for sheet in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sheet)
                all_periods.update(df['Dönem'].unique())
    
    # 2. Dönemleri kronolojik sırala
    # '2016/12' formatını sıralamak için geçici bir yapı kur
    def sort_key(p):
        parts = str(p).replace("/", "-").split("-")
        return int(parts[0]) * 100 + int(parts[1])

    sorted_periods = sorted(list(all_periods), key=sort_key)
    
    # Mapping oluştur: { "2016/3": 1, "2016/6": 2 ... }
    period_map = {p: i+1 for i, p in enumerate(sorted_periods)}
    
    print(f"[+] Toplam {len(sorted_periods)} benzersiz dönem tespit edildi.")
    print(f"    İlk Dönem: {sorted_periods[0]} (No: 1)")
    print(f"    Son Dönem: {sorted_periods[-1]} (No: {len(sorted_periods)})")

    # 3. Tüm dosyalara bu mapping'i uygula
    for f in files:
        src_path = os.path.join(DATA_DIR, f)
        if not os.path.exists(src_path): continue
        
        print(f"\n[İŞLEM] {f} dosyasına Dönem_No ekleniyor...")
        xl = pd.ExcelFile(src_path)
        output_path = os.path.join(OUT_DIR, f.replace(".xlsx", "_Indexed.xlsx"))
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sector in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=sector)
                
                # Mevcut 'Dönem' kolonunun üzerine sayısal indeksi yaz
                df['Dönem'] = df['Dönem'].map(period_map)
                
                # Akıllı Sıralama: Önce Firma Adı, sonra Dönem (Artan)
                df = df.sort_values(by=['Firma Adı', 'Dönem'], ascending=[True, True])
                
                df.to_excel(writer, sheet_name=sector, index=False)
                print(f"  > {sector} sektörü tamamlandı.")

        print(f"[+] Kaydedildi: {output_path}")

    print("\n" + "="*70)
    print("   ZAMAN SERİSİ İNDEKSLEME BAŞARIYLA TAMAMLANDI")
    print("="*70)

if __name__ == "__main__":
    zaman_indeksle()
