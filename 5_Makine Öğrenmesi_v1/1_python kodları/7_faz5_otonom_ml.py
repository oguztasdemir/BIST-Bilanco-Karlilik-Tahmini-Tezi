import os
import sys
import subprocess
import time
import logging

# ── Log dosyası kurulumu ───────────────────────────────────────────────────────
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import kullanici as kb

log_path = os.path.join(kb.klasor, "5_Makine Öğrenmesi_v1", "3_çıktılar", "master_ml_run.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("ML_PIPELINE")


def run_script(step_name: str, script_path: str, currency: str) -> bool:
    log.info(f"{'='*70}")
    log.info(f"BAŞLIYOR: {step_name}  |  Para Birimi: {currency}")
    log.info(f"Script: {script_path}")

    start = time.time()
    result = subprocess.run(
        [sys.executable, "-u", script_path, currency],
        capture_output=False,
    )
    elapsed = time.time() - start

    if result.returncode == 0:
        log.info(f"BAŞARILI: {step_name} — {elapsed:.1f} saniye")
        return True
    else:
        log.error(f"BAŞARISIZ: {step_name} — Çıkış kodu {result.returncode}  ({elapsed:.1f} saniye)")
        return False


def run_pipeline_for_currency(currency: str, scripts: list[tuple[str, str]]) -> int:
    log.info(f"\n{'#'*70}")
    log.info(f"# PARA BİRİMİ BLOĞU BAŞLIYOR: {currency}")
    log.info(f"{'#'*70}")

    ok = 0
    for step_name, filename in scripts:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if not os.path.exists(script_path):
            log.error(f"Script bulunamadı: {script_path}")
            return ok

        success = run_script(step_name, script_path, currency)
        if success:
            ok += 1
        else:
            log.error(f"Pipeline '{currency}' para birimi için {step_name} adımında durdu.")
            sys.exit(1)

    return ok


def main():
    CURRENCIES = ["USD", "EUR", "TRY"]

    SCRIPTS = [
        ("Adım 1 — Veri Ön İşleme & Anomali Temizleme",    "1_veri_on_isleme_anomali.py"),
        ("Adım 2 — Çoklu Doğrusal Bağlantı (VIF) Filtresi","2_coklu_dogrusal_baglanti_vif.py"),
        ("Adım 3 — Çok Yöntemli Regresyon Analizi",         "3_cok_yontemli_regresyon_analizi.py"),
        ("Adım 4 — Çoklu Hedefli Sınıflandırma",            "4_coklu_hedefli_siniflandirma.py"),
        ("Adım 5 — Açıklanabilir Yapay Zeka (SHAP / XAI)",  "5_aciklanabilir_yapay_zeka_xai.py"),
        ("Adım 6 — Nihai Sentez & Jüri Savunma Rehberi",    "6_nihai_tez_sentezi_yonetici_ozeti.py"),
    ]

    log.info("="*70)
    log.info(" BIST MAKİNE ÖĞRENMESİ PIPELINE — FAZ 5 OTONOM ÇALIŞTIRICISI")
    log.info(f" Para birimleri: {', '.join(CURRENCIES)}")
    log.info("="*70)

    total_start  = time.time()
    total_ok     = 0
    total_expect = len(SCRIPTS) * len(CURRENCIES)

    for currency in CURRENCIES:
        ok = run_pipeline_for_currency(currency, SCRIPTS)
        total_ok += ok

    total_elapsed = time.time() - total_start

    log.info("\n" + "="*70)
    log.info(" PIPELINE TAMAMLANDI")
    log.info(f" Başarılı adım: {total_ok} / {total_expect}")
    log.info(f" Toplam süre  : {total_elapsed/60:.1f} dakika")
    log.info("="*70)


if __name__ == "__main__":
    main()
