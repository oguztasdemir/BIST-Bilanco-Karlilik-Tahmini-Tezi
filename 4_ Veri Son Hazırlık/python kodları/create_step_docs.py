import os

BASE_PATH = r"c:\Users\User\Desktop\Tez Feature Selection"
PHASE4_BASE = os.path.join(BASE_PATH, "4_ Veri Son Hazırlık")
OUTPUT_BASE = os.path.join(PHASE4_BASE, "çıktılar")

docs = {
    "1_Adim_Aykiri_Temizlik": {
        "title": "Adım 1: Aykırı Değer Winsorization (Winsorizasyon Temizliği)",
        "what_we_did": (
            "Finansal oranlar ve özniteliklerin en alt %1 ve en üst %99'luk dilimlerindeki aykırı (uç) değerleri, "
            "bu sınır değerlerine çekilerek (clipping/winsorize) stabilize edildi. Veri setinden satır silme işlemi "
            "yapılmaksızın uç değerlerin modelin öğrenme kalitesini bozması engellendi."
        ),
        "what_graphs_explain": (
            "- 1_Aykiri_Temizlik/1_Aykiri_Sektorel_Oranlari.png: Sektör bazında her bir finansal oran özelliğinin kaç adet aykırı değer içerdiğini "
            "ve yüzde kaçlık bir anomali oranına tekabül ettiğini gösteren bar grafiğidir.\n"
            "- 1_Aykiri_Temizlik/1_Aykiri_Sektorel_Ozet_Raporu.png: Her sektör için toplam kontrol edilen hücre sayısını, "
            "etkilenen/düzeltilen aykırı hücre miktarını ve ortalama anomali oranını özet tablo olarak gösterir.\n"
            "- 1_Aykiri_Temizlik/1_Aykiri_Raporlari/*.png: Her bir sektör için finansal oran bazlı anomali oranlarını gösteren detaylı bar grafikleridir."
        ),
        "outputs": "1_Aykiri_Temiz_Veri_*.xlsx ve 1_Aykiri_Deger_Raporu_*.xlsx"
    },
    "2_Adim_Hedef_Kaydirma": {
        "title": "Adım 2: Hedef Değişken Kaydırma (Shift t+1)",
        "what_we_did": (
            "Makine öğrenmesi regresyon modellerinin sonraki dönem kârını tahmin edebilmesi amacıyla, her firmanın t "
            "dönemindeki satırına, bir sonraki çeyrek dönemdeki (t+1) Net Dönem Kârı/Zararı değeri hedef değişken olarak eklendi. "
            "Dönemler arasındaki takvimsel süreklilik ve firma bazında kaydırma tutarlılığı korundu."
        ),
        "what_graphs_explain": (
            "- 2_Hedef_Kaydirma/2_Hedef_Kaydirma_Uyum_Grafigi_*.png: Sektörlere göre başarılı hedef eşleşmesi sağlayan geçerli gözlemler ile "
            "gelecek çeyrek verisi olmadığı için elenen son çeyrek satırlarını karşılaştırmalı bar grafiği olarak gösterir.\n"
            "- 2_Hedef_Kaydirma/2_Hedef_Kaydirma_Durum_Raporu_*.png: Kaydırma işlemi sonrasındaki geçerli ve kayıp gözlem adetlerini "
            "sektörel bazda detaylandıran özet istatistik tablosudur."
        ),
        "outputs": "2_Hedef_Kaydirilmis_Veri_*.xlsx"
    },
    "3_Adim_Zeki_Eleme": {
        "title": "Adım 3: Zeki Firma Eleme Karar Destek Matrisi",
        "what_we_did": (
            "Yetersiz veri geçmişine sahip (toplamda 4 çeyrek dönemden az gözlemi bulunan) veya hedef değişkeni (t+1 net kârı) "
            "boş olan firmalar veri setinden elendi. Bu işlem, modelin öğrenemeyeceği gürültülü verileri temizleyerek tutarlılığı artırdı."
        ),
        "what_graphs_explain": (
            "- 3_Zeki_Eleme/3_Zeki_Eleme_Kalan_Giden_*.png: Sektör bazında filtreyi geçen kalan firmalar ile elenen giden firmaların sayılarını "
            "gösteren karşılaştırmalı sütun grafiğidir.\n"
            "- 3_Zeki_Eleme/3_Zeki_Firma_Eleme_Matrisi_*.png: Hangi dönem eşik değerinin seçildiğini ve bu seçime göre silinen firma ile "
            "satır sayılarını gösteren karar destek matrisi tablosudur."
        ),
        "outputs": "3_Final_Filtreli_Veri_*.xlsx"
    },
    "4_Adim_Anomali_Entegrasyonu": {
        "title": "Adım 4: Tarihsel Anomali Entegrasyonu",
        "what_we_did": (
            "Türkiye ekonomisindeki makro şokları ve kriz dönemlerini (Covid-19 pandemisi, kur şokları, darbe girişimi ve "
            "Kahramanmaraş depremleri gibi) temsil eden ikili anomali bayrakları (Anomali_Durumu) veri setine çeyreklik dönem bazında entegre edildi."
        ),
        "what_graphs_explain": (
            "- 4_Anomali/4_Anomali_Zaman_Cizelgesi_*.png: 2016 Q1 ile 2025 Q4 arasındaki 40 çeyreklik süreçte hangi çeyreklerin "
            "anomali kabul edildiğini ve bunun arkasındaki ekonomik/tarihsel nedenleri takvimsel bir zaman çizelgesiyle gösterir.\n"
            "- 4_Anomali/4_Anomali_Sektorel_Dagilim_Tablosu_*.png: Sektörler bazında toplam gözlemlerin, normal dönem gözlemlerinin, "
            "anomali dönem gözlemlerinin sayılarını ve anomali oranlarını gösteren özet tablodur."
        ),
        "outputs": "4_Final_Anomali_Entegre_Veri_*.xlsx"
    },
    "5_Adim_Mevsimsellik_Entegrasyonu": {
        "title": "Adım 5: Mevsimsellik Entegrasyonu",
        "what_we_did": (
            "Şirketlerin bilançolarındaki çeyreklik mevsimsel döngüleri (Q1, Q2, Q3, Q4) yakalamak amacıyla 1'den 4'e kadar "
            "mevsimsellik kodları (Mevsimsellik) veri setine eklendi. This sayede yıl sonu bilanço kapanış kârları ile diğer çeyrekler ayırt edilebilir hale geldi."
        ),
        "what_graphs_explain": (
            "- 5_Mevsimsellik/5_Mevsimsel_Dagilim_*.png: Sektör bazında her bir çeyrek döneme (Q1-Q4) düşen gözlem sayılarını karşılaştırarak, "
            "veri setinin mevsimler arasında dengeli ve homojen bir dağılıma sahip olup olmadığını doğrular.\n"
            "- 5_Mevsimsellik/5_Mevsimsel_Tablo_*.png: Sektör ve çeyrek bazında gözlem sayılarını detaylı olarak veren pivot dağılım tablosudur."
        ),
        "outputs": "5_Final_Mevsimsellik_Entegre_Veri_*.xlsx"
    },
    "6_Adim_Kumulatif_Sektor_Kiyaslamasi": {
        "title": "Adım 6: Kümülatif Kâr ve Sektör Kıyaslaması (Büyüklük Ölçümü)",
        "what_we_did": (
            "Firmaların tarihsel büyüklüklerini yansıtmak amacıyla expanding cumsum yöntemiyle kümülatif net kârları hesaplandı. "
            "Ayrıca veri sızıntısını (data leakage) engellemek adına Leave-One-Out yöntemi kullanılarak, firmanın kümülatif kârı "
            "sektördeki diğer akranlarının ortalaması ile kıyaslanarak Sektorel_Kumulatif_Gorece_Kar türetildi."
        ),
        "what_graphs_explain": (
            "- 6_Kumulatif_Kar/6_Kumulatif_Sektor_Kar_Trendi_*.png: Sektörlerin 40 çeyreklik süre boyunca kümülatif olarak ortalama kâr biriktirme "
            "ve büyüme hızlarını gösteren, sektörler arası performans gelişimini karşılaştıran çizgi grafiğidir.\n"
            "- 6_Kumulatif_Kar/6_Kumulatif_Kar_Buyume_Tablosu_*.png: Sektörler bazında başlangıç-bitiş dönemleri ile ilk ve son dönem kümülatif kâr "
            "ortalamalarını ve kümülatif büyüme oranlarını gösteren özet tablodur."
        ),
        "outputs": "6_Final_Kumulatif_Sektor_Kiyaslamasi_*.xlsx"
    },
    "7_Adim_Cari_Donem_Sektor_Kiyaslamasi": {
        "title": "Adım 7: Cari Dönem Sektörel Görece Durum (Normalizasyon)",
        "what_we_did": (
            "Cari dönemdeki kâr performansını sektörel bazda standartlaştırmak için medyan ve çeyrekler arası açıklık (IQR) "
            "kullanılarak Sektorel_Cari_Z_Skoru özniteliği üretildi. Ayrıca Leave-One-Out yöntemiyle cari döneme ait sektörel "
            "görece kâr oranları hesaplandı. Böylece sektörler arasındaki ölçek farkları arındırıldı."
        ),
        "what_graphs_explain": (
            "- 7_Cari_Sektor/7_Sektorel_Z_Skor_Dagilimi_*.png: Sektör bazında normalize edilmiş cari kâr dağılımlarını kutu grafiği (Boxplot) "
            "olarak gösterir. Sektörler arasındaki Z-skorunun sıfır etrafındaki dengesini ve aykırı durumların yayılımını raporlar.\n"
            "- 7_Cari_Sektor/7_Sektorel_Z_Skor_İstatistik_Tablosu_*.png: Her sektör için Z-skoru minimum, maksimum, medyan ve çeyreklik kartil "
            "değerlerini gösteren detaylı betimsel istatistik tablosudur."
        ),
        "outputs": "7_Final_Cari_Donem_Sektor_Kiyaslamasi_*.xlsx"
    },
    "8_Adim_Mevsimsel_Gecmis_Sektor_Kiyaslamasi": {
        "title": "Adım 8: Mevsimsel Geçmiş ve Sektörel Mevsimsel Kıyas (Momentum)",
        "what_we_did": (
            "Firmaların geçen yılın aynı çeyreğine göre kâr değişimlerini ölçen Mevsimsel_YoY_Kar_Büyümesi özniteliği üretildi. "
            "Ayrıca firmanın geçmiş çeyreklerdeki mevsimsel ortalama performansı ile sektörün mevsimsel geçmişi kıyaslanarak "
            "Sektorel_Mevsimsel_Gorece_Kar (mevsimsel momentum) özniteliği türetildi."
        ),
        "what_graphs_explain": (
            "- 8_Mevsimsel_Gecmis/8_Sektorel_Mevsimsel_YoY_Büyüme_*.png: Sektörlerin tarihsel olarak geçen yılın aynı dönemine göre ortalama yüzde kaç "
            "kâr büyümesi veya küçülmesi gerçekleştirdiğini gösterir (Pozitif kâr büyümeleri yeşil, negatifler kırmızı barlar ile gösterilir).\n"
            "- 8_Mevsimsel_Gecmis/8_Sektorel_Mevsimsel_YoY_Tablosu_*.png: Sektörlerin yıllık bazda ortalama, standart sapma, minimum ve maksimum "
            "YoY kâr büyüme oranlarını gösteren istatistik tablosudur."
        ),
        "outputs": "8_Final_Mevsimsel_Gecmis_Sektor_Kiyaslamasi_*.xlsx"
    },
    "9_Adim_Sektorel_Akran_Kiyaslama": {
        "title": "Adım 9: Sektörel Akran Kıyaslama (Hedef Sınıflandırma Değişkeni)",
        "what_we_did": (
            "İlgili çeyrek dönemde şirketin net kârının sektör medyanından büyük olup olmadığı kıyaslanarak ikili (binary) sınıflandırma "
            "hedef değişkeni (Sektör Üstü Performans Gerçek) türetildi. Bu adım sonucunda veri kümesinin genel özet istatistiklerini "
            "içeren bir kapak sayfası ve bağımsız özet raporları oluşturuldu."
        ),
        "what_graphs_explain": (
            "- 9_Akran_Kiyas/9_Akran_Performans_Dagilimi_*.png: Sektör bazında hedef değişken sınıflarının dağılımını gösterir. Grafik, barların "
            "neredeyse tamamen eşit yükseklikte çıkmasıyla (%50-%50) makine öğrenmesi için mükemmel bir sınıf dengesi kurulduğunu kanıtlar.\n"
            "- 9_Akran_Kiyas/9_Akran_Performans_Ozet_Tablosu_*.png: Benzersiz firma sayısı, toplam gözlem sayısı, başlangıç ve bitiş dönemleri ile "
            "akran üstü performans oranını sektörlere göre listeleyen genel veri kümesi özet tablosudur."
        ),
        "outputs": "9_Final_Sektorel_Akran_Kiyaslama_*.xlsx ve bağımsız Veri_Kumesi_Genel_Ozeti_*.xlsx"
    }
}

