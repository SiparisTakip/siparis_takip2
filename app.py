from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
import pandas as pd


kullanici_Adi = "seffafbutik@yesilkar.com"
sifre = "Ma123456"
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        takip = request.form.get("takip_no")
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

            takip_kodu = arama(takip)
            if not takip_kodu:
                return "Kargodan Bilgiler Geldikçe Bu Ekran'da Gösterilecektir 2 Saat Sonra Tekrar Deneyiniz"

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

                bilgiler = {
                    "Alıcı Adı": alici_adi,
                    "Çıkış Şube": cıkıs_sube,
                    "Teslimat Şube": teslimat_sube,
                    "Gönderim Tarihi": gonderim_tarihi,
                    "Kargo Son Durum": son_durum,
                    "Gönderi Tipi": gonderi_tip,
                    "Aras KARGO Takip Kodu":veriler[4]
                }

                return render_template("result.html", bilgiler=bilgiler, son_durum=son_durum, gonderi_tip=gonderi_tip)

        return render_template("index.html", error_message="Takip numarası bulunamadı. Lütfen geçerli bir numara girin! ")

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
