import os
import sys
import time
import re
import threading
import json
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------------
# CONFIGURATION & PATH SETUP
# ------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Access kullanici.py and Project Root
PROJECT_ROOT = SCRIPT_DIR
while True:
    if os.path.exists(os.path.join(PROJECT_ROOT, 'kullanici.py')):
        if PROJECT_ROOT not in sys.path:
            sys.path.append(PROJECT_ROOT)
        break
    parent_path = os.path.dirname(PROJECT_ROOT)
    if parent_path == PROJECT_ROOT:
        break
    PROJECT_ROOT = parent_path

try:
    import kullanici as kb
    GÖRSEL_KLASORU = os.path.join(SCRIPT_DIR, "Gorseller")
    os.makedirs(GÖRSEL_KLASORU, exist_ok=True)
except ImportError:
    print("Hata: 'kullanici.py' bulunamadı.")
    sys.exit()

# File Paths (Organized in Datalar folder)
DATA_DIR = os.path.join(SCRIPT_DIR, "Datalar")
os.makedirs(DATA_DIR, exist_ok=True)

PATH_RAW_LIST = os.path.join(DATA_DIR, "1_firmalar.txt")
PATH_CLEAN_LIST = os.path.join(DATA_DIR, "2_firmalar_temiz.txt")
PATH_BLACKLIST = os.path.join(DATA_DIR, "3_hatali_firmalar.txt")
PATH_SECTOR_JSON = os.path.join(DATA_DIR, "5_sektorler.json")
PATH_SECTOR_ANA_JSON = os.path.join(DATA_DIR, "6_sektorler_ana.json")
PATH_MANIP_DATASET = os.path.join(PROJECT_ROOT, "1_Veri Manipulasyonu", "0_Datasetler")
os.makedirs(PATH_MANIP_DATASET, exist_ok=True)