for folder, info in docs.items():
    folder_path = os.path.join(OUTPUT_BASE, folder)
    os.makedirs(folder_path, exist_ok=True)
    
    # Eski dosyayı sil
    old_txt_path = os.path.join(folder_path, "adim_aciklamasi.txt")
    if os.path.exists(old_txt_path):
        try:
            os.remove(old_txt_path)
            print(f"[-] Eski dosya silindi: {old_txt_path}")
        except Exception as e:
            print(f"Hata: {e}")

    # Yeni ismiyle yaz
    new_txt_path = os.path.join(folder_path, "00_adim_aciklamasi.txt")
    
    content = f"""================================================================================
{info['title']}
================================================================================

1. BU ADIMDA NE YAPILDI?
--------------------------------------------------------------------------------
{info['what_we_did']}

2. GRAFİKLER NE ANLATIYOR?
--------------------------------------------------------------------------------
{info['what_graphs_explain']}

3. ÜRETİLEN EXCEL DOSYALARI
--------------------------------------------------------------------------------
{info['outputs']}
"""
    
    with open(new_txt_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"[+] Açıklama dosyası oluşturuldu: {new_txt_path}")

# ============================================================
# MASTER FAZ 4 ÖZETİ
# ============================================================
master_path = os.path.join(OUTPUT_BASE, "00_FAZ4_MASTER_OZETI.txt")

