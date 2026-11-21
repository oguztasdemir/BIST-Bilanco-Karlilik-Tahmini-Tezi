import os
import sys
import json
import shutil
import subprocess
import pandas as pd

# ============================================================
#   ADIM 13: OTONOM VERİ İŞLEME SİSTEMİ (MASTER WRAPPER)
#   Orijinal scriptleri (3, 7, 9, 10, 11, 12, 14) ardışık olarak çağırır.
# ============================================================

BASE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "1_Veri Manipulasyonu")
SCRIPTS_DIR = os.path.join(BASE_PATH, "python kodları")
DATASET_DIR = os.path.join(BASE_PATH, "0_Datasetler")

def run_script(script_name, args=None):
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"  [!] KRİTİK HATA: Script bulunamadı: {script_path}")
        return False
    cmd = [sys.executable, script_path]
    if args: cmd.extend(args)
    print(f"\n  [>>>] Başlatılıyor: {script_name} {' '.join(args) if args else ''}")
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n  [!] HATA: {script_name} başarısız oldu.")
        return False
    return True

def process_currency(kur):
    print(f"\n{'='*60}")
    print(f"  KUR İŞLENİYOR: {kur}")
    print(f"{'='*60}")

    # --- 1. HAZIRLIK: Başlangıç Ham Verisi ---
    source_data = os.path.join(DATASET_DIR, f"Veri_Havuzu_{kur}.xlsx")
    target_data_gen = os.path.join(DATASET_DIR, "Veri_Havuzu.xlsx")
    shutil.copy2(source_data, target_data_gen)

    # ADIMLARI SIRAYLA ÇALIŞTIR (CURRENCY ARGÜMANI İLE)
    # 1. Analiz
    if not run_script("1_veri_analizi_ana.py", [kur]): return False
    if not run_script("2_birlestirme_analizi.py", [kur]): return False
    
    # 3. Birleştirme
    if not run_script("3_veri_birlestirme.py", [kur]): return False
    
    # 4-5. Görselleştirme ve Eşik Analizi
    if not run_script("4_gorsellestirme.py", [kur]): return False
    if not run_script("5_doluluk_esik_analizi.py", [kur]): return False
    
    # Not: 6_manuel_gruplama_gui.py interaktif olduğu için otomasyona dahil edilmemiştir.
    
    # 7. Filtreleme
    if not run_script("7_final_veri_filtreleme.py", ["70", kur]): return False 
    
    # 8. İstatistiksel Analiz
    if not run_script("8_istatistiksel_onem_analizi.py", [kur]): return False
    
    # 9. Konsolidasyon
    if not run_script("9_gelir_gider_konsolidasyonu.py", [kur]): return False
    
    # 10. Medyan Doldurma
    if not run_script("10_sektorel_medyan_doldurma.py", [kur]): return False
    
    # 11-12. Raporlama
    if not run_script("11_veri_tamamlama_logu.py", [kur]): return False
    if not run_script("12_feature_takip_raporu.py", [kur]): return False
    
    # 14. Doğruluk Kontrolü
    if not run_script("14_dogruluk_kontrolu.py", [kur]): return False

    # 10. Sonuçları Taşı ve İsimlendir
    final_out = os.path.join(BASE_PATH, "raporlar", "10_Veri_Tamamlama", f"10_Medyan_Doldurulmus_Final_Veri_{kur}.xlsx")
    out_dir = os.path.join(BASE_PATH, "raporlar", "13_Otonom_Sistem")
    os.makedirs(out_dir, exist_ok=True)
    
    # TRY -> TL dönüşümü (Raporlama için)
    out_kur = "TL" if kur == "TRY" else kur
    
    save_path = os.path.join(out_dir, f"Final_Veri_{out_kur}.xlsx")
    if os.path.exists(final_out):
        shutil.copy2(final_out, save_path)
    
    # Log dosyasını taşı (İsim zaten kur bazlı: Doldurulan_Veriler_Log_USD.xlsx)
    log_name = f"Doldurulan_Veriler_Log_{kur}.xlsx"
    log_src = os.path.join(BASE_PATH, "raporlar", "11_Veri_Tamamlama_Logu", log_name)
    if os.path.exists(log_src):
        # Hedefte TL olarak kaydet
        target_log_name = f"Doldurulan_Veriler_Log_{out_kur}.xlsx"
        shutil.copy2(log_src, os.path.join(out_dir, target_log_name))

    print(f"  [+] {out_kur} için tüm adımlar tamamlandı.")
    return True

def main():
    print("\n" + "="*65)
    print("   ADIM 13: OTONOM VERİ İŞLEME SİSTEMİ (MASTER WRAPPER)")
    print("="*65)

    out_dir = os.path.join(BASE_PATH, "raporlar", "13_Otonom_Sistem")
    os.makedirs(out_dir, exist_ok=True)

    print("\n  1. Sadece USD\n  2. Sadece EUR\n  3. Sadece TL\n  4. TÜMÜ")
    sec = input("\n  Seçiminiz: ").strip()
    
    targets = {'1':['USD'], '2':['EUR'], '3':['TRY'], '4':['USD','EUR','TRY']}.get(sec, [])

    for kur in targets:
        process_currency(kur)

    print("\n" + "="*65)
    print("  TÜM İŞLEMLER TAMAMLANDI. Çıktılar: raporlar/13_Otonom_Sistem")
    print("="*65)

if __name__ == "__main__":
    main()
