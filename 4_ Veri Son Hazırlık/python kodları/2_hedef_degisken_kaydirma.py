import pandas as pd
import os
import matplotlib.pyplot as plt

# --- YOLLAR ---
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "1_Adim_Aykiri_Temizlik")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "2_Adim_Hedef_Kaydirma")
IMG_DIR = os.path.join(PHASE4_BASE, "görseller")
os.makedirs(OUT_DIR, exist_ok=True)

def run_target_shifting(input_file_name="1_Aykiri_Temiz_Veri_USD.xlsx"):
    currency = input_file_name.split("_")[4].replace(".xlsx", "")
    
    # Alt klasör yolları
    CUR_IMG_DIR = os.path.join(IMG_DIR, currency, "2_Hedef_Kaydirma")
    os.makedirs(CUR_IMG_DIR, exist_ok=True)
    
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, "2_Hedef_Kaydirilmis_Veri_" + currency + ".xlsx")

    print(f"\n[>>>] Hedef Değişken Kaydırma (t+1) Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    shift_stats = []

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - İşleniyor: {sector}")
            df = pd.read_excel(xl, sector)
            
            total_obs = len(df)
            total_firms = df['Firma Adı'].nunique()
            
            # --- İYİLEŞTİRME: FİRMA ADI NORMALİZASYONU ---
            # Kaydırma hatasını önlemek için isimleri geçici olarak normalize et
            df['Firma_Temp'] = df['Firma Adı'].astype(str).str.upper().str.strip()
            
            # Veriyi firma ve döneme göre sırala (Shift için kritik)
            df = df.sort_values(by=['Firma_Temp', 'Dönem'])
            
            # Hedef değişken (t+1) kaydırma
            target_col = 'Net Dönem Karı/Zararı'
            new_col = 'Net Dönem Karı (t+1)'
            
            # 1. Aşama: Standart Gruplu Kaydırma
            df[new_col] = df.groupby('Firma_Temp')[target_col].shift(-1)
            
            # 2. Aşama: AKILLI KURTARMA (Eğer hala boşsa ama bir sonraki dönem verisi varsa)
            # Bu kısım, shift'in kaçırdığı (indeks bozukluğu vb) durumları tamir eder
            null_targets = df[df[new_col].isna()].index
            if not null_targets.empty:
                print(f"    [!] {len(null_targets)} boş hedef tespit edildi, tamir deneniyor...")
                # Firma ve Dönem bazlı bir lookup sözlüğü oluştur
                lookup_dict = df.set_index(['Firma_Temp', 'Dönem'])[target_col].to_dict()
                
                # Dönemler genellikle ardışık tam sayılardır (Phase 1'de öyle yaptık)
                # Eğer dönem n+1 ise değeri getir
                for idx in null_targets:
                    f_name = df.at[idx, 'Firma_Temp']
                    p_val = df.at[idx, 'Dönem']
                    next_val = lookup_dict.get((f_name, p_val + 1))
                    if pd.notna(next_val):
                        df.at[idx, new_col] = next_val

            # Geçici kolonu sil
            df = df.drop(columns=['Firma_Temp'])
            
            # Kayıp analizi
            valid_target_obs = df[new_col].notna().sum()
            lost_obs = total_obs - valid_target_obs
            loss_rate = (lost_obs / total_obs) * 100
            
            shift_stats.append({
                "Sektör": sector,
                "Toplam Gözlem": total_obs,
                "Kayıp Gözlem (Son Dönem)": lost_obs,
                "Geçerli Hedef (t+1)": valid_target_obs,
                "Veri Kaybı (%)": f"{loss_rate:.2f}%"
            })

            # Yeni sütunu orijinal hedefin hemen yanına taşı
            cols = df.columns.tolist()
            target_idx = cols.index(target_col)
            new_cols = cols[:target_idx+1] + [new_col] + [c for c in cols[target_idx+1:] if c != new_col]
            df = df[new_cols]
            
            # Kaydet
            df.to_excel(writer, sheet_name=sector, index=False)

    # --- DURUM RAPORU GÖRSELLEŞTİRME ---
    df_stats = pd.DataFrame(shift_stats)
    
    # 1. Bar Chart: Hedef Değişken t+1 Eşleşme Oranları
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    df_bar = df_stats.copy()
    
    bars1 = ax1.bar(df_bar['Sektör'], df_bar['Geçerli Hedef (t+1)'], label='Geçerli Hedef (t+1)', color='#8E44AD', alpha=0.8)
    bars2 = ax1.bar(df_bar['Sektör'], df_bar['Kayıp Gözlem (Son Dönem)'], bottom=df_bar['Geçerli Hedef (t+1)'], label='Kayıp Gözlem (Son Dönem)', color='#D2B4DE', alpha=0.8)
    
    ax1.set_title(f"Sektörlere Göre Hedef Değişken (t+1) Eşleşme Oranları - {currency}", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Sektör", fontsize=11)
    ax1.set_ylabel("Gözlem Sayısı", fontsize=11)
    ax1.set_xticklabels(df_bar['Sektör'], rotation=15, ha='right')
    ax1.legend(loc='upper left')
    ax1.grid(True, axis='y', linestyle='--', alpha=0.5)
    
    for b1, b2 in zip(bars1, bars2):
        h1 = b1.get_height()
        h2 = b2.get_height()
        ax1.annotate(f"{int(h1)}", (b1.get_x() + b1.get_width() / 2., h1 / 2),
                     ha='center', va='center', color='white', fontweight='bold', fontsize=9)
        ax1.annotate(f"{int(h2)}", (b2.get_x() + b2.get_width() / 2., h1 + h2 / 2),
                     ha='center', va='center', color='black', fontweight='bold', fontsize=9)
        ax1.annotate(f"Toplam: {int(h1+h2)}", (b1.get_x() + b1.get_width() / 2., h1 + h2),
                     ha='center', va='bottom', color='black', fontweight='bold', fontsize=9, xytext=(0, 3), textcoords='offset points')
                     
    plt.tight_layout()
    img_path1 = os.path.join(CUR_IMG_DIR, "2_Hedef_Kaydirma_Uyum_Grafigi_" + currency + ".png")
    plt.savefig(img_path1, dpi=200, bbox_inches='tight')
    plt.close()

    # 2. Table: Hedef Değişken Kaydırma Durum Raporu
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.axis('off')
    plt.title(f"HEDEF DEĞİŞKEN KAYDIRMA DURUM RAPORU ({currency})", fontsize=14, fontweight='bold', pad=20)
    
    table = ax2.table(cellText=df_stats.values, colLabels=df_stats.columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 2.2)
    
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#8E44AD') # Mor
        else:
            if c == 0: cell.set_facecolor('#F4ECF7')
            else: cell.set_facecolor('white')

    # Alt Not
    note_text = "NOT: Veri kaybı, her firmanın elindeki en son dönemin bir sonraki (t+1) hedefi bulunmadığı için oluşmaktadır.\nBu durum, zaman serisi modellemesinde beklenen zamansal bir kısıttır."
    plt.figtext(0.5, 0.05, note_text, ha="center", fontsize=11, fontstyle='italic', color='#5D6D7E',
                bbox={"facecolor":"white", "alpha":0.8, "pad":5, "edgecolor":"#8E44AD", "linewidth":1})

    img_path2 = os.path.join(CUR_IMG_DIR, "2_Hedef_Kaydirma_Durum_Raporu_" + currency + ".png")
    plt.savefig(img_path2, dpi=200, bbox_inches='tight')
    plt.close()

    print(f"[+] Hedef kaydırılmış veri kaydedildi: {os.path.basename(output_path)}")
    print(f"[+] Durum raporu görselleri oluşturuldu: {os.path.basename(img_path1)} ve {os.path.basename(img_path2)}")

if __name__ == "__main__":
    # Giriş klasöründeki tüm kurları otomatik tara
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("1_Aykiri_Temiz_Veri_") and f.endswith(".xlsx")]
        if not files:
            print("Uyarı: İşlenecek veri dosyası bulunamadı!")
        else:
            for f_name in files:
                try:
                    run_target_shifting(f_name)
                except Exception as e:
                    print(f"Hata ({f_name}): {e}")
    else:
        print(f"Hata: Giriş klasörü bulunamadı: {INPUT_DIR}")