turetilen_oznitelikler = [
    ("Anomali_Durumu",                    "Adım 4", "Makroekonomik şok dönemlerini işaretleyen ikili bayrak (0=normal, 1=anomali)"),
    ("Mevsimsellik",                      "Adım 5", "Çeyreklik dönem kodu: Q1=1, Q2=2, Q3=3, Q4=4"),
    ("Firma_Kum_Kar",                     "Adım 6", "Firmanın o ana kadar biriktirdiği kümülatif net kârı (expanding sum)"),
    ("Sektor_Kum_Kar_Ortalama",           "Adım 6", "Leave-One-Out sektör kümülatif kâr ortalaması (veri sızıntısı önlendi)"),
    ("Sektorel_Kumulatif_Gorece_Kar",     "Adım 6", "Firma kümülatif kârının sektör ortalamasına oranı (büyüklük göstergesi)"),
    ("Sektorel_Cari_Z_Skoru",             "Adım 7", "Cari dönem kârının sektör içinde normalleştirilmiş Z-skoru (IQR bazlı)"),
    ("Sektorel_Cari_Gorece_Kar",          "Adım 7", "Firma cari kârının LOO sektör medyanına oranı"),
    ("Mevsimsel_YoY_Kar_Büyümesi",        "Adım 8", "Geçen yılın aynı çeyreğine göre kâr büyüme oranı (Year-over-Year)"),
    ("Mevsimsel_Sektor_YoY_Ortalamasi",   "Adım 8", "LOO sektörel mevsimsel YoY ortalaması"),
    ("Sektorel_Mevsimsel_Gorece_Kar",     "Adım 8", "Firmanın mevsimsel YoY büyümesinin sektör ortalamasına oranı"),
    ("Sektör Üstü Performans Gerçek",     "Adım 9", "İkili hedef değişken: Firma kârı > sektör medyanı ise 1, değilse 0"),
    ("Net Dönem Karı (t+1)",              "Adım 2", "Regresyon hedef değişkeni: Bir sonraki çeyreğin net kârı"),
]

