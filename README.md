# 📺 TV Program Planlayıcı Uygulaması

Bu uygulama, kullanıcıların tercihlerine göre haftalık TV programlarını optimize ederek kişiselleştirilmiş bir izleme planı oluşturur.

## 🌟 Özellikler

- Kullanıcı dostu arayüz ile program tercihlerini belirleme
- Kişiye özel uygunluk takvimi oluşturma
- 3 farklı algoritma ile program optimizasyonu:
  - Açgözlü Algoritma (Greedy)
  - Kısıt Programlama
  - Genetik Algoritma
- Görselleştirme desteği ile program takvimi
- Excel çıktıları ve raporlama

---

## 🖥️ Arayüz Kullanımı

Uygulama 6 ana sekmeden oluşur:
### 💡 1. Yardım
- Programın amacı ve kullanım kılavuzu yer alır.
- Sık sorulan sorular ile kullanıcının merak ettikleri cevaplandırılır.

### 🌐 2. Veri Çekme
- Güncel TV programlarını internetten çeker.
- Program türleri, yayın saatleri ve kanal bilgileri toplanır.
- Bu veri, optimizasyon sürecinde kullanılacak ana veri kümesini oluşturur.

### 💟 3. Program Tercihleri
- Kullanıcı, program türlerine puan vererek tercihlerini belirler.
- Aynı türdeki programların üst üste gelmemesi veya dengeli dağılması sağlanır.
- Kullanıcı tercihleri, optimizasyon sürecinde bir ağırlıklandırma faktörü olarak kullanılır.

### ⏰ 4. Zaman Tercihleri
- Kullanıcı, günün hangi saatlerinde TV izleyebileceğini belirler.
- Belirtilen zaman dilimleri dışındaki programlar optimize edilen plana dahil edilmez.
- Kullanıcı, farklı günler için farklı zaman dilimleri belirleyebilir.

### 🔍 5. Filtreleme
- Kullanıcı, izlemek istemediği kanalları, türleri ve programları çıkarabilir.
- Verilerin filtrelenmiş halini görüntüleyebilir.

### 🚀 6. Algoritma Seçimi ve Optimizasyon
Kullanıcı, 3 farklı optimizasyon algoritmasından birini seçerek program planını oluşturur:

| Algoritma | Çalışma Süresi | Optimalite | Kullanım Senaryosu |
|-----------|--------------|------------|-------------------|
| Açgözlü Algoritma (Greedy) | ⚡ Hızlı | Orta | Hızlı çözüm isteyenler |
| Kısıt Programlama | ⏱️ Orta | Yüksek | Kesin çözüm isteyenler |
| Genetik Algoritma | 🐢 Yavaş | Düşük | Büyük veri için uygun |

Optimizasyon tamamlandıktan sonra, kullanıcının izleme takvimi oluşturulur ve görselleştirilir.

---

## 📊 Çıktılar ve Raporlama
- Optimizasyon sonrası program planı bir tablo veya grafik olarak görüntülenir.
- Kullanıcı, planını `.xlsx` formatında dışa aktarabilir.
- Program süresi, tür dağılımı ve doluluk oranı gibi istatistikler görselleştirilir.

---

## 🚀 Nasıl Çalıştırılır?
1. Uygulamayı çalıştırmak için gerekli bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   streamlit run FrontEnd.py


## ✨Web Sitesi
[Web sitesi linkine tıklayarak lokale kurmadan demoya erişebilirsiniz.](https://tv-izleme-planlayici.streamlit.app/)