class FirmDataCollector:
    """
    Manages the entire firm data collection pipeline with Multi-Tab support.
    """

    def __init__(self):
        self.progress_lock = threading.Lock()
        self.processed_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.start_time = 0
        self.hatali_firmalar = self._load_list(PATH_BLACKLIST)
        self.lock = threading.Lock()

    def _load_list(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                return set(line.strip().upper() for line in f if line.strip())
        return set()

    def _save_list(self, path, data_list):
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(sorted(list(data_list))))

    def _get_work_list(self):
        """Returns Master List minus Blacklist (picks up new firms while skipping known dead ones)."""
        master = self._load_list(PATH_RAW_LIST)
        blacklist = self._load_list(PATH_BLACKLIST)
        return master - blacklist

    def _get_driver(self, headless=False, download_dir=None):
        """Centralized Selenium driver factory."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1280,720')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        if download_dir:
            chrome_options.add_experimental_option("prefs", {
                "download.default_directory": os.path.abspath(download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            })
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def _generate_excel_report(self, download_dir, label, suffix, firm_list):
        try:
            report_data = []
            present_files = os.listdir(download_dir) if os.path.exists(download_dir) else []
            for firma in firm_list:
                status = "Başarılı" if f"{firma} ({suffix}).xlsx" in present_files else "Başarısız"
                report_data.append({"Firma": firma, "Döviz": suffix, "Durum": status})
            df = pd.DataFrame(report_data)
            report_path = os.path.join(DATA_DIR, f"2_Indirme_Raporu_{label.upper()}.xlsx")
            df.to_excel(report_path, index=False)
            return df
        except: return None

    def _plot_pie_chart(self, filename, title, labels, values):
        try:
            plt.figure(figsize=(10, 7))
            colors = ['#2ecc71', '#e74c3c', '#95a5a6']
            final_labels, final_values = [], []
            for l, v in zip(labels, values):
                if v > 0:
                    final_labels.append(f"{l}\n({v})"); final_values.append(v)
            if not final_values: return
            plt.pie(final_values, labels=final_labels, autopct='%1.1f%%', startangle=140, colors=colors, wedgeprops={'edgecolor': 'white', 'linewidth': 2})
            centre_circle = plt.Circle((0,0), 0.70, fc='white'); plt.gca().add_artist(centre_circle)
            self._apply_style(title)
            plt.savefig(os.path.join(GÖRSEL_KLASORU, filename), bbox_inches='tight'); plt.close()
        except: pass

    def _get_downloaded_set(self, folder):
        if not os.path.exists(folder): return set()
        found = set()
        for filename in os.listdir(folder):
            if filename.lower().endswith(".xlsx"):
                match = re.match(r"(.+)\s\((.+)\).xlsx", filename, re.IGNORECASE)
                if match: found.add(f"{match.group(1).strip().upper()}_{match.group(2).strip().upper()}")
        return found

    def _cleanup_duplicates(self, folder_path):
        if not os.path.exists(folder_path): return 0
        count, pattern = 0, re.compile(r".* \(\d+\)\.xlsx$")
        for filename in os.listdir(folder_path):
            if pattern.match(filename):
                try: os.remove(os.path.join(folder_path, filename)); count += 1
                except: pass
        return count

    def _apply_style(self, title_text):
        plt.style.use('bmh')
        plt.title(title_text, fontsize=14, fontweight='bold', pad=15, color='#2c3e50')
        plt.grid(axis='y', linestyle='--', alpha=0.6); plt.tight_layout()

    def _plot_summary(self, filename, title, labels, values, colors=None, rotation=0, figsize=(10, 6), fontsize=10, note=None):
        try:
            plt.figure(figsize=figsize)
            bars = plt.bar(labels, values, color=colors if colors else ['#3498db', '#2980b9', '#2c3e50', '#16a085'])
            
            # Add labels on top of each bar
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                         f'{int(height)}', ha='center', va='bottom', fontsize=fontsize, fontweight='bold')
            
            self._apply_style(title)
            
            # Add note if provided (top-right)
            if note:
                plt.text(0.99, 0.98, note, transform=plt.gca().transAxes, 
                         ha='right', va='top', fontsize=9, style='italic', 
                         color='#7f8c8d', bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))
            
            plt.xticks(rotation=rotation, ha='right')
            plt.savefig(os.path.join(GÖRSEL_KLASORU, filename), bbox_inches='tight')
            plt.close()
        except Exception as e:
            print(f"[HATA] Grafik oluşturulamadı: {e}")

    def _print_header(self, text):
        border = "=" * 60
        print(f"\n{border}\n {text.center(58)} \n{border}")

    def _print_progress(self, total, current_firma):
        elapsed = time.time() - self.start_time
        avg_time = elapsed / self.processed_count if self.processed_count > 0 else 0
        eta_sec = int(avg_time * (total - self.processed_count))
        pct = (self.processed_count / total) * 100
        bar = '#' * int(30 * self.processed_count / total) + '-' * (30 - int(30 * self.processed_count / total))
        sys.stdout.write(f"\r|{bar}| %{pct:.1f} [{self.processed_count}/{total}] - Kalan: {eta_sec}sn - {current_firma}   ")
        sys.stdout.flush()

    def update_ticker_list(self):
        self._print_header("FİRMA LİSTESİ GÜNCELLEME (RADAR - STEP 1)")
        driver = self._get_driver(headless=False)
        try:
            driver.get("https://fintables.com/radar/hisse-senetleri")
            driver.set_window_position(3000, 3000) # Background mode
            driver.maximize_window()
            time.sleep(5)
            
            firmalar_found = set()
            last_count, same_repeat, actions = 0, 0, ActionChains(driver)
            print("[!] Arka planda tarama başlatıldı (Cihaz ekranını bozmaz)...")
            
            for i in range(500):
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                for row in rows:
                    try:
                        href = row.find_element(By.XPATH, ".//a[contains(@href, '/sirketler/')]").get_attribute("href")
                        firmalar_found.add(href.rstrip("/").split("/")[-1].upper())
                    except: continue
                
                if len(firmalar_found) == last_count: same_repeat += 1
                else: same_repeat = 0; print(f"Scroll {i} -> Toplam: {len(firmalar_found)}")
                if same_repeat >= 12: break
                last_count = len(firmalar_found)
                
                try:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", rows[-1])
                    time.sleep(1.2); actions.send_keys(Keys.PAGE_DOWN).perform()
                except: driver.execute_script("window.scrollBy(0, 1000);"); time.sleep(1.0)
            
            mevcut = self._load_list(PATH_RAW_LIST)
            tumu = mevcut | firmalar_found
            self._save_list(PATH_RAW_LIST, tumu)
            print(f"\n[BAŞARILI] Master liste güncellendi. Yeni: {len(firmalar_found - mevcut)} | Toplam: {len(tumu)}")
            self._plot_summary("1_Radar_Ozet.png", "Radar Veri Çekme Özeti", ['Mevcut', 'Yeni', 'Sitede'], [len(mevcut), len(firmalar_found - mevcut), len(firmalar_found)])
        finally: driver.quit()

    def download_excels(self, currency, custom_list=None):
        label = "euro" if currency == "eur" else ("usd" if currency == "usd" else "tl")
        suffix = currency.upper() if currency != "try" else "TRY"
        download_dir = os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", f"fintables_excel_{label}")
        os.makedirs(download_dir, exist_ok=True)
        
        # Reporting should be based on the FULL Master List (633 firms) for total context
        source_list = custom_list if custom_list else list(self._load_list(PATH_RAW_LIST))
        downloaded = self._get_downloaded_set(download_dir)
        
        should_download = True
        if downloaded and not custom_list:
            mtime = os.path.getmtime(os.path.join(download_dir, os.listdir(download_dir)[0]))
            dt_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
            self._print_header("MEVCUT VERİ BULUNDU")
            print(f"[?] {label.upper()} verileri zaten mevcut ({dt_str} tarihinde indirilmiş).")
            ans = input("Yeniden indirilsin mi? (e: Yeniden İndir / h: Sadece Raporla): ").lower()
            if ans != 'e': should_download = False
            
        # Download queue should EXCLUDE the blacklist to prevent retrying broken firms
        blacklist = self._load_list(PATH_BLACKLIST)
        firmalar = [f for f in source_list if f"{f.upper()}_{suffix}" not in downloaded and f not in blacklist] if should_download else []
        total = len(firmalar)
        
        if should_download and total > 0:
            self.processed_count = 0; self.success_count = 0; self.fail_count = 0; success_firms = []; fail_firms = []; self.start_time = time.time()
            print(f"\n[İŞLEM] {total} şirket için {label.upper()} indiriliyor (6 SEKME)...")
            driver = self._get_driver(download_dir=download_dir)
            try:
                num_tabs = min(6, total)
                tabs = [driver.current_window_handle]
                for _ in range(num_tabs - 1): driver.execute_script("window.open('about:blank');"); tabs.append(driver.window_handles[-1])
                tab_status = [{"active": False, "firma": None, "start_time": 0, "org_p": ""} for _ in range(num_tabs)]
                queue = firmalar.copy()
                while queue or any(t["active"] for t in tab_status):
                    for i in range(num_tabs):
                        ts = tab_status[i]
                        if ts["active"]:
                            if os.path.exists(ts["org_p"]) and os.path.getsize(ts["org_p"]) > 1024:
                                ts["active"] = False; self.success_count += 1; success_firms.append(ts["firma"]); self.processed_count += 1; self._print_progress(total, ts["firma"])
                            elif time.time() - ts["start_time"] > 25:
                                ts["active"] = False; self.fail_count += 1; fail_firms.append(ts["firma"]); self.processed_count += 1; self._print_progress(total, ts["firma"])
                        if not ts["active"] and queue:
                            ts["firma"] = queue.pop(0); ts["start_time"] = time.time(); ts["org_p"] = os.path.join(download_dir, f"{ts['firma']} ({suffix}).xlsx")
                            try: driver.switch_to.window(tabs[i]); driver.get(f"https://fintables.com/sirketler/{ts['firma']}/finansal-tablolar/excel/?currency={currency}"); ts["active"] = True
                            except: queue.insert(0, ts["firma"])
                    time.sleep(0.4)
            finally: driver.quit()
        
        self._cleanup_duplicates(download_dir); downloaded = self._get_downloaded_set(download_dir)
        self._plot_pie_chart(f"2_Indirme_{label.lower()}_Pasta.png", f"{label.upper()} Dağılımı", ['Mevcut', 'Eksik'], [len(downloaded), len(source_list)-len(downloaded)])
        self._generate_excel_report(download_dir, label, suffix, source_list)

    def smart_batch_download(self):
        self._print_header("3 KUR BAZLI AKILLI YÜKLEME (STEP 2)")
        for cur in ["eur", "usd", "try"]:
            self.download_excels(cur)

    def perform_audit(self, silent=False):
        self._print_header("DENETİM VE KARA LİSTE SENKRONİZASYONU (STEP 3)")
        kurlar = {"1": ("EUR", "eur", "euro", "EUR"), "2": ("USD", "usd", "usd", "USD"), "3": ("TRY", "try", "tl", "TRY"), "4": ("TÜMÜ", "all", "all", "ALL")}
        sec = "4" if silent else input("1. EUR | 2. USD | 3. TL | 4. TÜMÜ\nSeçim: ")
        sel = [kurlar["1"], kurlar["2"], kurlar["3"]] if sec == "4" else ([kurlar[sec]] if sec in kurlar else [])
        
        total_cleaned = 0
        for name, code, label, suffix in sel:
            fld = os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", f"fintables_excel_{label}")
            cleaned = self._cleanup_duplicates(fld)
            total_cleaned += cleaned
            if cleaned > 0: print(f"   [TEMİZLİK] {name} klasöründe {cleaned} kopya dosya silindi.")
        
        # --- BLACKLIST RECOVERY & SYNC ---
        print("\n[!] Nihai veri kontrolü ve kara liste senkronizasyonu yapılıyor...")
        master_list = self._load_list(PATH_RAW_LIST)
        self.hatali_firmalar = self._load_list(PATH_BLACKLIST)
        
        dead_firms, restored_firms = [], []
        folders = {
            "EUR": os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", "fintables_excel_euro"),
            "USD": os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", "fintables_excel_usd"),
            "TRY": os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", "fintables_excel_tl")
        }
        
        for firm in master_list:
            found_any = False
            for s, fld in folders.items():
                if os.path.exists(os.path.join(fld, f"{firm} ({s}).xlsx")):
                    found_any = True; break
            if not found_any and firm not in self.hatali_firmalar: dead_firms.append(firm)

        for firm in list(self.hatali_firmalar):
            found_any = False
            for s, fld in folders.items():
                if os.path.exists(os.path.join(fld, f"{firm} ({s}).xlsx")):
                    found_any = True; break
            if found_any: restored_firms.append(firm)

        if dead_firms: self.hatali_firmalar.update(dead_firms)
        if restored_firms:
            for f in restored_firms: self.hatali_firmalar.discard(f)
            print(f"   [-] {len(restored_firms)} firma kara listeden kurtarıldı.")
            
        self._save_list(PATH_BLACKLIST, self.hatali_firmalar)
        clean_list = master_list - self.hatali_firmalar
        self._save_list(PATH_CLEAN_LIST, clean_list)
        
        # Reporting
        tot_count, cln_count = len(master_list), len(clean_list)
        cur_counts = {s: sum(1 for f in master_list if os.path.exists(os.path.join(fld, f"{f} ({s}).xlsx"))) for s, fld in folders.items()}
        
        print(f" > Toplam: {tot_count}\n > Temiz: {cln_count}\n > Kara Liste: {len(self.hatali_firmalar)}")
        self._plot_summary("3_Denetim_Ozeti.png", "Envanter Raporu", 
                           ['Toplam', 'Temiz', 'TL', 'USD', 'EUR', 'Hata'], 
                           [tot_count, cln_count, cur_counts['TRY'], cur_counts['USD'], cur_counts['EUR'], len(self.hatali_firmalar)],
                           colors=['#2c3e50', '#16a085', '#2ecc71', '#3498db', '#9b59b6', '#e74c3c'])

    def run_sector_analysis(self, silent=False):
        self._print_header("DETAYLI SEKTÖR ANALİZİ (STEP 5)")
        all_viable = list(self._load_list(PATH_CLEAN_LIST)) if os.path.exists(PATH_CLEAN_LIST) else list(self._get_work_list())
        
        data = {}
        if os.path.exists(PATH_SECTOR_JSON):
            try:
                with open(PATH_SECTOR_JSON, "r", encoding="utf-8") as f: data = json.load(f)
            except: pass
        
        if not data or (not silent and input("Yeniden internetten çekilsin mi? (e/h): ").lower() == 'e'):
            driver = self._get_driver()
            try:
                driver.get("https://fintables.com/sektorler"); time.sleep(5)
                links = [{"name": (a.get_attribute("title") or a.text).replace(" Sektörü", "").strip(), "url": a.get_attribute("href")} for a in driver.find_elements(By.TAG_NAME, "a") if a.get_attribute("href") and "/sektorler/" in a.get_attribute("href") and not a.get_attribute("href").endswith("/sektorler")]
                for l in links:
                    print(f"Sektör: {l['name']}")
                    driver.get(l["url"]); time.sleep(1.5)
                    data[l['name']] = list(set(re.split(r'\s|\n', r.find_element(By.XPATH, ".//a[contains(@href, '/sirketler/')]").get_attribute("href").rstrip("/").split("/")[-1].upper())[0] for r in driver.find_elements(By.XPATH, "//table/tbody/tr") if "/sirketler/" in r.get_attribute('innerHTML')))
                with open(PATH_SECTOR_JSON, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
            finally: driver.quit()

        stats = {s: len([f for f in flist if f in all_viable]) for s, flist in data.items()}
        sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
        
        unique_count = len(all_viable)
        total_assignments = sum(sorted_stats.values())
        
        # Plotting Phase (Raw 44 Sectors) - Now Step 5
        title = f"Detaylı Sektör Dağılımı ({unique_count} Özgün Firma | {total_assignments} Kayıt)"
        note = "Not: Bir firma birden fazla sektörde bulunabilir."
        
        self._plot_summary("5_Sektor_Detayli.png", title, 
                           list(sorted_stats.keys()), list(sorted_stats.values()), 
                           colors=['#2980b9'], rotation=90, figsize=(16, 9), fontsize=7, note=note)
        
        # Excel Report (Step 5 - Detailed mapping)
        firm_to_subs = {}
        for sub, firms in data.items():
            for f in firms:
                if f in all_viable: firm_to_subs.setdefault(f, []).append(sub)
        
        sector_detay_data = []
        for f, subs in firm_to_subs.items():
            sector_detay_data.append({"Firma": f, "Sektör Sayısı": len(subs), "Sektörler": ", ".join(subs)})
        
        if sector_detay_data:
            df_detay = pd.DataFrame(sector_detay_data).sort_values(by="Sektör Sayısı", ascending=False)
            report_path = os.path.join(DATA_DIR, "5_Sektorel_Analiz_Detayli.xlsx")
            df_detay.to_excel(report_path, index=False)
            print(f" [BİLGİ] Detaylı sektör raporu oluşturuldu -> {os.path.basename(report_path)}")
            
        print(f"\n[TAMAM] Detaylı sektör grafiği ve raporu güncellendi (Step 5).")

    def run_strategic_grouping(self, silent=False):
        self._print_header("STRATEJİK SEKTÖR GRUPLAMA (STEP 6)")
        all_viable = list(self._load_list(PATH_CLEAN_LIST)) if os.path.exists(PATH_CLEAN_LIST) else list(self._get_work_list())
        
        if not os.path.exists(PATH_SECTOR_JSON):
            print("[HATA] Önce 5. Adımı çalıştırıp sektör verilerini çekmelisiniz.")
            return

        with open(PATH_SECTOR_JSON, "r", encoding="utf-8") as f: data = json.load(f)

        # 7 Ana Kategori Haritası
        MAIN_SECTOR_MAP = {
            "SANAYİ VE İMALAT": ["İmalat", "Ana Metal", "Metal Eşya ve Makine", "Otomotiv", "Otomotiv Yan Sanayi", "Savunma", "Ambalaj", "Kağıt ve Kağıt Ürünleri", "Kimya ve Plastik", "Cam, Seramik, Porselen", "Mobilya ve Dekorasyon", "Tekstil, Giyim ve Deri", "İlaç ve Sağlık"],
            "FİNANS VE YATIRIM": ["Bankacılık", "Sigorta", "Emeklilik", "Faktoring", "Finansal Kiralama", "Aracı Kurum", "Menkul Kıymet Yat. Ort.", "Girişim Sermayesi Yat. Ort.", "Tasarruf Finansman", "Holding", "Varlık Yönetimi"],
            "İNŞAAT VE GAYRİMENKUL": ["İnşaat", "Gayrimenkul", "Taş, Toprak, Çimento"],
            "TEKNOLOJİ VE HİZMET": ["Bilişim ve Yazılım", "Haberleşme", "Ulaştırma", "Servis Taşımacılığı ve Araç Kiralama", "Turizm", "Spor", "Destek ve Hizmet"],
            "ENERJİ VE HAMMADDE": ["Enerji Üretim ve Dağıtım", "Enerji Teknolojileri", "Madencilik ve Taş Ocakçılığı"],
            "GIDA VE TARIM": ["Gıda ve İçecek", "Tarım, Hayvancılık, Balıkçılık"],
            "TİCARET VE PAZARLAMA": ["Toptan ve Perakende Ticaret", "Gıda Perakendeciliği", "Teknolojik Ürün Ticareti", "Giyim, Tekstil ve Deri Ürünleri Perakendeciliği", "Dayanıklı Tüketim Ürünleri"]
        }

        ana_data = {}
        for main_cat, sub_cats in MAIN_SECTOR_MAP.items():
            combined_firms = set()
            for sub in sub_cats:
                if sub in data: combined_firms.update(data[sub])
            ana_data[main_cat] = list(combined_firms)
        
        with open(PATH_SECTOR_ANA_JSON, "w", encoding="utf-8") as f: json.dump(ana_data, f, ensure_ascii=False, indent=4)

        stats = {s: len([f for f in flist if f in all_viable]) for s, flist in ana_data.items()}
        sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
        
        unique_count = len(all_viable)
        total_assignments = sum(sorted_stats.values())
        
        # Excel Report
        firm_to_main = {}
        for main, firms in ana_data.items():
            for f in firms:
                if f in all_viable: firm_to_main.setdefault(f, []).append(main)
        
        sector_analysis_data = []
        for f, mains in firm_to_main.items():
            sector_analysis_data.append({"Firma": f, "Ana Sektör Sayısı": len(mains), "Ana Sektörler": ", ".join(mains)})
        
        if sector_analysis_data:
            df_sector = pd.DataFrame(sector_analysis_data).sort_values(by="Ana Sektör Sayısı", ascending=False)
            
            # Ana-Alt Sektör Eşleşme Tablosu (Yeni Sheet için)
            mapping_data = []
            for main, subs in MAIN_SECTOR_MAP.items():
                mapping_data.append({
                    "Ana Sektör": main, 
                    "Alt Sektör Sayısı": len(subs),
                    "Alt Sektörler": ", ".join(subs)
                })
            df_map = pd.DataFrame(mapping_data)

            report_path = os.path.join(DATA_DIR, "6_Sektorel_Analiz.xlsx")
            with pd.ExcelWriter(report_path, engine='xlsxwriter') as writer:
                # Firma Bazlı
                df_sector.to_excel(writer, sheet_name="Firma_Bazli_Analiz", index=False)
                sh1 = writer.sheets["Firma_Bazli_Analiz"]
                for i, col in enumerate(df_sector.columns):
                    w = max(df_sector[col].astype(str).map(len).max(), len(col)) + 2
                    sh1.set_column(i, i, min(w, 50))

                # Sektör Haritası
                df_map.to_excel(writer, sheet_name="Sektor_Haritasi", index=False)
                sh2 = writer.sheets["Sektor_Haritasi"]
                for i, col in enumerate(df_map.columns):
                    w = max(df_map[col].astype(str).map(len).max(), len(col)) + 2
                    sh2.set_column(i, i, min(w, 100))
                
            print(f" [BİLGİ] Stratejik analiz raporu (Optimize Edildi) oluşturuldu -> {os.path.basename(report_path)}")
        
        # Plotting Phase (Strategic 7) - Corrected to Step 6
        title = f"Stratejik Sektör Gruplandırması ({unique_count} Özgün Firma)"
        note = "Not: Bir firma birden fazla ana sektörde bulunabilir."
        self._plot_summary("6_Sektor_Gruplanmis.png", title, 
                           list(sorted_stats.keys()), list(sorted_stats.values()), 
                           colors=['#2980b9', '#3498db', '#2c3e50', '#16a085', '#9b59b6', '#e67e22', '#e74c3c'], 
                           rotation=45, figsize=(12, 7), fontsize=10, note=note)
        
        print(f"\n[TAMAM] Stratejik gruplandırma grafiği (6_Sektor_Gruplanmis.png) ve raporu güncellendi.")

    def run_integrity_check(self):
        self._print_header("VERİ BÜTÜNLÜĞÜ VE DENETİM (STEP 8)")
        
        import math
        import random
        
        kurlar = [("EUR", "eur", "euro", "EUR"), ("USD", "usd", "usd", "USD"), ("TRY", "try", "tl", "TRY")]
        all_results = []
        total_cells_checked = 0
        total_matches = 0
        
        for name, code, label, suffix in kurlar:
            pool_path = os.path.join(PATH_MANIP_DATASET, f"Veri_Havuzu_{name}.xlsx")
            source_dir = os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", f"fintables_excel_{label}")
            
            if not os.path.exists(pool_path):
                continue
                
            print(f"\n[*] {name} Havuzu için %100 Hücre Denetimi başlatılıyor...")
            xls_pool = pd.ExcelFile(pool_path)
            
            df_pool_list = []
            for sh in xls_pool.sheet_names:
                df_pool_list.append(pd.read_excel(pool_path, sheet_name=sh))
            df_pool = pd.concat(df_pool_list, ignore_index=True)
            df_pool = df_pool.drop_duplicates(subset=['Firma Adı', 'Dönem'])
            
            firms_in_pool = df_pool['Firma Adı'].unique()
            total_firms = len(firms_in_pool)
            
            def make_unique_local(cols):
                counts = {}; new_cols = []
                for c in cols:
                    clean = str(c).split('.')[0].strip()
                    counts[clean] = counts.get(clean, 0) + 1
                    new_cols.append(f"{clean}_{counts[clean]}" if counts[clean] > 1 else clean)
                return new_cols
                
            for idx, firm in enumerate(firms_in_pool, 1):
                self._print_progress_raw(total_firms, idx, f"Kontrol: {firm[:10]}")
                raw_file = os.path.join(source_dir, f"{firm} ({suffix}).xlsx")
                if not os.path.exists(raw_file): continue
                
                try:
                    xls_raw = pd.ExcelFile(raw_file)
                    df_bil_temp = pd.read_excel(raw_file, sheet_name=xls_raw.sheet_names[0])
                    df_bil_temp['Kalem'] = df_bil_temp['Kalem'].astype(str).str.strip()
                    df_bil_raw = df_bil_temp.groupby('Kalem').first()
                    df_bil_raw.columns = make_unique_local(df_bil_raw.columns)
                    df_bil = df_bil_raw.T

                    sheet_don = [s for s in xls_raw.sheet_names if 'Dönemsel' in s or 'Donemsel' in s][0]
                    df_don_temp = pd.read_excel(raw_file, sheet_name=sheet_don)
                    df_don_temp['Kalem'] = df_don_temp['Kalem'].astype(str).str.strip()
                    df_don_raw = df_don_temp.groupby('Kalem').first()
                    df_don_raw.columns = make_unique_local(df_don_raw.columns)
                    
                    df_c = df_don_raw.copy()
                    for col in df_don_raw.columns:
                        try: 
                            clean_col = col.split('_')[0] if '_' in col else col
                            y, a = map(int, str(clean_col).split('/'))
                            if a != 3:
                                suffix_col = f"_{col.split('_')[1]}" if '_' in col else ""
                                prev = f"{y}/{a-3}{suffix_col}"
                                if prev in df_don_raw.columns: 
                                    df_c[col] = df_don_raw[col] - df_don_raw[prev]
                                else:
                                    df_c[col] = None
                        except: continue
                    
                    df_m = pd.concat([df_c.T, df_bil], axis=1, join='inner')
                    df_m = df_m.loc[:, ~df_m.columns.duplicated()]
                except Exception as e:
                    continue
                
                pool_firm = df_pool[df_pool['Firma Adı'] == firm].set_index('Dönem')
                common_idx = pool_firm.index.intersection(df_m.index)
                
                for donem in common_idx:
                    for col in pool_firm.columns:
                        if col in ['Firma Adı']: continue
                        
                        pool_val = pool_firm.loc[donem, col]
                        if isinstance(pool_val, pd.Series): pool_val = pool_val.iloc[0]
                        
                        if col in df_m.columns:
                            raw_val = df_m.loc[donem, col]
                            if isinstance(raw_val, pd.Series): raw_val = raw_val.iloc[0]
                        else:
                            raw_val = None
                            
                        pool_is_nan = pd.isna(pool_val)
                        raw_is_nan = pd.isna(raw_val)
                        
                        if pool_is_nan and raw_is_nan:
                            match = True
                        elif pool_is_nan != raw_is_nan:
                            match = False
                        else:
                            try:
                                match = math.isclose(float(pool_val), float(raw_val), rel_tol=1e-3, abs_tol=1e-2)
                            except:
                                match = str(pool_val).strip() == str(raw_val).strip()
                                
                        if match: total_matches += 1
                        total_cells_checked += 1
                        
                        all_results.append((firm, donem, col, pool_val, raw_val, match))
                        
            print() 

        if total_cells_checked == 0:
            print("\n[!] Denetlenecek eşleşen veri havuzu bulunamadı.")
            return

        success_rate = (total_matches / total_cells_checked) * 100
        print(f"\n[SONUÇ] Toplam Taranan Hücre: {total_cells_checked:,}")
        print(f"[SONUÇ] Başarılı Eşleşme: {total_matches:,} (%{success_rate:.2f})")
        
        title = f"Veri Bütünlüğü ve Denetim\n(Taranan Hücre: {total_cells_checked:,})"
        self._plot_pie_chart("8_Guvenilirlik_Orani.png", title, 
                             ['Başarılı', 'Uyumsuz'], 
                             [total_matches, total_cells_checked - total_matches])
        print(" -> Rapor Görseli Oluşturuldu: Gorseller/8_Guvenilirlik_Orani.png")
        
        print("\n" + "="*85)
        print(" RASTGELE 30 HÜCRE DOĞRULAMA (ÖRNEKLEM) ".center(85, '='))
        print("="*85)
        while True:
            if not all_results: break
            sample_size = min(30, len(all_results))
            samples = random.sample(all_results, sample_size)
            
            print(f"{'Firma':<8} | {'Dönem':<8} | {'Kalem':<33} | {'Havuz Değeri':<13} | {'Raw Değeri':<13} | {'Durum'}")
            print("-" * 85)
            for f, d, k, pv, rv, m in samples:
                pv_str = f"{pv:.2f}" if isinstance(pv, (int, float)) and not pd.isna(pv) else str(pv)
                rv_str = f"{rv:.2f}" if isinstance(rv, (int, float)) and not pd.isna(rv) else str(rv)
                m_str = "GEÇTİ" if m else "HATA"
                print(f"{f[:7]:<8} | {str(d)[:8]:<8} | {str(k)[:32]:<33} | {pv_str[:12]:<13} | {rv_str[:12]:<13} | {m_str}")
                
            ans = input("\n[?] Başka 30 rastgele örnek görmek ister misiniz? (e: Evet / q: Çıkış): ").lower()
            if ans != 'e':
                break

    def run_full_pipeline(self):
        self._print_header("TAM OTOMATİK VERİ SİSTEMİ")
        self.update_ticker_list()
        self.smart_batch_download()
        self.perform_audit(silent=True)
        self.run_sector_analysis(silent=True)
        self.run_strategic_grouping(silent=True)
        # self.run_data_merging(silent=True) # Optional: User might want to pick currency

    def run_data_merging(self):
        self._print_header("VERİ BİRLEŞTİRME VE HAVUZ OLUŞTURMA (STEP 7)")
        
        # 1. Selection
        options = {"1": ("EUR", "eur", "euro", "EUR"), "2": ("USD", "usd", "usd", "USD"), "3": ("TRY", "try", "tl", "TRY"), "4": ("TÜMÜ", "all", "all", "ALL")}
        print("Birleştirilecek para birimini seçin:")
        for k, v in options.items(): print(f" {k}. {v[0]}")
        sec = input("\nSeçiminiz: ")
        if sec not in options: return
        
        sel = [options["1"], options["2"], options["3"]] if sec == "4" else [options[sec]]

        for name, code, label, suffix in sel:
            output_path = os.path.join(PATH_MANIP_DATASET, f"Veri_Havuzu_{name}.xlsx")
            
            # Smart Check
            if os.path.exists(output_path):
                mtime = os.path.getmtime(output_path)
                dt_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
                print(f"\n[?] {name} havuzu zaten mevcut ({dt_str} tarihinde oluşturulmuş).")
                ans = input("Yeniden oluşturulsun mu? (e: Yeniden Yap / h: Atla): ").lower()
                if ans != 'e': 
                    print(f"[{name}] Atlandı.")
                    continue

            source_path = os.path.join(SCRIPT_DIR, "1_Kaynak_Veriler", f"fintables_excel_{label}")
            if not os.path.exists(source_path):
                print(f"[HATA] Kaynak klasör bulunamadı: {source_path}")
                continue

            files = [f for f in os.listdir(source_path) if f.endswith('.xlsx')]
            if not files:
                print(f"[HATA] {name} klasöründe Excel dosyası bulunamadı.")
                continue

            print(f"\n[İŞLEM] {len(files)} dosya birleştiriliyor ({name})...")
            st = time.time(); master = []

            def make_unique(cols):
                counts = {}; new_cols = []
                for c in cols:
                    clean = str(c).split('.')[0].strip()
                    counts[clean] = counts.get(clean, 0) + 1
                    new_cols.append(f"{clean}_{counts[clean]}" if counts[clean] > 1 else clean)
                return new_cols

            # 2. Processing Files
            for i, f in enumerate(files, 1):
                try:
                    self._print_progress_raw(len(files), i, f)
                    p = os.path.join(source_path, f); firm_code = re.sub(r'\s*\(.*?\)', '', f.replace('.xlsx', '')).strip().upper()
                    xls = pd.ExcelFile(p)
                    
                    df_bil_temp = pd.read_excel(p, sheet_name=xls.sheet_names[0])
                    df_bil_temp['Kalem'] = df_bil_temp['Kalem'].astype(str).str.strip()
                    df_bil_raw = df_bil_temp.groupby('Kalem').first()
                    df_bil_raw.columns = make_unique(df_bil_raw.columns)
                    df_bil = df_bil_raw.T
                    
                    sheet_don = [s for s in xls.sheet_names if 'Dönemsel' in s or 'Donemsel' in s][0]
                    df_don_temp = pd.read_excel(p, sheet_name=sheet_don)
                    df_don_temp['Kalem'] = df_don_temp['Kalem'].astype(str).str.strip()
                    df_don_raw = df_don_temp.groupby('Kalem').first()
                    df_don_raw.columns = make_unique(df_don_raw.columns)
                    
                    df_c = df_don_raw.copy()
                    for col in df_don_raw.columns:
                        try: 
                            clean_col = col.split('_')[0] if '_' in col else col
                            y, a = map(int, str(clean_col).split('/'))
                            if a != 3:
                                suffix_col = f"_{col.split('_')[1]}" if '_' in col else ""
                                prev = f"{y}/{a-3}{suffix_col}"
                                if prev in df_don_raw.columns: 
                                    df_c[col] = df_don_raw[col] - df_don_raw[prev]
                                else:
                                    # Eğer bir önceki çeyrek yoksa (örn. IPO yılı), kümülâtif değeri çeyreklik gibi kullanmak yanlıştır.
                                    df_c[col] = None
                        except: continue
                    
                    # Inner join kullanarak sadece hem Bilanço hem de Gelir Tablosu'nda var olan TAM dönemleri (örn. sadece 2016/3 olanları değil) alıyoruz.
                    df_m = pd.concat([df_c.T, df_bil], axis=1, join='inner')
                    df_m = df_m.loc[:, ~df_m.columns.duplicated()]
                    df_m.insert(0, 'Firma Adı', firm_code)
                    master.append(df_m.reset_index().rename(columns={'index': 'Dönem'}))
                except: continue

            if not master: continue
            df_final = pd.concat(master, ignore_index=True)
            df_final.columns = [str(c).strip() for c in df_final.columns]
            df_final = df_final.loc[:, ~df_final.columns.duplicated()]

            # 3. Sector Splitting
            if not os.path.exists(PATH_SECTOR_ANA_JSON):
                print("\n[UYARI] 6. Adım verisi bulunamadı. Tek sayfada toplanıyor.")
                df_final.to_excel(output_path, index=False)
            else:
                with open(PATH_SECTOR_ANA_JSON, "r", encoding="utf-8") as fs: ana_data = json.load(fs)
                with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                    found_any = False
                    for sec_name, firms in ana_data.items():
                        sub = df_final[df_final['Firma Adı'].isin([f.upper() for f in firms])].copy()
                        if not sub.empty:
                            v_cols = [c for c in sub.columns if not (sub[c].isnull().all() or (pd.to_numeric(sub[c], errors='coerce').fillna(1) == 0).all())]
                            sub_clean = sub[v_cols]
                            sh_name = sec_name[:31].replace(' ', '_')
                            sub_clean.to_excel(writer, sheet_name=sh_name, index=False)
                            
                            work_sheet = writer.sheets[sh_name]
                            for idx, col in enumerate(sub_clean.columns):
                                series = sub_clean[col]
                                max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                                work_sheet.set_column(idx, idx, min(max_len, 60))
                            
                            print(f"   -> {sec_name} sayfası oluşturuldu ({len(sub['Firma Adı'].unique())} Firma).")
                            found_any = True
                    
                    if not found_any: df_final.to_excel(writer, sheet_name="Genel_Veri", index=False)

            print(f"\n[BAŞARILI] {name} Havuzu hazırlandı: {output_path}")

    def _print_progress_raw(self, total, current, f_name):
        pct = (current / total) * 100
        bar = '█'*int(pct/2)+'-'*(50-int(pct/2))
        sys.stdout.write(f"\r|{bar}| %{pct:.1f} [{current}/{total}] - {f_name[:15]:<15}   "); sys.stdout.flush()

    def start(self):
        while True:
            self._print_header("FİRMA VERİ YÖNETİCİSİ")
            print(" 1. FİRMA LİSTESİNİ ÇEK\n 2. YÜKLEME YAP\n 3. DENETİM\n 4. SENKRONİZASYON\n 5. SEKTÖR (DETAY)\n 6. SEKTÖREL GRUPLAMA\n 7. VERİ BİRLEŞTİRME\n 8. KONTROL VE DOĞRULAMA\n A. TAM OTOMATİK\n Q. ÇIKIŞ")
            s = input("\nSeçiminiz: ").lower()
            if s == 'q': break
            elif s == '1': self.update_ticker_list()
            elif s == '2': self.smart_batch_download()
            elif s == '3': self.perform_audit()
            elif s == '4': self.update_ticker_list()
            elif s == '5': self.run_sector_analysis()
            elif s == '6': self.run_strategic_grouping()
            elif s == '7': self.run_data_merging()
            elif s == '8': self.run_integrity_check()
            elif s == 'a': self.run_full_pipeline()

if __name__ == "__main__":
    FirmDataCollector().start()
