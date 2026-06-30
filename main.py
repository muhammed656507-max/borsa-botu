import time
import requests
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from flask import Flask
from threading import Thread

# Flask web sunucusu (Render'ın arka planda botu kapatmasını engeller)
app = Flask('')

@app.route('/')
def home():
    return "Borsa Botu Bulutta Aktif ve Canlı Çalışıyor!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- TELEGRAM BİLGİLERİN ---
TOKEN = "8660829928:AAEYnGp90WMJk14bxe_SzSfs0-S3YhQhkJ8"
CHAT_ID = "1270038537"

# --- BIST 30 + TAKİP LİSTEN ---
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

def sinyal_kontrol(periyot_adi, yf_interval, yf_period, rsi_ust_sinir):
    for hisse in HISSELER:
        try:
            df = yf.download(hisse, period=yf_period, interval=yf_interval, progress=False, auto_adjust=True)
            if df.empty or len(df) < 65:
                continue
                
            kapanis_serisi = pd.Series(df['Close'].squeeze().dropna())
            if len(kapanis_serisi) < 65:
                continue

            rsi_serisi = ta.rsi(kapanis_serisi, length=14)
            sma20_serisi = ta.sma(kapanis_serisi, length=20)
            sma50_serisi = ta.sma(kapanis_serisi, length=50)
            
            if rsi_serisi is None or sma20_serisi is None or sma50_serisi is None or len(rsi_serisi) < 2:
                continue
                
            son_fiyat = float(kapanis_serisi.iloc[-1])
            son_rsi = float(rsi_serisi.iloc[-1])
            son_sma20 = float(sma20_serisi.iloc[-1])
            son_sma50 = float(sma50_serisi.iloc[-1])
            
            # Kriter 1: RSI 35'in altı (Alım Yakın)
            if son_rsi < 35:
                mesaj = f"🚨 [{periyot_adi} GRAFİK] RSI DÜŞÜK (ALIM YAKIN)!\nŞirket: {hisse.split('.')[0]}\nFiyat: {son_fiyat:.2f} TL\nRSI: {son_rsi:.2f}"
                telegram_mesaj_gonder(mesaj)
                
            # Kriter 2: RSI üst sınır aşımı
            if son_rsi > rsi_ust_sinir:
                mesaj = f"⚠️ [{periyot_adi} GRAFİK] RSI ÇOK YÜKSEK (RİSK)!\nŞirket: {hisse.split('.')[0]}\nFiyat: {son_fiyat:.2f} TL\nRSI: {son_rsi:.2f}"
                telegram_mesaj_gonder(mesaj)
                
            # Kriter 3: SMA20 / SMA50 Yükseliş Kesişimi
            onceki_sma20 = float(sma20_serisi.iloc[-2])
            onceki_sma50 = float(sma50_serisi.iloc[-2])
            if onceki_sma20 <= onceki_sma50 and son_sma20 > son_sma50:
                mesaj = f"🚀 [{periyot_adi} GRAFİK] TREND DÖNÜŞÜ (AL)!\nŞirket: {hisse.split('.')[0]}\nHızlı Ortalama (SMA20) Yavaş Ortalamayı (SMA50) YUKARI KIRDI!"
                telegram_mesaj_gonder(mesaj)
        except Exception:
            pass

def ana_dongu():
    # Bağlantı testi için mesajı döngünün hemen dışına, en başa alıyoruz
    telegram_mesaj_gonder("🤖 Bulut Sistemi Aktif! Bot 7/24 taramaya başladı, bilgisayarınızı kapatabilirsiniz.")
    while True:
        sinyal_kontrol("GÜNLÜK", "1d", "1y", 80)
        sinyal_kontrol("HAFTALIK", "1wk", "3y", 70)  # c harfi k olarak düzeltildi
        time.sleep(14400) # 4 saat bekler

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    ana_dongu()
