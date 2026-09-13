import pandas as pd
import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns

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
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")
INPUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "4_Adim_Anomali_Entegrasyonu")
OUT_DIR = os.path.join(PHASE4_BASE, "çıktılar", "5_Adim_Mevsimsellik_Entegrasyonu")
os.makedirs(OUT_DIR, exist_ok=True)

def run_seasonality_integration(input_file_name):
    currency = input_file_name.split("_")[-1].replace(".xlsx", "")
    input_path = os.path.join(INPUT_DIR, input_file_name)
    output_path = os.path.join(OUT_DIR, f"5_Final_Mevsimsellik_Entegre_Veri_{currency}.xlsx")

    print(f"\n[>>>] Mevsimsellik Entegrasyonu Başlatılıyor: {input_file_name}")
    
    xl = pd.ExcelFile(input_path)
    
    # Görselleştirme Klasörünü Hazırla
    img_dir = os.path.join(PHASE4_BASE, "görseller", currency, "5_Mevsimsellik")
    os.makedirs(img_dir, exist_ok=True)

    all_season_counts = []

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sector in xl.sheet_names:
            print(f"  - Mevsimsellik Hesaplanıyor: {sector}")
            df = pd.read_excel(xl, sector)
            
            # Mevsimsellik Formülü: (Dönem - 1) % 4 + 1
            df['Mevsimsellik'] = ((df['Dönem'] - 1) % 4) + 1
            
            # Sütun Sıralama (Anomali_Durumu'nun sağına)
            cols = list(df.columns)
            if 'Mevsimsellik' in cols:
                cols.remove('Mevsimsellik')
                if 'Anomali_Durumu' in cols:
                    idx = cols.index('Anomali_Durumu') + 1
                else:
                    idx = 2
                cols.insert(idx, 'Mevsimsellik')
            
            df_final = df[cols]
            df_final.to_excel(writer, sheet_name=sector, index=False)
            
            # Dağılım İstatistikleri Topla
            counts = df_final['Mevsimsellik'].value_counts().reset_index()
            counts.columns = ['Çeyrek', 'Gözlem Sayısı']
            counts['Sektör'] = sector
            all_season_counts.append(counts)

    # Görsel Rapor Oluştur (Mevsimsel Dağılım Çizelgesi + Tablo)
    try:
        combined_counts = pd.concat(all_season_counts)
        combined_counts['Çeyrek Adı'] = combined_counts['Çeyrek'].map({1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'})
        
        # 1. Bar plot
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        sns.barplot(data=combined_counts, x='Sektör', y='Gözlem Sayısı', hue='Çeyrek Adı', palette='Set2', ax=ax1)
        
        # Barların üzerine tam sayısal değerleri ekle
        for p in ax1.patches:
            height = p.get_height()
            if pd.notna(height) and height > 0:
                ax1.annotate(f"{int(height)}", 
                            (p.get_x() + p.get_width() / 2., height),
                            ha='center', va='center', 
                            xytext=(0, 6), 
                            textcoords='offset points', 
                            fontsize=8, fontweight='bold', color='black')
        
        ax1.set_title(f"Sektörlere Göre Mevsimsel Veri Dağılımı ({currency})", fontsize=14, fontweight='bold')
        ax1.set_xlabel("Sektör", fontsize=11)
        ax1.set_ylabel("Gözlem (Satır) Sayısı", fontsize=11)
        ax1.set_xticklabels(combined_counts['Sektör'].unique(), rotation=15, ha='right')
        ax1.legend(title='Çeyrek Dönemler')
        ax1.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        img_path1 = os.path.join(img_dir, f"5_Mevsimsel_Dagilim_{currency}.png")
        plt.savefig(img_path1, dpi=200)
        plt.close()
        
        # 2. Pivot Table
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        ax2.axis('off')
        plt.title("SEKTÖRLERE GÖRE ÇEYREKLİK GÖZLEM DAĞILIM TABLOSU", fontsize=14, fontweight='bold', pad=15)
        
        df_pivot = combined_counts.pivot(index='Sektör', columns='Çeyrek Adı', values='Gözlem Sayısı').reset_index()
        df_pivot['Toplam'] = df_pivot[['Q1', 'Q2', 'Q3', 'Q4']].sum(axis=1)
        for col in ['Q1', 'Q2', 'Q3', 'Q4', 'Toplam']:
            df_pivot[col] = df_pivot[col].astype(int)
            
        table = ax2.table(cellText=df_pivot.values, colLabels=df_pivot.columns, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.0, 2.2)
        
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor('#2E86C1')
            else:
                if c == 0: cell.set_facecolor('#EBF5FB')
                elif c == 5: cell.set_facecolor('#EAFAF1') # Green for totals
                else: cell.set_facecolor('white')
                
        plt.tight_layout()
        img_path2 = os.path.join(img_dir, f"5_Mevsimsel_Tablo_{currency}.png")
        plt.savefig(img_path2, dpi=200)
        plt.close()
        
        print(f"[+] Mevsimsellik görselleri kaydedildi: {img_path1} ve {img_path2}")
    except Exception as e:
        print(f"Mevsimsellik görseli oluşturma hatası: {e}")

    print(f"[+] Mevsimsellik entegre edilmiş veri kaydedildi: {os.path.basename(output_path)}")

if __name__ == "__main__":
    if os.path.exists(INPUT_DIR):
        files = [f for f in os.listdir(INPUT_DIR) if f.startswith("4_Final_Anomali_Entegre_Veri_") and f.endswith(".xlsx")]
        for f_name in files:
            run_seasonality_integration(f_name)
    else:
        print(f"Hata: Giriş klasörü bulunamadı: {INPUT_DIR}")
