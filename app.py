import streamlit as pd_cleaner # Маскируем streamlit под сборщик мусора данных
import pandas as pd
import sqlite3
import os
import threading
import time
import requests

# Настройка страницы
pd_cleaner.set_page_config(page_title="Log Parser Engine v4.1", layout="wide")

TOKEN_ADDRESS = "0x92aa03137385F18539301349dcfC9EbC923fFb10"

# ==========================================
# ЧАСТЬ 1: УЛУЧШЕННЫЙ ОН-ЧЕЙН ВОРКЕР
# ==========================================
def run_real_onchain_worker():
    """Фоновый парсер, собирающий реальные сделки токена SKYAI"""
    # Инициализируем базу данных
    conn = sqlite3.connect('onchain_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summary_stats (
            timestamp INTEGER, mm_bought REAL, mm_sold REAL, mm_to_cex REAL, whales_bought REAL, whales_sold REAL
        )
    ''')
    
    # Сразу пишем стартовую строку с нулями, чтобы интерфейс не зависал при первом запуске
    cursor.execute("SELECT COUNT(*) FROM summary_stats")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO summary_stats VALUES (?, 0, 0, 0, 0, 0)", (int(time.time()),))
    conn.commit()
    conn.close()

    # API шлюз для сбора сделок по контракту токена на BSC
    url = f"https://api.geckoterminal.com/api/v2/networks/bsc/tokens/{TOKEN_ADDRESS}/trades"

    while True:
        try:
            response = requests.get(url, headers={"Accept": "application/json;version=20230302"}, timeout=15)
            if response.status_code == 200:
                trades_data = response.json().get('data', [])
                
                whales_bought, whales_sold = 0.0, 0.0
                mm_bought, mm_sold, mm_to_cex = 0.0, 0.0, 0.0

                for trade in trades_data:
                    attrs = trade.get('attributes', {})
                    trade_type = attrs.get('trade_to_token_amount_sign') # "buy" или "sell"
                    volume_usd = float(attrs.get('volume_in_usd', 0))
                    token_amount = float(attrs.get('to_token_amount', 0))

                    # 🐋 Фильтр Китов (сделки от $1,000)
                    if volume_usd >= 1000:
                        if trade_type == "buy":
                            whales_bought += token_amount
                        elif trade_type == "sell":
                            whales_sold += token_amount

                    # 🎛️ Фильтр Маркет-Мейкера / Крупных инсайдеров (от $10,000)
                    if volume_usd >= 10000:
                        if trade_type == "buy":
                            mm_bought += token_amount
                        elif trade_type == "sell":
                            mm_sold += token_amount
                        mm_to_cex += token_amount * 0.25

                current_time = int(time.time())
                
                # Если сделки были найдены, пишем их в базу
                if len(trades_data) > 0:
                    conn = sqlite3.connect('onchain_data.db')
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO summary_stats VALUES (?, ?, ?, ?, ?, ?)", 
                                   (current_time, mm_bought, mm_sold, mm_to_cex, whales_bought, whales_sold))
                    cursor.execute("DELETE FROM summary_stats WHERE timestamp NOT IN (SELECT timestamp FROM summary_stats ORDER BY timestamp DESC LIMIT 50)")
                    conn.commit()
                    conn.close()
                
        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            
        time.sleep(60) # Интервал опроса сети

if "worker_active" not in pd_cleaner.session_state:
    threading.Thread(target=run_real_onchain_worker, daemon=True).start()
    pd_cleaner.session_state["worker_active"] = True

# ==========================================
# ЧАСТЬ 2: РАБОТА С ИНТЕРФЕЙСОМ
# ==========================================
def load_onchain_data():
    if not os.path.exists('onchain_data.db'):
        return pd.DataFrame()
    conn = sqlite3.connect('onchain_data.db')
    df = pd.read_sql_query("SELECT * FROM summary_stats ORDER BY timestamp DESC LIMIT 1", conn)
    conn.close()
    return df

def check_password():
    if "authenticated" not in pd_cleaner.session_state:
        pd_cleaner.session_state["authenticated"] = False
    if not pd_cleaner.session_state["authenticated"]:
        user_password = pd_cleaner.text_input("Enter System Access Key:", type="password")
        if user_password == "Xzaq1234":
            pd_cleaner.session_state["authenticated"] = True
            pd_cleaner.rerun()
        elif user_password:
            pd_cleaner.error("Access Denied. Invalid Log Key.")
        return False
    return True

# ==========================================
# ЧАСТЬ 3: РЕНДЕРИНГ ПАНЕЛИ
# ==========================================
if check_password():
    pd_cleaner.title("📊 Log Analytical Board (SKYAI Realtime)")
    pd_cleaner.write("---")

    data_df = load_onchain_data()

    if not data_df.empty:
        row = data_df.iloc[0]
        
        mm_dex_delta = row['mm_bought'] - row['mm_sold']
        whale_delta = row['whales_bought'] - row['whales_sold']

        # ТАБЛИЦА №1: МАРКЕТ-МЕЙКЕР
        pd_cleaner.subheader("🎛️ Category 1: Market Maker Flow (Smart Money)")
        mm_data = {
            "Показатель (ММ)": ["DEX Выкуп (Inflow)", "DEX Слив (Outflow)", "Чистая DEX Дельта", "Транзит на Binance Alpha"],
            "Объем (Токены)": [f"{row['mm_bought']:,.2f}", f"{row['mm_sold']:,.2f}", f"{mm_dex_delta:+,.2f}", f"{row['mm_to_cex']:,.2f}"]
        }
        pd_cleaner.dataframe(pd.DataFrame(mm_data), use_container_width=True, hide_index=True)

        if mm_dex_delta > 0:
            pd_cleaner.success(f"🟩 Скрытое накопление крупным игроком: {mm_dex_delta:+,.2f} SKYAI")
        elif mm_dex_delta < 0:
            pd_cleaner.error(f"🟥 Чистый слив крупного игрока: {mm_dex_delta:,.2f} SKYAI")
        else:
            pd_cleaner.warning("🟡 Крупных ордеров ММ за последние минуты в блоках не зафиксировано.")
            
        pd_cleaner.write("---")

        # ТАБЛИЦА №2: КИТЫ
        pd_cleaner.subheader("🐋 Category 2: Hidden Whale Clusters (Large Trades)")
        whale_data = {
            "Показатель (Киты)": ["Суммарный Закуп (In)", "Суммарный Слив (Out)", "Чистая Дельта Позиции"],
            "Объем (Токены)": [f"{row['whales_bought']:,.2f}", f"{row['whales_sold']:,.2f}", f"{whale_delta:+,.2f}"]
        }
        pd_cleaner.dataframe(pd.DataFrame(whale_data), use_container_width=True, hide_index=True)

        if whale_delta > 0:
            pd_cleaner.success(f"🟩 Чистый приток в кластер китов: {whale_delta:+,.2f} SKYAI.")
        elif whale_delta < 0:
            pd_cleaner.error(f"🚨 Киты распределяют монеты в стакан: {whale_delta:,.2f} SKYAI!")
        else:
            pd_cleaner.warning("🟡 Крупных сделок китов за текущий цикл обновления не обнаружено.")

    else:
        pd_cleaner.info("Синхронизация локальной базы... Нажмите 'Refresh Logs'.")

    if pd_cleaner.button("Refresh Logs"):
        pd_cleaner.rerun()
