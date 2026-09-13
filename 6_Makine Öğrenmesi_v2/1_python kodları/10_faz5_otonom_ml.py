import os
import sys
import subprocess
import time

currency = sys.argv[1].upper() if len(sys.argv) > 1 else "USD"
print(f"================================================================================")
# Use Turkish log messages as requested
print(f"BIST {currency} DODECA-PIPELINE (12-Adımlı ML Hattı) Başlatılıyor...")
print(f"================================================================================")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

ml_dir = os.path.join(kb.klasor, "6_Makine Öğrenmesi_v2")
kodlar_dir = os.path.join(ml_dir, "1_python kodları")
log_path = os.path.join(ml_dir, "3_çıktılar", f"Master_Run_{currency}.log")

# Clear existing log if any
if os.path.exists(log_path):
    try: os.remove(log_path)
    except: pass

steps = [
    ("Adım 1: Veri Ön İşleme & Anomali", "01_veri_on_isleme_ve_anomali_tespiti.py"),
    ("Adım 2: Zaman Serisi Özellik Mühendisliği", "02_zaman_serisi_ozellik_muhendisligi.py"),
    ("Adım 3: VIF Çoklu Doğrusal Bağlantı Filtresi", "03_vif_coklu_dogrusal_baglanti.py"),
    ("Adım 4: İleri Özellik Seçimi (RFE)", "04_ileri_ozellik_secimi_rfe.py"),
    ("Adım 5: Veri Ölçekleme (RobustScaler)", "05_veri_olcekleme.py"),
    ("Adım 6: Çok Yöntemli Regresyon Analizi", "06_cok_yontemli_regresyon_analizi.py"),
    ("Adım 7: Çoklu Hedefli Sınıflandırma", "07_coklu_hedefli_siniflandirma.py"),
    ("Adım 8: Bayesian Hiperparametre Görselleri", "08_hiperparametre_optimizasyonu_gorselleri.py"),
    ("Adım 9: Meta-Modelleme (Stacking Ensemble)", "09_meta_modelleme_stacking.py"),
    ("Adım 10: İstatistiksel Anlamlılık Testleri", "10_istatistiksel_anlamlilik_testleri.py"),
    ("Adım 11: Açıklanabilir Yapay Zeka (XAI)", "11_aciklanabilir_yapay_zeka_xai.py"),
    ("Adım 12: Nihai Tez Sentezi ve Master Rapor", "12_nihai_makale_sentezi_ve_master_excel.py")
]

def log_message(msg):
    print(msg)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

start_time = time.time()
log_message(f"Master Runner Başlangıç Saati: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

success = True
for name, script in steps:
    log_message(f"--- Çalıştırılıyor: {name} ({script}) ---")
    script_path = os.path.join(kodlar_dir, script)
    
    if not os.path.exists(script_path):
        log_message(f"HATA: {script} dosyası bulunamadı!\n")
        success = False
        break
        
    step_start = time.time()
    try:
        # Run python script as subprocess
        result = subprocess.run(
            ["python", script_path, currency],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        step_elapsed = time.time() - step_start
        
        # Log stdout and stderr
        with open(log_path, "a", encoding="utf-8") as lf:
            lf.write(f"=== STDOUT for {script} ===\n")
            lf.write(result.stdout + "\n")
            if result.stderr:
                lf.write(f"=== STDERR for {script} ===\n")
                lf.write(result.stderr + "\n")
                
        if result.returncode == 0:
            log_message(f"Başarıyla Tamamlandı. Süre: {step_elapsed:.2f} saniye.\n")
        else:
            log_message(f"HATA: {script} hata ile sonlandı! Hata Kodu: {result.returncode}")
            log_message(f"Detaylı bilgi için log dosyasına bakın: {log_path}\n")
            success = False
            break
            
    except Exception as e:
        log_message(f"HATA: {script} çalıştırılırken beklenmeyen istisna oluştu: {str(e)}\n")
        success = False
        break

total_elapsed = time.time() - start_time
log_message(f"================================================================================")
if success:
    log_message(f"ML İşlem Hattı Başarıyla Sonuçlandı! Toplam Süre: {total_elapsed:.2f} saniye.")
else:
    log_message(f"ML İşlem Hattı Hata Nedeniyle Yarım Kaldı!")
log_message(f"Log dosyası kaydedildi: {log_path}")
log_message(f"================================================================================")
