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
            api_url = "http://webpostman.yesilkarkargo.com:9999/restapi/client/cargo"

            # API Key ve Kullanıcı E-postası
            api_key = "apRFMXVkh5sKDnyCEqmGrASxTHOc4d71BgzZJ9Y0"
            user_email = "seffafbutik@yesilkar.com"

            # HTTP Başlıkları
            headers = {
                "Authorization": api_key,
                "From": user_email
            }
            # İsteğe bağlı parametreler (Örneğin belirli bir barkodu sorgulamak için)
            params = {
            "sipno" : takip
            }
            # GET isteği gönder
            response = requests.get(api_url, headers=headers, params=params)

            # Yanıtı kontrol et
            
            json_data = response.json()
            # "data" anahtarındaki ilk öğeden "gonderino" değerini al
            if "data" in json_data and len(json_data["data"]) > 0:
                gonderino = json_data["data"][0]["cikisno"]
                ad = json_data["data"][0]["aliciadi"]
                soyad = json_data["data"][0]["alicisoyad"]
                tutar = json_data["data"][0]["tutar"]
                il = json_data["data"][0]["sehiradi"]
                ilce = json_data["data"][0]["ilce"]
                Takipyok_bilgiler = {
                "Alıcı Adı": ad + " " + soyad ,                    
                "Teslimat Şube": "ARAS KARGO",
                "Kargo Son Durum": "PAKET YAPILDI",                    
                "İL-İLÇE": il + " " + ilce ,
                "Ücret": tutar + "TL"
                    }
        # Telefon numarasına göre arama
            
                if gonderino == '' :
                    return render_template("takipyok.html",veriler = "ad" , bilgiler1=Takipyok_bilgiler)
            else :
             raise ValueError("API'den veri gelmedi veya kayıt bulunamadı!")
      
  

                
            # Aras Kargo işlemleri
            url1 = f"https://kargotakip.araskargo.com.tr/mainpage.aspx?code={gonderino}"
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
                    "Aras KARGO Takip Kodu":gonderino
                }

                return render_template("result.html", bilgiler=bilgiler, son_durum=son_durum, gonderi_tip=gonderi_tip, teslimat_sube=teslimat_sube, sonuçlar=sonuçlar)

        return render_template("index.html", error_message="Takip numarası bulunamadı. Lütfen geçerli bir numara girin! ")
      
      except (IndexError, KeyError, ValueError) as e:  
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