adim_ozeti = [
    ("Adım 1",  "Aykırı Değer Winsorization",              "%1-%99 kırpma ile uç değerler stabilize edildi. Satır silinmedi.",                                  "1_Aykiri_Temiz_Veri_*.xlsx"),
    ("Adım 2",  "Hedef Değişken Kaydırma (t+1)",           "Her firma satırına bir sonraki çeyreğin net kârı eklendi.",                                          "2_Hedef_Kaydirilmis_Veri_*.xlsx"),
    ("Adım 3",  "Zeki Firma Eleme",                        "Yetersiz gözlem geçmişi olan firmalar optimal eşik ile elendi.",                                     "3_Final_Filtreli_Veri_*.xlsx"),
    ("Adım 4",  "Tarihsel Anomali Entegrasyonu",           "Ekonomik şok dönemleri (Covid, kur krizi vb.) veri setine eklendi.",                                "4_Final_Anomali_Entegre_Veri_*.xlsx"),
    ("Adım 5",  "Mevsimsellik Entegrasyonu",               "Çeyreklik mevsim kodu (Q1-Q4) eklendi.",                                                            "5_Final_Mevsimsellik_Entegre_Veri_*.xlsx"),
    ("Adım 6",  "Kümülatif Kâr & Sektör Kıyaslaması",     "Expanding cumsum + LOO sektör kıyaslaması ile büyüklük öznitelikleri türetildi.",                   "6_Final_Kumulatif_Sektor_Kiyaslamasi_*.xlsx"),
    ("Adım 7",  "Cari Dönem Sektörel Görece Durum",        "IQR tabanlı Z-skor + LOO cari dönem sektör oranı türetildi.",                                       "7_Final_Cari_Donem_Sektor_Kiyaslamasi_*.xlsx"),
    ("Adım 8",  "Mevsimsel Geçmiş & Sektörel Kıyas",       "YoY büyüme oranı + LOO mevsimsel sektör kıyaslaması türetildi.",                                    "8_Final_Mevsimsel_Gecmis_Sektor_Kiyaslamasi_*.xlsx"),
    ("Adım 9",  "Sektörel Akran Kıyaslama (Hedef)",        "İkili sınıflandırma hedefi: Sektör medyanı üstü performans bayrağı türetildi.",                     "9_Final_Sektorel_Akran_Kiyaslama_*.xlsx"),
]

