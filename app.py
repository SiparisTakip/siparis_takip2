from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
import pandas as pd
from supabase import create_client, Client
import re
url = "https://ezyhoocwfrocaqsehler.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6eWhvb2N3ZnJvY2Fxc2VobGVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjcyOTkzOTUsImV4cCI6MjA0Mjg3NTM5NX0.3A2pCuleW0RnGIlCaM5pALWw8fB_KW_y2-qsIJ1_FJI"
supabase_DB = "siparislistesi"
#kargo kullanıcı adı şifre ve kargo kodu
kullanici_Adi = "seffafbutik@yesilkar.com"
sifre = "Ma123456"
# Supabase Client oluştur
supabase: Client = create_client(url, key)
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
      try:  
        takip = request.form.get("takip_no")
        def duzenle_telefon_numarasi(takip):
            takip = takip.replace(" ", "")            
            # Başında sıfır yoksa sıfır ekle
            if not takip.startswith("0"):
                takip = "0" + takip            
            return takip    
            
        takip = duzenle_telefon_numarasi(takip)             
        if len(takip) == 11:
            tarih_baslangic = datetime.now() - timedelta(days=15)
            tarih_bitis = datetime.now().strftime("%d.%m.%Y")
            tarih_baslangic = tarih_baslangic.strftime("%d.%m.%Y")

            # Giriş ve verilerin alınması
            login_link = "https://webpostman.yesilkarkargo.com/user/login"
            headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0'
                }

                # Giriş isteği yap
            login_response = requests.get(login_link, headers=headers)

                # BeautifulSoup ile HTML'i ayrıştır
            bs = BS(login_response.content, 'html5lib')

                # Giriş form verileri ve token değerini al
            form_data = {
                    "token": bs.find('input', attrs={'name': 'token'})['value'],
                    "return_url": "/",
                    "email": kullanici_Adi,
                    "password": sifre
                }



            giris = requests.post(login_link, headers=headers, data=form_data,cookies=login_response.cookies)
            kullanici = BS(giris.content, "html.parser")
            cookie = login_response.cookies
            cargo_link = f"https://webpostman.yesilkarkargo.com/cargo/?alim_start={tarih_baslangic}&alim_end={tarih_bitis}&durums=-1&teslim_start=&teslim_end=&barkod=&isim=&soyisim=&seh_kod=0&ilce=&sipno={takip}&telno=&d_trbkod=0&d_subekod=0&btnSubmit=btnSubmit"
            cargo_response = requests.get(cargo_link, cookies=cookie)
            cargo_bs = BS(cargo_response.content, "html5lib")
            tablo = cargo_bs.find("table", {"id": "generalTables"}).find("tbody").find_all("tr")
            liste = []
            for satir in tablo:
                    sütunlar = satir.find_all("td")
                    veriler = [sütun.get_text(strip=True) for sütun in sütunlar]
                    liste.append({"TAKİP KODU":veriler[4], 
                    "İSİM SOYİSİM":veriler[5],
                    "TELEFON NU":"0"+veriler[19],
                    "SONUÇ":veriler[9],
                    "KARGO ŞUBESİ":veriler[10],
                    "ÜCRET":veriler[13]+" TL" ,
                    "siparis_takip": veriler[18] })
            df = pd.DataFrame(liste)

            # Telefon numarasına göre arama
            def arama(telefon_numarasi):
                sonuc = df[df["siparis_takip"] == telefon_numarasi]
                if not sonuc.empty:
                    return sonuc.iloc[0]["TAKİP KODU"]
                return None
            Takipyok_bilgiler = {
                    "Alıcı Adı": veriler[5],                    
                    "Teslimat Şube": "ARAS KARGO",
                    "Kargo Son Durum": "PAKET YAPILDI",                    
                    "İL-İLÇE":veriler[6] + " " + veriler[7] ,
                    "Ücret": veriler[13] + "TL"
                }
            takip_kodu = arama(takip)
            if not takip_kodu:
                return render_template("takipyok.html",veriler = veriler[5],bilgiler1=Takipyok_bilgiler)
            # Aras Kargo işlemleri
            url1 = f"https://kargotakip.araskargo.com.tr/mainpage.aspx?code={takip_kodu}"
            response = requests.get(url1, headers=headers)
            soup = BS(response.content, "html5lib")
            link_veri = soup.findAll("a")
            link_cikti = None
            link_cargo = None

            for a_tag in link_veri:
                href_attribute = a_tag['href']
                if "CargoInfoWaybillAndDelivered.aspx" in href_attribute:
                    link_cargo = f"https://kargotakip.araskargo.com.tr/{href_attribute}"
                if "CargoInfoTransactionAndRedirection.aspx" in href_attribute:
                    link_cikti = f"https://kargotakip.araskargo.com.tr/{href_attribute}"

            if link_cargo:
                cargo_response = requests.get(link_cargo)
                soup = BS(cargo_response.text, "html5lib")
                cıkıs_sube = soup.find("span", {"id": "cikis_subesi"}).text
                teslimat_sube = soup.find("span", {"id": "varis_subesi"}).text
                gonderim_tarihi = soup.find("span", {"id": "cikis_tarihi"}).text
                son_durum = soup.find("span", {"id": "Son_Durum"}).text
                alici_adi = soup.find("span", {"id": "alici_adi_soyadi"}).text
                gonderi_tip = soup.find("span", {"id": "LabelGonTipi"}).text
                response=requests.get(link_cikti)
                soup=BS(response.text,"html5lib")
                tablo = soup.find("table").findAll("tr")
                sonuçlar = []
                for td in tablo[0:2]:
                    metin = td.text  # <td> içindeki metni al
                    # Regex ile parçala
                    pattern = r"(\d{1,2}\.\d{1,2}\.\d{4} \d{2}:\d{2}:\d{2})([A-ZŞĞİÜÖÇ]+)([A-ZŞĞİÜÖÇ ]+)"
                    matches = re.findall(pattern, metin)

                    for match in matches:
                        tarih_saat, il, birim_islem = match
                        sonuçlar.append({
                            "Tarih/Saat": tarih_saat,
                            "İl": il,
                            "Birim/İşlem": birim_islem.strip()
                        })
                bilgiler = {
                    "Alıcı Adı": alici_adi,                    
                    "Teslimat Şube": teslimat_sube,
                    "Gönderim Tarihi": gonderim_tarihi,
                    "Kargo Son Durum": son_durum,
                    "Gönderi Tipi": gonderi_tip,
                    "Aras KARGO Takip Kodu":veriler[4]
                }

                return render_template("result.html", bilgiler=bilgiler, son_durum=son_durum, gonderi_tip=gonderi_tip, teslimat_sube=teslimat_sube, sonuçlar=sonuçlar)

        return render_template("index.html", error_message="Takip numarası bulunamadı. Lütfen geçerli bir numara girin! ")
      except (AttributeError, requests.exceptions.RequestException) as e:
               # except AttributeError or requests.exceptions.RequestException:             
        print("Tablo bulunamadı. Alternatif işlem yapılıyor.")   
        data = supabase.table(supabase_DB).select("*").eq("TELEFON",takip).execute()
        data = pd.DataFrame(data.data)
        if not data.empty:
            
                    bilgiler = {
                                "Alıcı Adı": data["İSİM SOYİSİM"].iloc[0],
                                "Adres": data["ADRES"].iloc[0],
                                "İl - İlçe": data["İL"].iloc[0] +" "+ data["İLÇE"].iloc[0],
                                "Telefon": data["TELEFON"].iloc[0]
                }
                    
        else:
           return render_template("index.html", error_message="Takip numarası bulunamadı. Lütfen geçerli bir numara girin! ")
        
        return render_template("result.html", bilgiler=bilgiler,supabase_takip = "supabase")   
    return render_template("index.html")
  

if __name__ == "__main__":
    app.run(debug=True)
