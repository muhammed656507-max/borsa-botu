import time
import requests
import yfinance as yf
import pandas as pd
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz  # Türkiye saat dilimi için

app = Flask('')

@app.route('/')
def home():
    return "Borsa Botu Bulutta Aktif!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

TOKEN = "8660829928:AAEYnGp90WMJk14bxe_SzSfs0-S3YhQhkJ8"
CHAT_ID = "1270038537"

HISSELER = [
    "AKBNK.IS", "ALARK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", 
    "BIMAS.IS", "BRSAN.IS", "EKGYO.IS", "ENKAI.IS", "EREGL.IS", 
    "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", 
    "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", 
    "ODAS.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", 
    "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS", 
    "TUPRS.IS", "YKBNK.IS", "YESIL.IS", "SDTTR.IS"
]

def telegram_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mesaj}
    try:
        requests.post(url, json=payload)
    except Exception:
        pass

def indikatör_hesapla(kapanislar):
    delta = kapanislar.diff()
    kazanc = delta.clip(lower=0)
    kayip = -delta.clip(upper=0)
    ema_kazanc = kazanc.ewm(com=13, adjust=False).mean()
    ema_kayip = kayip.ewm(com=13, adjust=False).mean()
    rs = ema_kazanc / (ema_kayip + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    sma20 = kapanislar.rolling(window=20).mean()
    sma50 = kapanislar.rolling(window=50).mean()
    return rsi, sma20, sma50

def sinyal_control(periyot_adi, yf_interval, yf_period, rsi_ust_sinir):
    sinyal_bulundu = False
    for hisse in HISSELER:
        try:
            df = yf.download(hisse, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            if df.empty or len(df) < 65:
                continue
            kapanis_serisi = pd.Series(df['Close'].squeeze().dropna())
            if len(kapanis_serisi) < 65:
                continue

            rsi_serisi, sma20_serisi, sma50_serisi = indikatör_hesapla(kapanis_serisi)
            son_fiyat = float(kapanis_serisi.iloc[-1])
            son_rsi = float(rsi_serisi.iloc[-1])
            son_sma20 = float(sma20_serisi.iloc[-1])
            son_sma50 = float(sma50_serisi.iloc[-1])
            
            if son_rsi < 35:
                telegram_mesaj_gonder(f"🚨 [{periyot_adi}] RSI DÜŞÜK!\nŞirket: {hisse.split('.')[0]}\nFiyat: {son_fiyat:.2f} TL\nRSI: {son_rsi:.2f}")
                sinyal_bulundu = True
            if son_rsi > rsi_ust_sinir:
                telegram_mesaj_gonder(f"⚠️ [{periyot_adi}] RSI YÜKSEK!\nŞirket: {hisse.split('.')[0]}\nFiyat: {son_fiyat:.2f} TL\nRSI: {son_rsi:.2f}")
                sinyal_bulundu = True
            onceki_sma20 = float(sma20_serisi.iloc[-2])
            onceki_sma50 = float(sma50_serisi.iloc[-2])
            if onceki_sma20 <= onceki_sma50 and son_sma20 > son_sma50:
                telegram_mesaj_gonder(f"🚀 [{periyot_adi}] TREND DÖNÜŞÜ (AL)!\nŞirket: {hisse.split('.')[0]}\nSMA20, SMA50'yi yukarı kırdı!")
                sinyal_bulundu = True
        except Exception:
            pass
    return sinyal_bulundu

def ana_dongu():
    # Bot ilk açıldığında anında onay mesajı fırlatır
    telegram_mesaj_gonder("🤖 Bulut Sistemi Güncellendi!\nBotunuz aktifleşti. Her gün saat 10:30, 13:30, 16:30 ve 19:30 saatlerinde otomatik tarama yapacaktır.")
    
    # 3 saatlik periyot takvimi
    HEDEF_SAATLER = ["10:30", "13:30", "16:30", "19:30"]
    son_calisilan_saat = ""

    tz = pytz.timezone('Europe/Istanbul')

    while True:
        simdi = datetime.now(tz)
        su_an_saat_dakika = simdi.strftime("%H:%M")

        if su_an_saat_dakika in HEDEF_SAATLER and su_an_saat_dakika != son_calisilan_saat:
            telegram_mesaj_gonder(f"🔄 Saat {su_an_saat_dakika} periyodik taraması başladı...")
            
            sinyal_g = sinyal_control("GÜNLÜK", "1d", "1y", 80)
            sinyal_h = sinyal_control("HAFTALIK", "1wk", "3y", 70)
            
            if not sinyal_g and not sinyal_h:
                telegram_mesaj_gonder(f"✅ Saat {su_an_saat_dakika} taraması tamamlandı. Kriterlere uyan yeni bir sinyal bulunamadı.")
                
            son_calisilan_saat = su_an_saat_dakika
            
        time.sleep(30) # Saati yakalamak için 30 saniyede bir kontrol eder

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    ana_dongu()
