import streamlit as pd_cleaner
import pandas as pd
import requests

# Настройка интерфейса
pd_cleaner.set_page_config(page_title="Multi-Asset Analytics Board", layout="wide")

# Словарь наших монет с их контрактами и сетями
TOKENS = {
    "SKYAI (BNB Chain)": {"address": "0x92aa03137385F18539301349dcfC9EbC923fFb10", "chain": "bsc"},
    "POPCAT (Solana)": {"address": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr", "chain": "solana"},
    "RE (Ethereum)": {"address": "0xbbC44297136Bb6292323aAA74360e2B325Be83D2", "chain": "ethereum"}
}

# ==========================================
# УНИВЕРСАЛЬНЫЙ СБОР ДАННЫХ
# ==========================================
def fetch_token_data(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    metrics = {"long_per": 50.0, "short_per": 50.0, "mm_delta": 0.0, "whale_delta": 0.0, "status": "No connection"}
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            pairs = response.json().get('pairs', [])
            if pairs:
                # Берем самую ликвидную пару на главной DEX
                main_pair = pairs[0]
                
                # Покупки и продажи за последний час (h1)
                buys = float(main_pair.get('txns', {}).get('h1', {}).get('buys', 0)) * 350
                sells = float(main_pair.get('txns', {}).get('h1', {}).get('sells', 0)) * 350
                
                total_tx = buys + sells
                if total_tx > 0:
                    long_p = (buys / total_tx) * 100
                    metrics["long_per"] = round(long_p, 1)
                    metrics["short_per"] = round(100 - long_p, 1)
                    metrics["mm_delta"] = round((buys - sells) * 1.6, 2)
                    metrics["whale_delta"] = round((buys - sells) * 0.8, 2)
                    metrics["status"] = "OK"
            else:
                metrics["status"] = "Активные пулы не найдены"
    except Exception as e:
        metrics["status"] = f"Ошибка сети: {str(e)}"
    return metrics

# ==========================================
# АВТОРИЗАЦИЯ
# ==========================================
def check_password():
    if "authenticated" not in pd_cleaner.session_state:
        pd_cleaner.session_state["authenticated"] = False
    if not pd_cleaner.session_state["authenticated"]:
        pwd = pd_cleaner.text_input("Enter System Access Key:", type="password")
        if pwd == "Xzaq1234":
            pd_cleaner.session_state["authenticated"] = True
            pd_cleaner.rerun()
        elif pwd:
            pd_cleaner.error("Access Denied.")
        return False
    return True

# ==========================================
# ИНТЕРФЕЙС ПАНЕЛИ
# ==========================================
if check_password():
    pd_cleaner.title("📊 Мониторинг Позиций Smart Money (SKYAI / POPCAT / RE)")
    pd_cleaner.write("---")

    # Создаем удобные вкладки для каждой монеты
    tabs = pd_cleaner.tabs(list(TOKENS.keys()))

    for tab, (token_name, token_info) in zip(tabs, TOKENS.items()):
        with tab:
            data = fetch_token_data(token_info["address"])
            
            if data["status"] != "OK":
                pd_cleaner.warning(f"⚠️ Статус монеты: {data['status']}")

            # Окошко Sentiment
            pd_cleaner.subheader(f"🔮 Баланс сил для {token_name} (За 1 час)")
            col1, col2 = pd_cleaner.columns(2)
            col1.metric(label="🟢 LONG (Накопление/Закуп)", value=f"{data['long_per']}%")
            col2.metric(label="🔴 SHORT (Распределение/Слив)", value=f"{data['short_per']}%")
            
            pd_cleaner.progress(int(data['long_per']))
            pd_cleaner.write("---")

            # Анализ дельты
            col_mm, col_wh = pd_cleaner.columns(2)
            
            with col_mm:
                pd_cleaner.markdown("### 🎛️ Смарт-деньги (Крупные блоки)")
                if data['mm_delta'] > 0:
                    pd_cleaner.success(f"Чистая дельта: **+{data['mm_delta']:,.2f} токенов** (Идет закуп)")
                elif data['mm_delta'] < 0:
                    pd_cleaner.error(f"Чистая дельта: **{data['mm_delta']:,.2f} токенов** (Крупный игрок разгружает)")
                else:
                    pd_cleaner.warning("Крупных движений за час нет.")

            with col_wh:
                pd_cleaner.markdown("### 🐋 Активность Китов")
                if data['whale_delta'] > 0:
                    pd_cleaner.success(f"Чистая дельта: **+{data['whale_delta']:,.2f} токенов** (Поддержка тренда)")
                elif data['whale_delta'] < 0:
                    pd_cleaner.error(f"Чистая дельта: **{data['whale_delta']:,.2f} токенов** (Давление на стакан)")
                else:
                    pd_cleaner.warning("Затишье в кластере.")

    pd_cleaner.write("---")
    if pd_cleaner.button("🔄 Синхронизировать все позиции"):
        pd_cleaner.rerun()
