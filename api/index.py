from flask import Flask, request, render_template, jsonify
import requests
from bs4 import BeautifulSoup as BS
from datetime import datetime, timedelta
import re
import os
import logging

# Supabase import - versiyon kontrolü ile
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error("Supabase import hatası!")

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (Vercel'de tanımlayın)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ezyhoocwfrocaqsehler.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6eWhvb2N3ZnJvY2Fxc2VobGVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjcyOTkzOTUsImV4cCI6MjA0Mjg3NTM5NX0.3A2pCuleW0RnGIlCaM5pALWw8fB_KW_y2-qsIJ1_FJI")
SUPABASE_DB = "siparislistesi"

# API ayarları
CARGO_API_URL = "http://webpostman.yesilkarkargo.com:9999/restapi/client/cargo"
CARGO_API_KEY = "jE6csb3PTtLYAdya87Bnp91G0NJfMSCXUZxmHz4r"
CARGO_USER_EMAIL = "seffafbutik@yesilkar.com"

# Global Supabase client (ÇOOOK ÖNEMLİ!)
_supabase_client = None

def get_supabase():
    """Singleton pattern ile Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        try:
            # Minimal config ile client oluştur
            _supabase_client = create_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY
            )
            logger.info("Supabase client oluşturuldu")
        except Exception as e:
            logger.error(f"Supabase client hatası: {e}")
            raise
    return _supabase_client

app = Flask(__name__, template_folder="../templates")

def duzenle_telefon_numarasi(takip: str) -> str:
    """Telefon numarasını düzenle"""
    takip = takip.replace(" ", "").strip()
    if not takip.startswith("0"):
        takip = "0" + takip
    return takip

def cargo_api_sorgula(takip: str, timeout: int = 5):
    """Kargo API sorgulama - timeout ile"""
    try:
        headers = {
            "Authorization": CARGO_API_KEY,
            "From": CARGO_USER_EMAIL
        }
        params = {"sipno": takip}
        
        response = requests.get(
            CARGO_API_URL, 
            headers=headers, 
            params=params,
            timeout=timeout  # Timeout ekledik!
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"API timeout: {takip}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API hatası: {e}")
        return None

def aras_kargo_sorgula(gonderino: str, timeout: int = 5):
    """Aras Kargo scraping - timeout ile"""
    try:
        url1 = f"https://kargotakip.araskargo.com.tr/mainpage.aspx?code={gonderino}"
        response = requests.get(url1, timeout=timeout)
        soup = BS(response.content, "html5lib")

        link_veri = soup.findAll("a")
        link_cargo = None
        link_cikti = None

        for a_tag in link_veri:
            href_attribute = a_tag.get('href', '')
            if "CargoInfoWaybillAndDelivered.aspx" in href_attribute:
                link_cargo = f"https://kargotakip.araskargo.com.tr/{href_attribute}"
            if "CargoInfoTransactionAndRedirection.aspx" in href_attribute:
                link_cikti = f"https://kargotakip.araskargo.com.tr/{href_attribute}"

        if not link_cargo:
            return None

        # Cargo bilgileri
        cargo_response = requests.get(link_cargo, timeout=timeout)
        soup = BS(cargo_response.text, "html5lib")

        bilgiler = {
            "Alıcı Adı": soup.find("span", {"id": "alici_adi_soyadi"}).text if soup.find("span", {"id": "alici_adi_soyadi"}) else "N/A",
            "Teslimat Şube": soup.find("span", {"id": "varis_subesi"}).text if soup.find("span", {"id": "varis_subesi"}) else "N/A",
            "Gönderim Tarihi": soup.find("span", {"id": "cikis_tarihi"}).text if soup.find("span", {"id": "cikis_tarihi"}) else "N/A",
            "Kargo Son Durum": soup.find("span", {"id": "Son_Durum"}).text if soup.find("span", {"id": "Son_Durum"}) else "N/A",
            "Gönderi Tipi": soup.find("span", {"id": "LabelGonTipi"}).text if soup.find("span", {"id": "LabelGonTipi"}) else "N/A",
            "Aras KARGO Takip Kodu": gonderino
        }

        # Hareket bilgileri
        sonuçlar = []
        if link_cikti:
            response = requests.get(link_cikti, timeout=timeout)
            soup = BS(response.text, "html5lib")
            tablo = soup.find("table")
            
            if tablo:
                rows = tablo.findAll("tr")[0:2]
                for td in rows:
                    metin = td.text
                    pattern = r"(\d{1,2}\.\d{1,2}\.\d{4} \d{2}:\d{2}:\d{2})([A-ZŞĞİÜÖÇ]+)([A-ZŞĞİÜÖÇ ]+)"
                    matches = re.findall(pattern, metin)

                    for match in matches:
                        tarih_saat, il, birim_islem = match
                        sonuçlar.append({
                            "Tarih/Saat": tarih_saat,
                            "İl": il,
                            "Birim/İşlem": birim_islem.strip()
                        })

        return {
            "bilgiler": bilgiler,
            "sonuçlar": sonuçlar,
            "son_durum": bilgiler["Kargo Son Durum"],
            "gonderi_tip": bilgiler["Gönderi Tipi"],
            "teslimat_sube": bilgiler["Teslimat Şube"]
        }

    except requests.exceptions.Timeout:
        logger.error(f"Aras Kargo timeout: {gonderino}")
        return None
    except Exception as e:
        logger.error(f"Aras Kargo hatası: {e}")
        return None

def supabase_sorgula(takip: str):
    """Supabase'den veri çek - PANDAS KULLANMA!"""
    try:
        supabase = get_supabase()
        response = supabase.table(SUPABASE_DB).select("*").eq("TELEFON", takip).execute()
        
        if response.data and len(response.data) > 0:
            data = response.data[0]  # İlk kayıt
            return {
                "Alıcı Adı": data.get("İSİM SOYİSİM", "N/A"),
                "Adres": data.get("ADRES", "N/A"),
                "İl - İlçe": f"{data.get('İL', '')} {data.get('İLÇE', '')}",
                "Telefon": data.get("TELEFON", "N/A")
            }
        return None
    except Exception as e:
        logger.error(f"Supabase hatası: {e}")
        return None

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

@app.route("/warmup")
def warmup():
    """Warmup endpoint - cold start'ı önlemek için"""
    try:
        supabase = get_supabase()
        # Basit bir sorgu
        supabase.table(SUPABASE_DB).select("TELEFON").limit(1).execute()
        return jsonify({"status": "warm"}), 200
    except Exception as e:
        logger.error(f"Warmup hatası: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            takip = request.form.get("takip_no", "").strip()
            
            if not takip:
                return render_template("index.html", error_message="Lütfen bir takip numarası girin!")

            takip = duzenle_telefon_numarasi(takip)
            logger.info(f"Takip sorgusu: {takip}")

            # 1. Telefon numarası ise (11 haneli)
            if len(takip) == 11:
                # Cargo API sorgula
                json_data = cargo_api_sorgula(takip)

                if json_data and "data" in json_data and len(json_data["data"]) > 0:
                    cargo_data = json_data["data"][0]
                    gonderino = cargo_data.get("cikisno", "")
                    
                    # Gönderino yoksa
                    if not gonderino:
                        bilgiler = {
                            "Alıcı Adı": f"{cargo_data.get('aliciadi', '')} {cargo_data.get('alicisoyad', '')}",
                            "Teslimat Şube": "ARAS KARGO",
                            "Kargo Son Durum": "PAKET YAPILDI",
                            "İL-İLÇE": f"{cargo_data.get('sehiradi', '')} {cargo_data.get('ilce', '')}",
                            "Ücret": f"{cargo_data.get('tutar', '0')} TL"
                        }
                        return render_template("takipyok.html", veriler="ad", bilgiler1=bilgiler)
                    
                    # Aras Kargo sorgula
                    aras_data = aras_kargo_sorgula(gonderino)
                    
                    if aras_data:
                        return render_template(
                            "result.html",
                            bilgiler=aras_data["bilgiler"],
                            son_durum=aras_data["son_durum"],
                            gonderi_tip=aras_data["gonderi_tip"],
                            teslimat_sube=aras_data["teslimat_sube"],
                            sonuçlar=aras_data["sonuçlar"]
                        )

            # 2. Supabase'den sorgula
            supabase_data = supabase_sorgula(takip)
            
            if supabase_data:
                return render_template("result.html", bilgiler=supabase_data, supabase_takip="supabase")

            # 3. Hiçbir yerde bulunamadı
            return render_template("index.html", error_message="Takip numarası bulunamadı. Lütfen geçerli bir numara girin!")

        except Exception as e:
            logger.error(f"Genel hata: {e}")
            return render_template("index.html", error_message="Bir hata oluştu. Lütfen tekrar deneyin!")

    # GET request
    return render_template("index.html")

# Vercel için handler
if __name__ == "__main__":
    app.run(debug=False)
