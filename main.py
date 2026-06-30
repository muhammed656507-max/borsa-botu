import time
import requests
import yfinance as yf
import pandas as pd
from flask import Flask
from threading import Thread

app = Flask('')

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
        response = requests.post(url, json=payload)
        # Eğer Telegram hata dönerse bunu Render loguna yazdır:
        if response.status_code != 200:
            print(f"❌ Telegram Hatası: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {str(e)}")

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
            time.sleep(2)
            df = yf.download(hisse, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True, group_by=False)
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

def tarama_tetikle():
    # Burası çok önemli: Girişte hemen bir test mesajı gönderiyoruz
    telegram_mesaj_gonder("🎯 Bot tetiklendi! Tarama fonksiyonu başarıyla başladı.")
    
    sinyal_g = sinyal_control("GÜNLÜK", "1d", "1y", 80)
    sinyal_h = sinyal_control("HAFTALIK", "1wk", "3y", 70)
    
    if not sinyal_g and not sinyal_h:
        telegram_mesaj_gonder("✅ Tarama tamamlandı. Kriterlere uyan yeni bir sinyal bulunamadı.")

@app.route('/')
def home():
    t = Thread(target=tarama_tetikle)
    t.start()
    return "OK"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
