import pandas as pd
import numpy as np
import os
import json
import sys

# --- YOLLAR ---
BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection\1_Veri Manipulasyonu"
OUT_DIR = os.path.join(BASE_PATH, "raporlar", "11_Veri_Tamamlama_Logu")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return text.upper().strip().replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C').replace('Ş', 'S').replace('Ğ', 'G')

def is_id_col(col_name):
    n = normalize_text(col_name)
    ident_keywords = ['DONEM', 'FIRMA', 'SEKTOR', 'YEAR', 'MONTH', 'YIL', 'AY']
    return any(k in n for k in ident_keywords) and len(n) < 15

def generate_imputation_log(currency="USD"):
    print("\n" + "="*70)
    print(f"   ADIM 11: VERİ TAMAMLAMA İZLENEBİLİRLİK LOGU ({currency})")
    print("="*70)
    
    # --- ÇIKTI YOLLARI ---
    OUT_XLSX = os.path.join(OUT_DIR, f"Doldurulan_Veriler_Log_{currency}.xlsx")

    before_name = f"9_Gelir_Gider_Birlesik_Havuz_{currency}.xlsx" if currency else "9_Gelir_Gider_Birlesik_Havuz.xlsx"
    after_name = f"10_Medyan_Doldurulmus_Final_Veri_{currency}.xlsx" if currency else "10_Medyan_Doldurulmus_Final_Veri.xlsx"
    
    before_path = os.path.join(BASE_PATH, "raporlar", "9_Gelir_Gider_Konsolidasyonu", before_name)
    after_path = os.path.join(BASE_PATH, "raporlar", "10_Veri_Tamamlama", after_name)
    
    # Fallback to generic if needed
    if not os.path.exists(before_path): before_path = os.path.join(BASE_PATH, "raporlar", "9_Gelir_Gider_Konsolidasyonu", "9_Gelir_Gider_Birlesik_Havuz.xlsx")
    if not os.path.exists(after_path): after_path = os.path.join(BASE_PATH, "raporlar", "10_Veri_Tamamlama", "10_Medyan_Doldurulmus_Final_Veri.xlsx")

    if not os.path.exists(before_path) or not os.path.exists(after_path):
        print(f"Hata: Girdi dosyaları bulunamadı! ({before_path} veya {after_path})")
        return

    xl_before = pd.ExcelFile(before_path)
    xl_after = pd.ExcelFile(after_path)
    
    total_logs = []
    
    for sector in xl_after.sheet_names:
        print(f"Sektör İşleniyor: {sector}")
        
        if sector not in xl_before.sheet_names:
            continue
            
        df_before = pd.read_excel(xl_before, sheet_name=sector)
        df_after = pd.read_excel(xl_after, sheet_name=sector)
        
        firm_col = [c for c in df_after.columns if 'Firma' in str(c)][0]
        period_col = [c for c in df_after.columns if 'Dnem' in str(c) or 'Dönem' in str(c)][0]
        
        num_cols = [c for c in df_after.columns if not is_id_col(c) and pd.api.types.is_numeric_dtype(df_after[c])]
        
        for col in num_cols:
            if col not in df_before.columns:
                continue
                
            mask = df_before[col].isna() & df_after[col].notna()
            
            if mask.any():
                filled_rows = df_after[mask]
                for _, row in filled_rows.iterrows():
                    total_logs.append({
                        "Sektör": sector,
                        "Firma Adı": str(row[firm_col]),
                        "Dönem": str(row[period_col]),
                        "Öznitelik": col,
                        "Eski Değer": "BOŞ (NaN)",
                        "Yeni Değer": float(row[col])
                        # KUR sütunu kaldırıldı
                    })

    # 1. EXCEL Kaydet (Sektör Bazlı Sayfalar/Sheets)
    if total_logs:
        df_all = pd.DataFrame(total_logs)
        
        try:
            with pd.ExcelWriter(OUT_XLSX, engine='xlsxwriter') as writer:
                # Sektörlere göre grupla ve her birini ayrı sayfaya yaz
                for sector_name, group in df_all.groupby("Sektör"):
                    sheet_name = str(sector_name)[:30]
                    # Log tablosundan Sektör sütununu çıkarıyoruz (zaten sayfa isminde var)
                    display_group = group.drop(columns=["Sektör"])
                    display_group.to_excel(writer, index=False, sheet_name=sheet_name)
                    
                    # Görsel düzenleme
                    worksheet = writer.sheets[sheet_name]
                    for i, col in enumerate(display_group.columns):
                        column_len = max(display_group[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(i, i, min(column_len, 50))
            
            print(f"[+] Sektör Bazlı Denetim Raporu Oluşturuldu: {OUT_XLSX}")
        except Exception as e:
            print(f"[!] Excel oluşturma hatası: {e}")
            df_all.to_excel(OUT_XLSX, index=False)
        
    # --- GÖRSELLEŞTİRME ---
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        IMG_DIR = os.path.join(BASE_PATH, "görseller", "11_Log_Analizi")
        os.makedirs(IMG_DIR, exist_ok=True)
        
        if total_logs:
            plt.figure(figsize=(12, 6))
            sns.set_style("whitegrid")
            counts = df_all["Sektör"].value_counts()
            sns.barplot(x=counts.index, y=counts.values, palette="viridis")
            plt.title(f"Sektör Bazlı Doldurulan Hücre Sayıları ({currency})", fontsize=14, fontweight='bold')
            plt.ylabel("Hücre Sayısı")
            plt.xticks(rotation=45, ha='right'); plt.tight_layout()
            plt.savefig(os.path.join(IMG_DIR, f"11_{currency}_Sektorel_Log.png"), dpi=300); plt.close()
            print(f"[+] Analitik görseller güncellendi: {IMG_DIR}")
    except:
        pass

    print("\n" + "="*80)
    print("LOGLAMA TAMAMLANDI (SADECE EXCEL)")
    print(f"Kur: {currency}")
    print(f"Toplam Doldurulan Hücre Sayısı: {len(total_logs)}")
    print(f"Rapor Dosyası: {OUT_XLSX}")
    print("="*80)

if __name__ == "__main__":
    # Komut satırı argümanı kontrolü (Step 13'ten geliyorsa)
    cur_arg = sys.argv[1] if len(sys.argv) > 1 else "USD"
    generate_imputation_log(cur_arg)