master_content = """\
================================================================================
  FAZ 4: VERİ SON HAZIRLIK — MASTER ÖZETİ
  (9 Adımlık Otonom Özellik Mühendisliği Zinciri)
================================================================================

HEDEF:
  Ham finansal panel verisini makine öğrenmesine hazır hale getirmek.
  Regresyon (t+1 net kâr tahmini) ve sınıflandırma (sektör üstü performans)
  için kullanılabilir öznitelik seti oluşturmak.

KAPSAM:
  Para birimleri : USD, EUR, TRY (her biri bağımsız işlendi)
  Sektörler      : 7 sektör (SANAYİ, FİNANS, İNŞAAT, TEKNOLOJİ, ENERJİ,
                              GIDA, TİCARET)
  Dönem aralığı  : 2016 Q1 – 2025 Q4 (40 çeyrek)

================================================================================
  9 ADIM — KISA ÖZET
================================================================================

"""

for adim, baslik, aciklama, cikti in adim_ozeti:
    master_content += f"  {adim}: {baslik}\n"
    master_content += f"    → {aciklama}\n"
    master_content += f"    → Çıktı: {cikti}\n\n"

master_content += """\
================================================================================
  TÜRETİLEN ÖZNİTELİKLER (12 Yeni Sütun)
================================================================================

"""

col_w = [42, 8, 62]
header = f"  {'Öznitelik Adı':<{col_w[0]}} {'Adım':<{col_w[1]}} {'Açıklama':<{col_w[2]}}\n"
master_content += header
master_content += "  " + "-" * (sum(col_w) + 4) + "\n"
for oznitelik, adim, aciklama in turetilen_oznitelikler:
    master_content += f"  {oznitelik:<{col_w[0]}} {adim:<{col_w[1]}} {aciklama}\n"

master_content += """\

================================================================================
  GÖRSEL KLASÖR YAPISI
================================================================================

  görseller/
  └── {USD | EUR | TRY}/
      ├── 1_Aykiri_Temizlik/      (2 PNG + alt klasör)
      ├── 2_Hedef_Kaydirma/       (2 PNG)
      ├── 3_Zeki_Eleme/           (2 PNG)
      ├── 4_Anomali/              (2 PNG)
      ├── 5_Mevsimsellik/         (2 PNG)
      ├── 6_Kumulatif_Kar/        (2 PNG)
      ├── 7_Cari_Sektor/          (2 PNG)
      ├── 8_Mevsimsel_Gecmis/     (2 PNG)
      └── 9_Akran_Kiyas/          (2 PNG)

  Her adım için: 1 grafik görseli + 1 sektörel tablo görseli = 2 PNG

================================================================================
  NOT
================================================================================

  Tüm sektörel kıyaslamalar Leave-One-Out (LOO) yöntemiyle yapılmıştır.
  Bu yöntemde firmanın kendi değeri, sektör ortalaması/medyanı hesaplanırken
  dışarıda bırakılır. Böylece veri sızıntısı (data leakage) önlenir.

  Winsorization, firma eleme ve hedef kaydırma adımları modelin öğrenme
  kalitesini artırmak için uygulanmış ön işleme adımlarıdır. Hiçbir adımda
  keyfi veri silme yapılmamıştır.
"""

with open(master_path, "w", encoding="utf-8") as f:
    f.write(master_content)

print(f"\n[+] Master özet dosyası oluşturuldu: {master_path}")
