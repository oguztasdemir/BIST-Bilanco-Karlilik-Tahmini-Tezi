import yfinance as yf
import pandas as pd
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Script'in bulunduğu dizini al
script_dizini = os.path.dirname(os.path.abspath(__file__))

# 'kullanici.py' dosyasını üst dizinlerde ara
mevcut_yol = script_dizini
while True:
    if os.path.exists(os.path.join(mevcut_yol, 'kullanici.py')):
        sys.path.append(mevcut_yol)
        break
    ust_yol = os.path.dirname(mevcut_yol)
    if ust_yol == mevcut_yol:
        break
    mevcut_yol = ust_yol

import kullanici as kb

def kurlari_cek_ve_hesapla():
    semboller = {
        'TL': 'TRY=X',
        'EURO': 'EURUSD=X'
    }
    
    sayfa_verileri = {}
    
    # Başlangıç tarihini 2015 yapalım
    baslangic_tarihi = "2015-01-01"
    
    for para_birimi, sembol in semboller.items():
        print(f"{para_birimi} ({sembol}) verileri çekiliyor...")
        veriler = yf.download(sembol, start=baslangic_tarihi, interval="1d")
        
        if veriler.empty:
            print(f"{para_birimi} için veri bulunamadı. Atlanıyor...")
            continue
            
        kurlar = veriler['Close']
        if para_birimi == 'TL':
            kurlar = 1 / kurlar
            
        # 1. Aylık Ortalamaları Hesapla
        aylik_ortalama = kurlar.resample('ME').mean()
        df_aylik = pd.DataFrame(aylik_ortalama)
        df_aylik.columns = ['Ortalama Değer ($)']
        df_aylik.index = df_aylik.index.strftime('%Y-%m')
        df_aylik.index.name = 'Yıl / Ay'
        
        # 2. Çeyrek Bazlı Ortalamaları Hesapla
        ceyrek_ortalama = kurlar.resample('3ME').mean()
        df_ceyrek = pd.DataFrame(ceyrek_ortalama)
        df_ceyrek.columns = ['Ortalama Değer ($)']
        df_ceyrek.index = [f"{x.year}/{x.quarter}" for x in df_ceyrek.index]
        df_ceyrek.index.name = 'Yıl / Dönem'
        
        sayfa_verileri[f"{para_birimi}_AYLIK"] = df_aylik
        sayfa_verileri[f"{para_birimi}_CEYREK"] = df_ceyrek

    cikti_klasoru = os.path.join(os.path.dirname(script_dizini), "çıktılar", "1_Kur_Verileri")
    gorsel_klasoru = os.path.join(os.path.dirname(script_dizini), "görseller", "1_Kur_Grafikleri")
    os.makedirs(cikti_klasoru, exist_ok=True)
    os.makedirs(gorsel_klasoru, exist_ok=True)
    
    # Görselleştirme
    print("Grafikler oluşturuluyor...")
    grafik_ayarlari = [
        ('TL_AYLIK', 'TL Dolar Bazlı Aylık Ortalama', '1_TL_Aylik.png', 'blue'),
        ('TL_CEYREK', 'TL Dolar Bazlı Çeyrek Ort.', '2_TL_Ceyrek.png', 'darkblue'),
        ('EURO_AYLIK', 'Euro Dolar Bazlı Aylık Ort.', '3_Euro_Aylik.png', 'green'),
        ('EURO_CEYREK', 'Euro Dolar Bazlı Çeyrek Ort.', '4_Euro_Ceyrek.png', 'darkgreen')
    ]

    for key, baslik, dosya_adi, renk in grafik_ayarlari:
        df = sayfa_verileri[key]
        plt.figure(figsize=(12, 6))
        plt.plot(range(len(df)), df['Ortalama Değer ($)'], marker='o', color=renk, linestyle='-', markersize=4)
        
        # X ekseni etiketlerini seyrelt (Çok fazla veri olabilir)
        step = max(len(df) // 10, 1)
        plt.xticks(range(0, len(df), step), df.index[::step], rotation=45)
        
        plt.title(baslik, fontsize=14, weight='bold')
        plt.xlabel('Dönem')
        plt.ylabel('Değer ($)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(os.path.join(gorsel_klasoru, dosya_adi), dpi=300)
        plt.close()

    cikti_dosyasi = os.path.join(cikti_klasoru, "doviz_ortalamalari.xlsx")
    print(f"Veriler kaydediliyor: {cikti_dosyasi}...")
    
    try:
        with pd.ExcelWriter(cikti_dosyasi, engine='openpyxl') as writer:
            for sayfa_adi, df in sayfa_verileri.items():
                df.to_excel(writer, sheet_name=sayfa_adi)
        print("İşlem başarıyla tamamlandı.")
    except Exception as e:
        print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    kurlari_cek_ve_hesapla()
