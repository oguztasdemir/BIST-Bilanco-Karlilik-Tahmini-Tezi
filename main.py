import os
import subprocess
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear_screen()
        print("="*70)
        print("             TEZ FIRMALAR VERI VE ANALIZ SISTEMI")
        print("="*70)
        
        print(" [ FAZ 0 - VERI TOPLAMA ]")
        print(" 1. Veri Cekme ve Sektorel Gruplama (Firmaları_cekme.py)")
        print("")
        
        print(" [ FAZ 1 - VERI MANIPULASYONU ]")
        print(" 2. Veri Analizi Ana (1_veri_analizi_ana.py)")
        print(" 3. Birlestirme Analizi (2_birlestirme_analizi.py)")
        print(" 4. Veri Birlestirme (3_veri_birlestirme.py)")
        print(" 5. Gorsellestirme (4_gorsellestirme.py)")
        print(" 6. Doluluk Esik Analizi (5_doluluk_esik_analizi.py)")
        print(" 7. Manuel Gruplama GUI (6_manuel_gruplama_gui.py)")
        print(" 8. Final Veri Filtreleme (7_final_veri_filtreleme.py)")
        print(" 9. Istatistiksel Onem Analizi (8_istatistiksel_onem_analizi.py)")
        print(" 10. Gelir Gider Konsolidasyonu (9_gelir_gider_konsolidasyonu.py)")
        print(" 11. Sektorel Medyan Doldurma (10_sektorel_medyan_doldurma.py)")
        print(" 12. Veri Tamamlama Logu (11_veri_tamamlama_logu.py)")
        print(" 13. Feature Takip Raporu (12_feature_takip_raporu.py)")
        print(" 14. Cok Kurlu Toplam Isleme (13_cok_kurlu_toplam_isleme.py)")
        print(" 15. Dogruluk Kontrolu (14_dogruluk_kontrolu.py)")
        print("")
        
        print(" [ FAZ 2 - KUR VE DOLARIZASYON ]")
        print(" 16. Doviz Kuru Hesaplamalari (1_doviz_hesaplama.py)")
        print(" 17. Bilanco Dolarizasyonu (2_bilanco_dolarizasyon.py)")
        print(" 18. Zaman Serisi Indeksleme (3_zaman_serisi_indeksleme.py)")
        print("")
        
        print(" [ FAZ 3 - OZELLIK SECIMI ]")
        print(" 19. Varyans Esigi Filtresi (1_varyans_esigi_filtresi.py)")
        print(" 20. Hedef Pearson Filtresi (2_hedef_pearson_filtresi.py)")
        print(" 21. Coklu Dogrusallik - VIF (3_coklu_dogrusallik_vif_filtresi.py)")
        print(" 22. Final Ozellik Sozlugu (4_final_ozellik_sozlugu.py)")
        print(" 23. Final Tablo Gorsellestirme (5_final_tablo_gorsellestirme.py)")
        print(" 24. Kur Oznitelik Senkronizasyonu (6_kur_oznitelik_senkronizasyonu.py)")
        print(" 25. Doluluk Orani Gorsellestirme (7_doluluk_orani_gorsellestirme.py)")
        print("")
        
        print(" [ FAZ 4 - VERI SON HAZIRLIK ]")
        print(" 26. Aykiri Deger Temizligi (1_aykiri_deger_winsorization.py)")
        print(" 27. Hedef Degisken Kaydirma (2_hedef_degisken_kaydirma.py)")
        print(" 28. Zeki Firma Eleme Matrisi (3_zeki_firma_eleme_matrisi.py)")
        print(" 29. Anomali Entegrasyonu (4_anomali_entegrasyonu.py)")
        print(" 30. Mevsimsellik Ekleme (5_mevsimsellik_ekleme.py)")
        print(" 31. Kumulatif Net Kar Sektor Kiyaslamasi (6_kumulatif_kar_sektor_kiyaslamasi.py)")
        print(" 32. Cari Donem Sektor Kiyaslamasi (7_cari_donem_sektor_kiyaslamasi.py)")
        print(" 33. Mevsimsel Gecmis Sektor Kiyaslamasi (8_mevsimsel_gecmis_sektor_kiyaslamasi.py)")
        print(" 34. Sektörel Akran Kıyaslama (9_sektorel_akran_kiyaslama.py)")
        
        print("-" * 70)
        print(" A. [OTONOM] VERI CEKME")
        print(" B. [OTONOM] VERI MANIPULASYONU (Faz 1)")
        print(" C. [OTONOM] KUR HESAPLAMA (Faz 2)")
        print(" D. [OTONOM] OZELLIK SECIMI (Faz 3)")
        print(" E. [OTONOM] VERI SON HAZIRLIK (Faz 4)")
        print(" F. [OTONOM] HEPSINI SIRAYLA YAP (Faz 0 -> 4)")
        print(" W. [WEB] WEB ARAYUZUNU BASLAT")
        print("-" * 70)
        print(" Q. CIKIS")
        
        sec = input("\n Seciminiz: ").upper()
        if sec == 'Q': 
            print("\n [!] Cikiliyor...")
            break
        
        # Mapping for individual scripts
        paths = {
            '1': ("0_Veri Çekme", "Firmaları_cekme.py"),
            '2': ("1_Veri Manipulasyonu/python kodları", "1_veri_analizi_ana.py"),
            '3': ("1_Veri Manipulasyonu/python kodları", "2_birlestirme_analizi.py"),
            '4': ("1_Veri Manipulasyonu/python kodları", "3_veri_birlestirme.py"),
            '5': ("1_Veri Manipulasyonu/python kodları", "4_gorsellestirme.py"),
            '6': ("1_Veri Manipulasyonu/python kodları", "5_doluluk_esik_analizi.py"),
            '7': ("1_Veri Manipulasyonu/python kodları", "6_manuel_gruplama_gui.py"),
            '8': ("1_Veri Manipulasyonu/python kodları", "7_final_veri_filtreleme.py"),
            '9': ("1_Veri Manipulasyonu/python kodları", "8_istatistiksel_onem_analizi.py"),
            '10': ("1_Veri Manipulasyonu/python kodları", "9_gelir_gider_konsolidasyonu.py"),
            '11': ("1_Veri Manipulasyonu/python kodları", "10_sektorel_medyan_doldurma.py"),
            '12': ("1_Veri Manipulasyonu/python kodları", "11_veri_tamamlama_logu.py"),
            '13': ("1_Veri Manipulasyonu/python kodları", "12_feature_takip_raporu.py"),
            '14': ("1_Veri Manipulasyonu/python kodları", "13_cok_kurlu_toplam_isleme.py"),
            '15': ("1_Veri Manipulasyonu/python kodları", "14_dogruluk_kontrolu.py"),
            '16': ("2_Kur Hesaplama ve Veriyi Hazırlama/python kodları", "1_doviz_hesaplama.py"),
            '17': ("2_Kur Hesaplama ve Veriyi Hazırlama/python kodları", "2_bilanco_dolarizasyon.py"),
            '18': ("2_Kur Hesaplama ve Veriyi Hazırlama/python kodları", "3_zaman_serisi_indeksleme.py"),
            '19': ("3_Özellik Seçimi/python kodları", "1_varyans_esigi_filtresi.py"),
            '20': ("3_Özellik Seçimi/python kodları", "2_hedef_pearson_filtresi.py"),
            '21': ("3_Özellik Seçimi/python kodları", "3_coklu_dogrusallik_vif_filtresi.py"),
            '22': ("3_Özellik Seçimi/python kodları", "4_final_ozellik_sozlugu.py"),
            '23': ("3_Özellik Seçimi/python kodları", "5_final_tablo_gorsellestirme.py"),
            '24': ("3_Özellik Seçimi/python kodları", "6_kur_oznitelik_senkronizasyonu.py"),
            '25': ("3_Özellik Seçimi/python kodları", "7_doluluk_orani_gorsellestirme.py"),
            '26': ("4_ Veri Son Hazırlık/python kodları", "1_aykiri_deger_winsorization.py"),
            '27': ("4_ Veri Son Hazırlık/python kodları", "2_hedef_degisken_kaydirma.py"),
            '28': ("4_ Veri Son Hazırlık/python kodları", "3_zeki_firma_eleme_matrisi.py"),
            '29': ("4_ Veri Son Hazırlık/python kodları", "4_anomali_entegrasyonu.py"),
            '30': ("4_ Veri Son Hazırlık/python kodları", "5_mevsimsellik_ekleme.py"),
            '31': ("4_ Veri Son Hazırlık/python kodları", "6_kumulatif_kar_sektor_kiyaslamasi.py"),
            '32': ("4_ Veri Son Hazırlık/python kodları", "7_cari_donem_sektor_kiyaslamasi.py"),
            '33': ("4_ Veri Son Hazırlık/python kodları", "8_mevsimsel_gecmis_sektor_kiyaslamasi.py"),
            '34': ("4_ Veri Son Hazırlık/python kodları", "9_sektorel_akran_kiyaslama.py")
        }

        if sec in paths:
            cwd, script = paths[sec]
            subprocess.run([sys.executable, script], cwd=cwd)
            input("\nDevam etmek icin Enter...")

        elif sec == 'A':
            subprocess.run([sys.executable, "Firmaları_cekme.py"], cwd="0_Veri Çekme")
            input("\nVeri Cekme tamamlandi...")

        elif sec == 'B':
            print("\n[OTONOM] Veri Manipulasyonu Baslatiliyor...")
            ph1_scripts = ["1_veri_analizi_ana.py", "3_veri_birlestirme.py", "7_final_veri_filtreleme.py", "10_sektorel_medyan_doldurma.py", "13_cok_kurlu_toplam_isleme.py"]
            for s in ph1_scripts:
                print(f"\n>>> Calisiyor: {s}")
                subprocess.run([sys.executable, s], cwd="1_Veri Manipulasyonu/python kodları")
            input("\nVeri Manipulasyonu tamamlandi...")

        elif sec == 'C':
            print("\n[OTONOM] Kur Hesaplama Baslatiliyor...")
            ph2_scripts = ["1_doviz_hesaplama.py", "2_bilanco_dolarizasyon.py", "3_zaman_serisi_indeksleme.py"]
            for s in ph2_scripts:
                print(f"\n>>> Calisiyor: {s}")
                subprocess.run([sys.executable, s], cwd="2_Kur Hesaplama ve Veriyi Hazırlama/python kodları")
            input("\nKur Hesaplama tamamlandi...")

        elif sec == 'D':
            print("\n[OTONOM] Ozellik Secimi Baslatiliyor...")
            subprocess.run([sys.executable, "8_ozellik_secimi_otonomu.py"], cwd="3_Özellik Seçimi/python kodları")
            input("\nOzellik Secimi tamamlandi...")

        elif sec == 'E':
            print("\n[OTONOM] Veri Son Hazirlik Baslatiliyor...")
            subprocess.run([sys.executable, "10_faz4_otonom_hazirlik.py"], cwd="4_ Veri Son Hazırlık/python kodları")
            input("\nVeri Son Hazirlik tamamlandi...")

        elif sec == 'F':
            print("\n[OTONOM] TUM SISTEM CALISTIRILIYOR...")
            subprocess.run([sys.executable, "Firmaları_cekme.py"], cwd="0_Veri Çekme")
            ph1_scripts = ["1_veri_analizi_ana.py", "3_veri_birlestirme.py", "7_final_veri_filtreleme.py", "10_sektorel_medyan_doldurma.py", "13_cok_kurlu_toplam_isleme.py"]
            for s in ph1_scripts: subprocess.run([sys.executable, s], cwd="1_Veri Manipulasyonu/python kodları")
            ph2_scripts = ["1_doviz_hesaplama.py", "2_bilanco_dolarizasyon.py", "3_zaman_serisi_indeksleme.py"]
            for s in ph2_scripts: subprocess.run([sys.executable, s], cwd="2_Kur Hesaplama ve Veriyi Hazırlama/python kodları")
            subprocess.run([sys.executable, "8_ozellik_secimi_otonomu.py"], cwd="3_Özellik Seçimi/python kodları")
            subprocess.run([sys.executable, "10_faz4_otonom_hazirlik.py"], cwd="4_ Veri Son Hazırlık/python kodları")
            input("\nTum sistem calismasi tamamlandi...")

        elif sec == 'W':
            print("\n[WEB] Web Arayüzü Başlatılıyor...")
            try:
                import flask
            except ImportError:
                print(" [!] Flask kütüphanesi eksik! Kuruluyor...")
                subprocess.run([sys.executable, "-m", "pip", "install", "flask"])
            
            subprocess.run([sys.executable, "main.py"], cwd="8_Arayuz")

if __name__ == "__main__":
    main()
