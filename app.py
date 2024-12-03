from flask import Flask, request, render_template_string, jsonify
import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
import pandas as pd


kullanici_Adi = "seffafbutik@yesilkar.com"
sifre = "Ma123456"
app = Flask(__name__)

result_html =""" 
<!DOCTYPE html>
<html>
<head>
    <title>Kargo Bilgileri</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f9;
            color: #333;
        }
        h1 {
            text-align: center;
            margin: 20px 0;
            color: #2c3e50;
        }
        table {
            width: 80%;
            margin: 20px auto;
            border-collapse: collapse;
            background-color: #fff;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #2c3e50;
            color: #fff;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        .status {
            text-align: center;
            margin: 20px auto;
            font-size: 1.2em;
            font-weight: bold;
            width: 80%;
        }
        .status.green {
            color: green;
        }
        .status.blue {
            color: blue;
        }
        .status.red {
            color: red;
        }
        .status.orange {
            color: orange;
        }
    </style>
</head>
<body>
    <h1>Kargo Bilgileri</h1>

    <table>
        <thead>
            <tr>
                <th>Bilgi</th>
                <th>Değer</th>
            </tr>
        </thead>
        <tbody>
            {% for key, value in bilgiler.items() %}
            <tr>
                <td><b>{{ key }}</b></td>
                <td>{{ value }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="status 
        {% if son_durum == "TESLİM EDİLDİ" and gonderi_tip == "NORMAL" %}
        green
        {% elif son_durum == "YOLDA" %}
        blue
        {% elif gonderi_tip == "İADE" %}
        red
        {% elif son_durum == "TESLİMATTA" and gonderi_tip == "NORMAL" %}
        green
        {% else %}
        orange
        {% endif %}">
        {% if son_durum == "TESLİM EDİLDİ" and gonderi_tip == "NORMAL" %}
        Kargonuz Teslim Edildi
        {% elif son_durum == "YOLDA" %}
        Kargonuz Yolda En Kısa Sürede Size Ulaşacaktır 
        {% elif gonderi_tip == "İADE" %}
        Kargonuz İade Ediliyor
        {% elif son_durum == "TESLİMATTA" and gonderi_tip == "NORMAL" %}
        Kargonuz Dağıtımda
        {% else %}
        Kargonuz Şubede
        {% endif %}
    </div>
</body>
</html>

"""

index_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Kargo Takip</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #f4f4f9;
        }
        .container {
            text-align: center;
            background: #fff;
            padding: 20px 30px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
        }
        form {
            margin-top: 15px;
        }
        input[type="text"] {
            width: 80%;
            padding: 10px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            background-color: #2c3e50;
            color: #fff;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        button:hover {
            background-color: #34495e;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Kargo Takip Sistemi</h1>
        <h2>Telefon Numaranızı Yazın</h2>
        <form method="post">
            <input type="text" name="takip_no" placeholder="Telefon Numarası" required>
            <button type="submit">Sorgula</button>
        </form>
    {% if error_message %}
    <p style="color: red;">{{ error_message }}</p>
    {% endif %}    
    </div>

</body>
</html>
"""
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
                return "Telefon Numarası bulunamadı."

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

                return render_template_string(result_html, bilgiler=bilgiler, son_durum=son_durum, gonderi_tip=gonderi_tip)

        return render_template_string(result_html, error_message="Takip numarası bulunamadı. Lütfen geçerli bir numara girin!")

    return render_template_string(index_html)


if __name__ == "__main__":
    app.run(debug=True)
