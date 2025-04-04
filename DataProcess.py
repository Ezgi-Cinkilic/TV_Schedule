from datetime import datetime
import pandas as pd
import requests
import pandas as pd
from bs4 import BeautifulSoup

def web_scrapping():
    # Günler listesi
    gunler = ["pazartesi", "sali", "carsamba", "persembe", "cuma", "cumartesi", "pazar"]
    
    # Verileri saklamak için liste oluştur
    veriler = []
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for gun in gunler:
        # Hedef URL
        url = f"https://www.hurriyet.com.tr/tv-rehberi/tum-programlar/{gun}/"
        
        # Sayfayı çek ve parse et
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Kanal listesini her gün için ayrı ayrı çek
        kanal_listesi = []
        channels = soup.find_all("li", class_="flow-module-channel")
        if channels:
            for channel in channels:
                link = channel.find("a", class_="flow-module-link")
                if link:
                    kanal_link = link["href"]  # Kanal sayfası linki
                    kanal_adı = kanal_link.split("/")[-2]
                    kanal_listesi.append(kanal_adı)
        
        # Tüm programları içeren alanlar
        programlar = soup.find_all("div", class_="flow-module-row")
        
        # Her bir row (program bloğu) için detayları al
        for kanal, program in zip(kanal_listesi, programlar):
            columns = program.find_all("div", class_="flow-module-col")
            
            for col in columns:
                # Tür (data-type özelliğinden)
                tur = col.get("data-type", "Bilinmiyor")
                
                # Program adı (Eğer başlık varsa çek)
                title_tag = col.find("h2", class_="column-title")
                ad = title_tag.text.strip() if title_tag else "Bilinmiyor"
                
                # Saat aralığı (span class="column-time")
                time_tag = col.find("span", class_="column-time")
                saat_araligi = time_tag.text.strip() if time_tag else "Saat Bilinmiyor"
                
                # Eğer kanal cartoon-network veya disney-junior ise, türü "Çizgi Dizi" yap
                if kanal in ["cartoon-network", "disney-junior"]:
                    tur = "Çizgi Dizi"
                    
                # Başlangıç ve bitiş saatini ayır
                if "-" in saat_araligi:
                    baslangic, bitis = saat_araligi.split("-")
                    baslangic = baslangic.strip()
                    bitis = bitis.strip()
                else:
                    baslangic, bitis = "Bilinmiyor", "Bilinmiyor"
                
                if ad != "Bilinmiyor":
                    ad = ad.split("\n")[0]  # Program adını temizle
                    veriler.append([kanal, tur, ad, gun.capitalize(), baslangic, bitis])
                
    # DataFrame oluştur
    columns = ["Kanal", "Tür", "Ad", "Gün", "Başlangıç Saati", "Bitiş Saati"]
    df = pd.DataFrame(veriler, columns=columns)
    df["Tür"] = df["Tür"].apply(lambda x: "dizi" if str(x).isdigit() else x)
  
    df.to_excel("tv_programlari_haftalik.xlsx")
    return df

def preprocess_and_sort_programs(program_df, user_preferences):
    # 1. ID sütunu ekleme
    program_df = program_df.reset_index().rename(columns={'index':'id'})
    
    # 2. Gün isimlerini düzeltme
    day_corrections = {
        'Pazartesi': 'Pazartesi',
        'Sali': 'Salı',
        'Carsamba': 'Çarşamba',
        'Persembe': 'Perşembe',
        'Cuma': 'Cuma',
        'Cumartesi': 'Cumartesi',
        'Pazar': 'Pazar'
    }
    program_df['Gün'] = program_df['Gün'].replace(day_corrections)
    program_df = program_df[program_df['Tür'] != 'diger'].copy()
   
    # 4. Geçersiz zaman aralıklarını filtreleme
    def time_to_minutes(t):
        if t == '24:00':
            return 24*60
        return datetime.strptime(t, "%H:%M").hour * 60 + datetime.strptime(t, "%H:%M").minute
    
    mask = (
        program_df['Başlangıç Saati'].apply(time_to_minutes) < 
        program_df['Bitiş Saati'].apply(time_to_minutes)
    )
    program_df = program_df[mask].copy()

    # 5. Program süresi hesaplama
    start_times = pd.to_datetime(program_df["Başlangıç Saati"], format="%H:%M", errors='coerce')
    end_times = pd.to_datetime(program_df["Bitiş Saati"], format="%H:%M", errors='coerce')
    
    end_times = end_times.where(
        program_df['Bitiş Saati'] != '24:00',
        start_times + pd.DateOffset(hours=24)
    )
    
    program_df['program_suresi'] = (end_times - start_times).dt.total_seconds() / 60
    
    # 6. Kısa programları filtreleme
    program_df = program_df[program_df['program_suresi'] > 10].copy()

    # 7. Priority ve value hesaplama
    program_df['priority'] = program_df['Tür'].apply(
        lambda x: user_preferences["türler"].get(x, 0)
    )
    program_df['value'] = program_df['program_suresi'] * program_df['priority']

    # 8. Sıralama ve ID'leri yeniden oluşturma
    sorted_df = program_df.sort_values(
        by=['value', 'Başlangıç Saati'], 
        ascending=[False, True]
    ).reset_index(drop=True)
    sorted_df['id'] = sorted_df.index  # ID'leri sıralamadan sonra yeniden oluştur
    
    sorted_df.to_excel("haftalik_düzenli.xlsx")
    return sorted_df


user_preferences = {
    "türler": {
        "haber": 10,  # En çok sevdiği tür (yüksek puan)
        "dizi": 8,      # İkinci en çok sevdiği tür
        "yasam": 5,     # Orta düzeyde sevdiği tür
        "Çizgi Dizi": 3,      # Az sevdiği tür
        "film": 2,   # En az sevdiği tür
        "eglence" : 1,
        "diger" : 1
    }
}

program_df = pd.read_excel("tv_programlari_haftalik.xlsx")
programs = preprocess_and_sort_programs(program_df, user_preferences)
programs.to_excel("haftalik_düzenli.xlsx")
programs = programs.to_dict(orient='records')