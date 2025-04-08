import streamlit as st
from datetime import time, datetime
from PIL import Image
import io
import plotly.graph_objects as go
import pandas as pd
import DataProcess as dp
import TV_Schedule_Greedy
from TV_Schedule_CP import TvSchedulerCP 
from TV_Schedule_GA import TvSchedulerGA  
import visualize
import TV_Schedule_CP
# Sayfa yapılandırmasını ayarla
st.set_page_config(
    page_title="TV İzleme Planlayıcı",
    page_icon=Image.open("tv_logo.png"),
    initial_sidebar_state="expanded"
)

tv_logo = Image.open("tv_logo.png")
img_bytes = io.BytesIO()
tv_logo.save(img_bytes, format="PNG")



#Arka plan rengini ayarla
st.markdown(
    """
    <style>
    .stApp {
        background: #f8fef3;
    }
    </style>
    """,
    unsafe_allow_html=True
)

#İkonu ve başlığı ayarla
col1, col2 = st.columns([1, 5])

with col1:
       st.markdown("""
       <div style='display: flex; align-items: center; height: 100%;'>
       """, unsafe_allow_html=True)
       st.image(tv_logo, use_column_width=True)
       st.markdown("</div>", unsafe_allow_html=True)


with col2:
    st.markdown("""
    <style>
    .gradient-text {
        font-weight: 700;
        background: linear-gradient(90deg, #FF8C00 0%, #FF0080 50%, #8000FF 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        padding: 10px;
        border-radius: 5px;
    }
    .gradient-header {
        background: linear-gradient(90deg, #FF8C00 0%, #FF0080 50%, #8000FF 100%);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .white-text {
        color: white !important;
        margin: 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(
        '<div class="gradient-header"><h1 class="white-text">TV İzleme Planlayıcısı</h1></div>', 
        unsafe_allow_html=True
    )


#--------------------------------------------
#--------Program Tercihlerini Al-------------
#--------------------------------------------

program_turleri = ['haber', 'dizi', 'yasam', 'Çizgi Dizi', 'film', 'eglence', 'spor']

program_colors = {
    "haber": "#FF0000",    # Kırmızı
    "dizi": "#00FF00",     # Yeşil
    "eglence": "#660099",  # Mor
    "spor": "#FFA500",     # Turuncu
    "yasam": "#FFFF00",    # Sarı
    "film": "#FF1493",     # Pembe
    "Çizgi Dizi": "#00FFFF" # Turkuaz        
}

def get_program_puanlari():
    # Dinamik CSS oluşturma
    css = """
    <style>
    .heart-icon {
        font-size: 20px;
        margin-right: 10px;
    }
    """
    
    for tur, color in program_colors.items():
        css += f"""
        div[data-testid="stSlider"] > div[data-testid="stHorizontalBlock"] > div:nth-child({list(program_colors.keys()).index(tur)+1}) > div > div > div > div {{
            background: {color} !important;
        }}
        div[data-testid="stSlider"] > div[data-testid="stHorizontalBlock"] > div:nth-child({list(program_colors.keys()).index(tur)+1}) > div > div > div > div:hover {{
            background: {color} !important;
            opacity: 0.8;
        }}
        """
    
    st.markdown(css, unsafe_allow_html=True)

    st.write("Program türlerini ne kadar sevdiğinizi seçin! (0-10 arası puan verin):")
    
    puanlar = {}
    cols = st.columns(2)
    
    for i, tur in enumerate(program_turleri):
        with cols[i % 2]:
            st.markdown(f'<span class="heart-icon" style="color:{program_colors[tur]}">❤</span> <span style="color:{program_colors[tur]}">**{tur}**</span>', unsafe_allow_html=True)
            puan = st.slider(
                label=tur,
                min_value=0,
                max_value=10,
                value=5,
                key=f'slider_{tur}',
                label_visibility="collapsed"
            )
            puanlar[tur] = puan
    
    # Kaydet butonu ve işlemler
    if st.button("💾 Program Tercihlerimi Kaydet ve İşle", type="primary", use_container_width=True):
        user_preferences = {
            "türler": puanlar
        }
        st.session_state['user_preferences'] = user_preferences
        
        try:
            # TV programlarını yükle ve işle
            program_df = pd.read_excel("tv_programlari_haftalik.xlsx")
            processed_programs = dp.preprocess_and_sort_programs(program_df, user_preferences)
            
            # Excel'e kaydet
            processed_programs.to_excel("haftalik_düzenli.xlsx", index=False)
            
            # Sonuçları göster
            st.success("Tercihleriniz başarıyla kaydedildi ve programlar işlendi!")
            #st.balloons()
            
            # Önizleme
            with st.expander("🔍 İşlenmiş Programları Görüntüle"):
                st.dataframe(processed_programs.head(10))
                
            # İndirme linki
            with open("haftalik_düzenli.xlsx", "rb") as file:
                st.download_button(
                    label="📥 İşlenmiş Programları İndir",
                    data=file,
                    file_name="haftalik_düzenli.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {str(e)}")
    
    return puanlar



#------------------------------------------------
#--------Uygun Zaman Aralıklarını Al-------------
#------------------------------------------------


def get_uygunluk_zamanlari():

    st.markdown("""
    <style>
    .day-section {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .time-input {
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.info("""
    **Her gün için uygun olduğunuz zaman aralıklarını seçin.**  
    ⭐ Birden fazla zaman aralığı ekleyebilirsiniz.  
    ⭐ Başlangıç saati bitiş saatinden önce olmalıdır.
    """)

    days_of_week = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    user_slots = []
    
    for day in days_of_week:
        with st.container():
            st.markdown(f'<div class="day-header">🎯 {day}</div>', unsafe_allow_html=True)
            
            # Dinamik zaman aralığı ekleme
            num_slots = st.number_input(
                f"{day} için kaç farklı zaman aralığı eklemek istiyorsunuz?", 
                min_value=0, max_value=5, value=1, key=f"{day}_num_slots",
                help=f"{day} günü için kaç farklı uygunluk aralığınız var?"
            )
            
            for i in range(num_slots):
                cols = st.columns(2)
                with cols[0]:
                    start_time = st.time_input(
                        f"Başlangıç Saati {i+1}",
                        value=time(9, 0),
                        key=f"start_{day}_{i}"
                    )
                with cols[1]:
                    end_time = st.time_input(
                        f"Bitiş Saati {i+1}",
                        value=time(17, 0),
                        key=f"end_{day}_{i}"
                    )
                
                if start_time < end_time:
                    user_slots.append({
                        "day": day,
                        "start_time": start_time.strftime("%H:%M"),
                        "end_time": end_time.strftime("%H:%M")
                    })
                else:
                    st.warning(f"Başlangıç saati bitiş saatinden önce olmalıdır! ({day} {i+1}. aralık)")

    # Kaydetme butonu
    if st.button("💾 Uygunluk Takvimimi Kaydet", type="primary", use_container_width=True):
        st.session_state['user_slots'] = user_slots
        st.success("Uygunluk takviminiz başarıyla kaydedildi!")
        #st.balloons()
        
        # Önizleme
        with st.expander("🔍 Kaydedilen Uygunluk Takvimi"):
            if len(user_slots) > 0:
                st.code("user_slots = [")
                for slot in user_slots:
                    st.code(f'    {{"day": "{slot["day"]}", "start_time": "{slot["start_time"]}", "end_time": "{slot["end_time"]}"}},')
                st.code("]")
            else:
                st.warning("Henüz zaman aralığı eklenmedi!")

    return user_slots



#------------------------------------------------
#--------Algoritmalar----------------------------
#------------------------------------------------



def acgozlu_algoritma():
    # Kontroller
    if 'user_preferences' not in st.session_state:
        st.error("Lütfen önce program tercihlerinizi kaydedin!")
        return None
    if 'user_slots' not in st.session_state:  # user_slots yerine uygunluk_zamanlari
        st.error("Lütfen önce uygunluk zamanlarınızı kaydedin!")
        return None
    
    with st.spinner("Açgözlü algoritma çalıştırılıyor, lütfen bekleyin..."):
        try:

            # Artık programs parametresine gerek yok
            scheduled_programs, total_val = TV_Schedule_Greedy.greedy_scheduler(
                user_slots=st.session_state['user_slots'],
                programs_file="haftalik_program_filtreli.xlsx"
            )

           
            
            # Sonuçları göster
            st.success("✅ Açgözlü algoritma başarıyla tamamlandı!")
            st.balloons()
            
            # İstatistikler
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Program Sayısı", len(scheduled_programs))
            with col2:
                st.metric("Toplam Değer (Objective)", f"{total_val:.2f}")
            with col3:
                avg_duration = sum(p['program_suresi'] for p in scheduled_programs)/len(scheduled_programs) if scheduled_programs else 0
                st.metric("Ortalama Program Süresi", f"{avg_duration:.1f} dakika")
                    
            visualize.visualize_schedule_interactive(st.session_state['user_slots'], [(p, {
                 "day": p["Gün"],
                 "start_time": p["Başlangıç Saati"],
                 "end_time": p["Bitiş Saati"]
             }) for p in scheduled_programs], "greedy")
             
             
            # Tür dağılımı
            if scheduled_programs:
                tur_dagilimi = pd.DataFrame.from_dict(
                    {tür: sum(1 for p in scheduled_programs if p["Tür"] == tür) 
                    for tür in st.session_state['user_preferences']['türler']},  # Sadece kullanıcının tercih ettiği türler
                    orient='index',
                    columns=['Sayı']
                )
                st.subheader("Program Türü Dağılımı")
                st.bar_chart(tur_dagilimi)
            
            # Program listesi
            with st.expander("📋 Planlanan Programları Görüntüle"):
                if scheduled_programs:
                    st.dataframe(pd.DataFrame(scheduled_programs))[
                        ['Gün', 'Kanal', 'Ad', 'Tür', 'Başlangıç Saati', 'Bitiş Saati', 'program_suresi']
                    ].sort_values(['Gün', 'Başlangıç Saati'])
                else:
                    st.warning("Hiç program planlanamadı")
            
            return {
                "scheduled_programs": scheduled_programs,
                "total_value": total_val,
                "tur_dagilimi": tur_dagilimi.to_dict() if scheduled_programs else {}
            }
            
        except Exception as e:
            st.error(f"❌ Algoritma çalıştırılırken hata oluştu: {str(e)}")
            return None

def kisit_programlama():
    # Önce kontrolleri yapalım
    if 'user_preferences' not in st.session_state:
        st.error("Lütfen önce program tercihlerinizi kaydedin!")
        return None
    if 'user_slots' not in st.session_state:
        st.error("Lütfen önce uygunluk zamanlarınızı kaydedin!")
        return None

    with st.spinner("Kısıt Programlama çalıştırılıyor, lütfen bekleyin..."):
        try:
            # 1. Çözücüyü başlat
            cp_scheduler = TvSchedulerCP(
                user_slots=st.session_state['user_slots'],
                programs_file="haftalik_program_filtreli.xlsx"
            )
            
            # 2. Problemi çöz
            scheduled_programs, total_val = cp_scheduler.solve()
            
            # 3. Görselleştirme için veriyi uygun formata dönüştür
            # solve() fonksiyonu zaten (program_dict, slot_dict) formatında dönüyor
            # Bu nedenle ek dönüşüme gerek yok
            
            # 4. Sonuçları göster
            st.success("✅ Kısıt Programlama başarıyla tamamlandı!")
            
            # 5. İstatistikler
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Program Sayısı", len(scheduled_programs))
            with col2:
                st.metric("Toplam Değer (Objective)", f"{total_val:.2f}")
            with col3:
                avg_duration = sum(p[0]['program_suresi'] for p in scheduled_programs)/len(scheduled_programs) if scheduled_programs else 0
                st.metric("Ortalama Program Süresi", f"{avg_duration:.1f} dakika")
            
            # 6. Görselleştirmeyi çiz
            visualize.visualize_schedule_interactive(
                st.session_state['user_slots'], 
                scheduled_programs, 
                " (Kısıt Programlama)"
            )
            
            # 7. Tür dağılımı (program bilgileri tuple'ın ilk elemanında)
            if scheduled_programs:
                tur_dagilimi = pd.DataFrame.from_dict(
                    {tür: sum(1 for p in scheduled_programs if p[0]["Tür"] == tür) 
                    for tür in st.session_state['user_preferences']['türler']},
                    orient='index',
                    columns=['Sayı']
                )
                st.subheader("Program Türü Dağılımı")
                st.bar_chart(tur_dagilimi)
            
            # 8. Detaylı liste (program bilgileri tuple'ın ilk elemanında)
            with st.expander("📋 Planlanan Programları Görüntüle"):
                if scheduled_programs:
                    program_list = [p[0] for p in scheduled_programs]
                    st.dataframe(pd.DataFrame(program_list)[
                        ['Gün', 'Kanal', 'Ad', 'Tür', 'Başlangıç Saati', 'Bitiş Saati', 'program_suresi']
                    ].sort_values(['Gün', 'Başlangıç Saati']))
                else:
                    st.warning("Hiç program planlanamadı")
            
            return {
                "scheduled_programs": [p[0] for p in scheduled_programs],
                "total_value": total_val,
                "tur_dagilimi": tur_dagilimi.to_dict() if scheduled_programs else {}
            }
            
        except Exception as e:
            st.error(f"❌ Kısıt Programlama çalıştırılırken hata oluştu: {str(e)}")
            st.error(f"Hata detayı: {repr(e)}")
            return None
        
        
def genetik_algoritma():
    # Önce kontrolleri yapalım
    if 'user_preferences' not in st.session_state:
        st.error("Lütfen önce program tercihlerinizi kaydedin!")
        return None
    if 'user_slots' not in st.session_state:
        st.error("Lütfen önce uygunluk zamanlarınızı kaydedin!")
        return None

    with st.spinner("Genetik algoritma çalıştırılıyor, lütfen bekleyin..."):
        try:
            # 1. Çözücüyü başlat
            ga_scheduler = TvSchedulerGA(
                user_slots=st.session_state['user_slots'],
                program_file="haftalik_program_filtreli.xlsx"
            )
            
            # 2. Problemi çöz
            scheduled_programs = ga_scheduler.schedule()
            
            # 3. Görselleştirme için veriyi uygun formata dönüştür
            visualization_data = []
            for program, slot in scheduled_programs:
                visualization_data.append((
                    program,
                    {
                        "day": slot["day"],
                        "start_time": slot["start_time"],
                        "end_time": slot["end_time"]
                    }
                ))
            
            # 4. Toplam değeri hesapla
            total_val = sum(p[0]['value'] for p in visualization_data)
            
            # 5. Sonuçları göster
            st.success("✅ Genetik algoritma başarıyla tamamlandı!")
            
            # 6. İstatistikler
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Program Sayısı", len(scheduled_programs))
            with col2:
                st.metric("Toplam Değer (Objective)", f"{total_val:.2f}")
            with col3:
                avg_duration = sum(p[0]['program_suresi'] for p in scheduled_programs)/len(scheduled_programs) if scheduled_programs else 0
                st.metric("Ortalama Program Süresi", f"{avg_duration:.1f} dakika")
            
            # 7. Görselleştirmeyi çiz
            visualize.visualize_schedule_interactive(
                st.session_state['user_slots'], 
                visualization_data, 
                " (Genetik Algoritma)"
            )
            
            # 8. Tür dağılımı
            if scheduled_programs:
                tur_dagilimi = pd.DataFrame.from_dict(
                    {tür: sum(1 for p in scheduled_programs if p[0]["Tür"] == tür) 
                    for tür in st.session_state['user_preferences']['türler']},
                    orient='index',
                    columns=['Sayı']
                )
                st.subheader("Program Türü Dağılımı")
                st.bar_chart(tur_dagilimi)
            
            # 9. Detaylı liste
            with st.expander("📋 Planlanan Programları Görüntüle"):
                if scheduled_programs:
                    program_list = [p[0] for p in scheduled_programs]
                    st.dataframe(pd.DataFrame(program_list)[
                        ['Gün', 'Kanal', 'Ad', 'Tür', 'Başlangıç Saati', 'Bitiş Saati', 'program_suresi', 'value']
                    ].sort_values(['Gün', 'Başlangıç Saati']))
                else:
                    st.warning("Hiç program planlanamadı")
            
            return {
                "scheduled_programs": [p[0] for p in scheduled_programs],
                "total_value": total_val,
                "tur_dagilimi": tur_dagilimi.to_dict() if scheduled_programs else {}
            }
            
        except Exception as e:
            st.error(f"❌ Genetik algoritma çalıştırılırken hata oluştu: {str(e)}")
            st.error(f"Hata detayı: {repr(e)}")
            return None




#------------------------------------------------
#--------Sayfa Tasarımı-------------
#------------------------------------------------



def main():
    
    # 5 Sekmeli Yapı yerine 6 sekme
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💡 Yardım",
        "🌐 Veri Çekme", 
        "💟 Program Tercihleri", 
        "⏰ Zaman Tercihleri",
        "🔍 Filtreleme",  # Yeni eklenen sekme
        "🚀 Algoritma Çalıştır"
    ])
    
    with tab1:
        st.subheader("TV Program Planlayıcı Yardım Merkezi", divider='rainbow')
        
        # 1. Uygulama Tanıtımı
        with st.container():
            st.subheader("🎯 Uygulama Nedir?")
            st.markdown("""
            <div style='
                background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #6366f1;
                margin-bottom: 25px;
            '>
            <p style='font-size: 16px; line-height: 1.6;'>
            <strong>TV Program Planlayıcı</strong>, izlemek istediğiniz programları:<br><br>
            ✓ <span style='color: #6366f1;'>Tercihlerinize göre</span> otomatik seçer<br>
            ✓ <span style='color: #6366f1;'>Uygun olduğunuz saatlere</span> göre planlar<br>
            ✓ <span style='color: #6366f1;'>3 farklı algoritma</span> ile optimize eder
            </p>
            </div>
            """, unsafe_allow_html=True)
    
        # 2. Hızlı Başlangıç Kılavuzu
        with st.container():
            st.subheader("📌 Hızlı Başlangıç Kılavuzu")
            st.markdown("""
            <div style='
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #10b981;
                margin-bottom: 25px;
            '>
            <ol style='font-size: 16px; line-height: 2; padding-left: 20px;'>
                <li><strong style='color: #10b981;'>Veri Çekme</strong> sekmesinden güncel programları indirin</li>
                <li><strong style='color: #10b981;'>Program Türü Tercihleri</strong> ile ne izlemek istediğinizi seçin</li>
                <li><strong style='color: #10b981;'>Zaman Tercihleri</strong> ile müsait olduğunuz saatleri girin</li>
                <li><strong style='color: #10b981;'>Kanal Tercihleri</strong> ile istemediğiniz kanalları ve programları filtreleyin</li>
                <li><strong style='color: #10b981;'>Algoritma Çalıştır</strong> ile kişisel programınızı oluşturun</li>
                <strong style='color: #b91037;'>Programın Doğru Çalışması İçin Tüm Sayfalardaki Kaydet Butonuna Tıklamayı Unutmayın!</strong>
            </ol>
            </div>
            """, unsafe_allow_html=True)
        
        # 3. Sık Sorulan Sorular (Tıklamalı)
        st.subheader("❓ Sık Sorulan Sorular")
        
        # SSS için özel CSS
        st.markdown("""
        <style>
        .faq-question {
            background-color: #f1f3f5;
            padding: 12px;
            border-radius: 8px;
            margin-top: 10px;
            cursor: pointer;
            font-weight: bold;
        }
        .faq-answer {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 0 0 8px 8px;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # SSS Öğeleri
        faqs = [
            {
                "question": "🔹 Veriler güncel değilse ne yapmalıyım?",
                "answer": "Veri Çekme sekmesinden 'Güncelle' butonuna basın. Hata alırsanız internet bağlantınızı kontrol edin."
            },
            {
                "question": "🔹 Programlar çakışıyorsa nasıl düzeltebilirim?",
                "answer": "Sistem otomatik olarak maksimum 10 dakikalık çakışmalara izin vermektedir. Kod üzerinden istenen çakışma süresi ayarlanabilir."
            },
            {
                "question": "🔹 Algoritma sonuçlarından memnun değilsem?",
                "answer": "1. Tercih puanlarınızı gözden geçirin\n2. Farklı algoritma deneyin\n3. Uygunluk saatlerinizi genişletin"
            },
            {
                "question": "🔹 Kesin izlemek istediğim programları nasıl seçebilirim?",
                "answer": "Mevcut sürümde maalesef izlemek istenilen programlar seçilememektedir. Ancak izlemek istemediğiniz kanalları ve programları filtreleyebilirsiniz."
            },
            {
                "question": "🔹 Excel dosyası nereye kaydediliyor?",
                "answer": "Uygulamanın çalıştığı ana klasöre kaydedilir. 'haftalik_düzenli.xlsx' adıyla bulabilirsiniz."
            }
        ]
        
        for faq in faqs:
            with st.expander(faq["question"], expanded=False):
                st.markdown(f"""
                <div class='faq-answer'>
                {faq["answer"]}
                </div>
                """, unsafe_allow_html=True)
        
        # İletişim Bilgileri
        st.markdown("---")
        st.markdown("""
        <div style='text-align:center; margin-top:30px;'>
            <h4>Yap441-Dönem Projesi</h4>
            <p>Ezgi Cinkılıç - 201301012<br>
            <p>✉️ e.cinkilic@etu.edu.tr<br>
        </div>
        """, unsafe_allow_html=True)        
        
    with tab2:
        st.subheader("Güncel TV Program Verilerini İndir", divider='rainbow')
        st.markdown("""
        <style>
        .scrap-info {
            background-color: #f0f8ff;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        </style>
        <div class="scrap-info">
        ℹ️ <b>Güncel TV programlarını çekmek için butona basın.</b><br>
        ⏳ Bu işlem internet hızınıza bağlı olarak 1 dakikadan az süremektedir.
        </div>
        """, unsafe_allow_html=True)
        
        if st.button('📡 Verileri Çek ve Güncelle', type="primary", help="Hürriyet TV Rehberi'nden güncel programları çeker"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("Bağlantı kuruluyor...")
                progress_bar.progress(10)
                
                # Web scraping işlemini başlat
                status_text.text("TV program verileri çekiliyor...")
                from DataProcess import web_scrapping  # Fonksiyonu import ediyoruz
                df = web_scrapping()
                progress_bar.progress(70)
                
                status_text.text("Veriler işleniyor...")
                # Veri temizleme işlemleri
                df = df[df['Ad'] != 'Bilinmiyor'].drop_duplicates()
                progress_bar.progress(90)
                
                status_text.text("Excel dosyası oluşturuluyor...")
                df.to_excel("tv_programlari_haftalik.xlsx", index=False)
                progress_bar.progress(100)
                
                st.success("✅ Veriler başarıyla güncellendi!")
                
                # Önizleme göster
                with st.expander("📊 Son Çekilen Verileri Görüntüle"):
                    st.dataframe(df.head(10))
                    
                # İndirme butonu
                with open("tv_programlari_haftalik.xlsx", "rb") as file:
                    st.download_button(
                        label="📥 TV Programlarını İndir",
                        data=file,
                        file_name="tv_programlari_haftalik.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
            except Exception as e:
                progress_bar.progress(0)
                status_text.text("")
                st.error(f"❌ Hata oluştu: {str(e)}")
                st.error("Lütfen internet bağlantınızı kontrol edip tekrar deneyin.")
    
    with tab3:
        st.subheader("Program Türü Tercihleriniz", divider='rainbow')
        get_program_puanlari()
    
    with tab4:
        st.subheader("Haftalık Uygunluk Takviminiz", divider='rainbow')
        
        def save_filtered_excel(user_slots):
            """Uygunluk zamanına göre filtrelenmiş Excel'i kaydeder"""
            try:
                df = pd.read_excel("haftalik_düzenli.xlsx")
                filtered_programs = []
                
                for _, row in df.iterrows():
                    program_day = row['Gün']
                    program_start = datetime.strptime(row['Başlangıç Saati'], "%H:%M").time()
                    program_end = datetime.strptime(row['Bitiş Saati'], "%H:%M").time()
                    
                    # Kullanıcının uygun olduğu slotlarla karşılaştır
                    for slot in user_slots:
                        if slot['day'] == program_day:
                            slot_start = datetime.strptime(slot['start_time'], "%H:%M").time()
                            slot_end = datetime.strptime(slot['end_time'], "%H:%M").time()
                            
                            # Programın kullanıcının uygun olduğu slot içinde olup olmadığını kontrol et
                            if (slot_start <= program_start <= slot_end) and (slot_start <= program_end <= slot_end):
                                filtered_programs.append(row.to_dict())
                                break
                
                # Filtrelenmiş programları yeni bir Excel dosyasına kaydet
                filtered_df = pd.DataFrame(filtered_programs)
                filtered_df.to_excel("haftalik_zaman_filtreli.xlsx", index=False)
                st.session_state['filtered_excel_ready'] = True
                return True
                
            except Exception as e:
                st.error(f"Excel filtreleme hatası: {str(e)}")
                return False
    
        def get_uygunluk_zamanlari():
            st.markdown("""
            <style>
            .day-section {
                background-color: #f0f2f6;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 15px;
            }
            .time-input {
                margin-bottom: 10px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.info("""
            **Her gün için uygun olduğunuz zaman aralıklarını seçin.**  
            ⭐ Birden fazla zaman aralığı ekleyebilirsiniz.  
            ⭐ Başlangıç saati bitiş saatinden önce olmalıdır.
            """)
    
            days_of_week = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
            user_slots = []
            
            for day in days_of_week:
                with st.container():
                    st.markdown(f'<div class="day-header">🎯 {day}</div>', unsafe_allow_html=True)
                    
                    num_slots = st.number_input(
                        f"{day} için kaç farklı zaman aralığı eklemek istiyorsunuz?", 
                        min_value=0, max_value=5, value=1, key=f"{day}_num_slots"
                    )
                    
                    for i in range(num_slots):
                        cols = st.columns(2)
                        with cols[0]:
                            start_time = st.time_input(
                                f"Başlangıç Saati {i+1}",
                                value=time(9, 0),
                                key=f"start_{day}_{i}"
                            )
                        with cols[1]:
                            end_time = st.time_input(
                                f"Bitiş Saati {i+1}",
                                value=time(17, 0),
                                key=f"end_{day}_{i}"
                            )
                        
                        if start_time < end_time:
                            user_slots.append({
                                "day": day,
                                "start_time": start_time.strftime("%H:%M"),
                                "end_time": end_time.strftime("%H:%M")
                            })
                        else:
                            st.warning(f"Başlangıç saati bitiş saatinden önce olmalıdır! ({day} {i+1}. aralık)")
    
            # Kaydetme butonu
            if st.button("💾 Uygunluk Takvimimi Kaydet ve Filtrele", type="primary", use_container_width=True):
                st.session_state['user_slots'] = user_slots
                if save_filtered_excel(user_slots):
                    st.success("Uygunluk takviminiz başarıyla kaydedildi ve programlar filtrelendi!")
                    
                    # Önizleme
                    with st.expander("🔍 Kaydedilen Uygunluk Takvimi"):
                        if len(user_slots) > 0:
                            st.code("user_slots = [")
                            for slot in user_slots:
                                st.code(f'    {{"day": "{slot["day"]}", "start_time": "{slot["start_time"]}", "end_time": "{slot["end_time"]}"}},')
                            st.code("]")
                        else:
                            st.warning("Henüz zaman aralığı eklenmedi!")
                
                # Filtrelenmiş veriyi göster
                st.markdown("### 🎯 Uygun Olduğunuz Programlar")
                try:
                    filtered_df = pd.read_excel("haftalik_zaman_filtreli.xlsx")
                    st.dataframe(filtered_df)
                except:
                    st.warning("Filtrelenmiş program listesi bulunamadı")
    
            return user_slots
    
        get_uygunluk_zamanlari()
            
    with tab5:  # Yeni Filtreleme Sekmesi
        st.subheader("Program Filtreleme Ayarları", divider='rainbow')
        
        try:
            # Excel'den verileri yükle
            df = pd.read_excel("haftalik_zaman_filtreli.xlsx")
            
            # Kanal seçimi
            st.markdown("### 📺 Kanal Filtreleme")
            kanallar = df['Kanal'].unique().tolist()
            selected_kanallar = st.multiselect(
                "Filtrelemek istediğiniz kanalları seçin:",
                options=kanallar,
                default=kanallar,
                key="kanal_filtre"
            )
            
            # Seçili kanallara göre filtrele
            filtered_by_kanal = df[df['Kanal'].isin(selected_kanallar)]
            
            # Tür/Kategori seçimi
            st.markdown("### 🏷️ Tür/Kategori Seçimi")
            turler = filtered_by_kanal['Tür'].unique().tolist()
            selected_turler = st.multiselect(
                "Hangi türlerdeki programları görmek istersiniz?",
                options=turler,
                default=turler,
                key="tur_filtre"
            )
            
            # Seçili türlere göre filtrele
            filtered_by_tur = filtered_by_kanal[filtered_by_kanal['Tür'].isin(selected_turler)]
            
            # Her tür için ayrı program seçimi
            st.markdown("### 📝 Türlere Göre Program Seçimi")
            
            # Tüm seçili programları saklayacağımız liste
            all_selected_programs = []
            
            # CSS ile multiselect genişliğini artırma
            st.markdown("""
            <style>
                .stMultiSelect [data-baseweb=select] span{
                    max-width: 500px;
                    font-size: 0.9rem;
                }
                .stMultiSelect div[role="button"] p {
                    white-space: normal !important;
                    overflow: visible !important;
                    text-overflow: unset !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Her tür için ayrı bir multiselect oluştur
            for tur in selected_turler:
                tur_programlari = filtered_by_tur[filtered_by_tur['Tür'] == tur]['Ad'].unique().tolist()
                
                st.markdown(f"#### {tur} Programları")
                selected_programs = st.multiselect(
                    f"{tur} türünden hangi programları izlemek istersiniz?",
                    options=tur_programlari,
                    default=tur_programlari,
                    key=f"program_{tur}",
                    format_func=lambda x: x[:50] + "..." if len(x) > 50 else x
                )
                
                # Seçilen programları listeye ekle
                all_selected_programs.extend(selected_programs)
            
            # Filtrelenmiş veriyi göster
            st.markdown("### 🔎 Filtrelenmiş Program Listesi")
            final_filtered = df[
                (df['Kanal'].isin(selected_kanallar)) & 
                (df['Tür'].isin(selected_turler)) & 
                (df['Ad'].isin(all_selected_programs))
            ]
            
            # DataFrame görüntüleme ayarları
            st.dataframe(
                final_filtered,
                width=1000,
                height=600,
                column_config={
                    "Kanal": st.column_config.TextColumn(width="medium"),
                    "Ad": st.column_config.TextColumn(width="large"),
                    "Tür": st.column_config.TextColumn(width="medium"),
                },
                hide_index=True
            )
            
            # Filtreleri session_state'e kaydet
            st.session_state['filtered_programs'] = final_filtered.to_dict(orient='records')
            
            # Kaydetme butonu
            if st.button("💾 Filtreleme Ayarlarını Kaydet", type="primary", key="save_filtered_programs"):
                try:
                    # DataFrame'i Excel olarak kaydet
                    final_filtered.to_excel("haftalik_program_filtreli.xlsx", index=False)
                    
                    # Kullanıcıya bilgi ver
                    st.success("Kanal, tür ve program tercihleriniz başarıyla kaydedildi!")
                    
                    # İndirme butonu ekle
                    with open("haftalik_program_filtreli.xlsx", "rb") as file:
                        st.download_button(
                            label="📥 Filtrelenmiş Programları İndir",
                            data=file,
                            file_name="haftalik_program_filtreli.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                except Exception as e:
                    st.error(f"Kaydetme işlemi sırasında hata oluştu: {str(e)}")
            
            st.success("Filtreleme ayarları kaydedildi!")
            
        except Exception as e:
            st.error(f"Filtreleme yapılırken hata oluştu: {str(e)}")
            st.info("Lütfen önce 'Veri Çekme' sekmesinden verileri yükleyin")
    
    with tab6:  # Eskiden tab5 olan kısım
        st.subheader("Algoritma Seçimi ve Çalıştırma", divider='rainbow')
        
        if 'user_preferences' in st.session_state:
            st.success("✔ Program tercihleri kaydedildi")
        else:
            st.warning("✖ Program tercihleri kaydedilmedi")
            
        if 'user_slots' in st.session_state:
            st.success("✔ Zaman tercihleri kaydedildi")
        else:
            st.warning("✖ Zaman tercihleri kaydedilmedi")
        algorithm = st.selectbox(
                "Çalıştırmak istediğiniz algoritmayı seçin:",
                ["Açgözlü Algoritma", "Kısıt Programlama", "Genetik Algoritma"],
                index=0
            )
            
        if st.button('🔍 Algoritmayı Çalıştır', type="primary", use_container_width=True):
            if 'user_slots' not in st.session_state:
                    st.error("Lütfen önce Program Tercihleri sekmesinden tercihlerinizi kaydedin!")
            elif 'user_slots' not in st.session_state:
                    st.error("Lütfen önce Zaman Tercihleri sekmesinden uygunluk zamanlarınızı kaydedin!")
            else:
                    if algorithm == "Açgözlü Algoritma":
                            result = acgozlu_algoritma()
                    elif algorithm == "Kısıt Programlama":
                            result = kisit_programlama()
                    else:
                            result = genetik_algoritma()
                        
                    if result:
                            st.success(f"{algorithm} başarıyla tamamlandı!")
                            st.balloons()
        
            
        # Sonuçların Gösterimi
        if 'algorithm_result' in st.session_state:
            st.subheader("⏱️ Algoritma Sonuçları")
            st.json(st.session_state['algorithm_result']) 
            
main()