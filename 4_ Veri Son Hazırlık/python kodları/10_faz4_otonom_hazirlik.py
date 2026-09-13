import os
import sys
import subprocess

# --- KULLANICI MODÜLÜ ENTEGRASYONU ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    if project_root not in sys.path:
        sys.path.append(project_root)
    import kullanici as kb
except ImportError:
    print("Hata: 'kullanici.py' bulunamadı.")
    exit(1)

# --- YOLLAR ---
BASE_PATH = kb.klasor
SCRIPTS_DIR = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık", "python kodları")

def run_pipeline(currency_suffix):
    input_files = {
        "USD": "6_Final_Veri_USD_Synced.xlsx",
        "EUR": "6_Final_Veri_EUR_Synced.xlsx",
        "TRY": "6_Final_Veri_TRY_Synced.xlsx"
    }
    
    print(f"\n--- FAZ 4: {currency_suffix} SÜRECİ BAŞLIYOR ---")
    
    # Step 1: Winsorization
    input_file = input_files[currency_suffix]
    cmd1 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s1 = importlib.import_module('1_aykiri_deger_winsorization'); s1.run_winsorization('{input_file}')"
    subprocess.run([sys.executable, "-c", cmd1])
    
    # Step 2: Shifting
    step1_out = f"1_Aykiri_Temiz_Veri_{currency_suffix}.xlsx"
    cmd2 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s2 = importlib.import_module('2_hedef_degisken_kaydirma'); s2.run_target_shifting('{step1_out}')"
    subprocess.run([sys.executable, "-c", cmd2])
    
    # Step 3: Filtering Matrix
    step2_out = f"2_Hedef_Kaydirilmis_Veri_{currency_suffix}.xlsx"
    cmd3 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s3 = importlib.import_module('3_zeki_firma_eleme_matrisi'); s3.run_firm_filtering('{step2_out}')"
    subprocess.run([sys.executable, "-c", cmd3])

    # Step 4: Anomaly Integration
    step3_out = f"3_Final_Filtreli_Veri_{currency_suffix}.xlsx"
    cmd4 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s4 = importlib.import_module('4_anomali_entegrasyonu'); s4.run_anomaly_integration('{step3_out}')"
    subprocess.run([sys.executable, "-c", cmd4])

    # Step 5: Mevsimsellik Integration
    step4_out = f"4_Final_Anomali_Entegre_Veri_{currency_suffix}.xlsx"
    cmd5 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s5 = importlib.import_module('5_mevsimsellik_ekleme'); s5.run_seasonality_integration('{step4_out}')"
    subprocess.run([sys.executable, "-c", cmd5])

    # Step 6: Kümülatif Net Kar ve Sektör Kıyaslaması (Yeni Adım 1)
    step5_out = f"5_Final_Mevsimsellik_Entegre_Veri_{currency_suffix}.xlsx"
    cmd6 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s6 = importlib.import_module('6_kumulatif_kar_sektor_kiyaslamasi'); s6.run_cumulative_sector_comparison('{step5_out}')"
    subprocess.run([sys.executable, "-c", cmd6])

    # Step 7: Cari Dönem Sektörel Görece Durum (Yeni Adım 2)
    step6_out = f"6_Final_Kumulatif_Sektor_Kiyaslamasi_{currency_suffix}.xlsx"
    cmd7 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s7 = importlib.import_module('7_cari_donem_sektor_kiyaslamasi'); s7.run_current_period_sector_comparison('{step6_out}')"
    subprocess.run([sys.executable, "-c", cmd7])

    # Step 8: Mevsimsel Geçmiş ve Sektörel Mevsimsel Kıyas (Yeni Adım 3)
    step7_out = f"7_Final_Cari_Donem_Sektor_Kiyaslamasi_{currency_suffix}.xlsx"
    cmd8 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s8 = importlib.import_module('8_mevsimsel_gecmis_sektor_kiyaslamasi'); s8.run_seasonal_history_sector_comparison('{step7_out}')"
    subprocess.run([sys.executable, "-c", cmd8])

    # Step 9: Sektörel Akran Kıyaslama (Yeni Adım 4)
    step8_out = f"8_Final_Mevsimsel_Gecmis_Sektor_Kiyaslamasi_{currency_suffix}.xlsx"
    cmd9 = f"import sys; sys.path.append(r'{SCRIPTS_DIR}'); import importlib; s9 = importlib.import_module('9_sektorel_akran_kiyaslama'); s9.run_peer_benchmarking('{step8_out}')"
    subprocess.run([sys.executable, "-c", cmd9])

def main():
    print("\n" + "="*80)
    print("   PHASE 4: OTONOM VERİ SON HAZIRLIK ZİNCİRİ (9 ADIM)")
    print("="*80)
    
    currencies = ["USD", "EUR", "TRY"]
    for cur in currencies:
        run_pipeline(cur)
        
    print("\n" + "="*80)
    print("   PHASE 4 TAMAMLANDI: TÜM KURLAR İŞLENDİ (GÖRECE & AKRAN ÖZNİTELİKLERİ EKLENDİ)")
    print("="*80)

if __name__ == "__main__":
    main()
