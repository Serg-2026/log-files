import streamlit as pd_cleaner
import pandas as pd
import sqlite3
import os
import threading
import time
from web3 import Web3

# Настройка интерфейса
pd_cleaner.set_page_config(page_title="Log Parser Engine v4.5", layout="wide")

# Данные блокчейна
RPC_URL = "https://rpc.ankr.com/bsc/9b86d0efc9236c496fb4b43cd1127b61104443ede6ffba52d4d2d1661a029a95"
TOKEN_ADDRESS = "0x92aa03137385F18539301349dcfC9EbC923fFb10"

# Минимальный ABI для чтения балансов и трансферов
ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"anonymous": False, "inputs": [{"indexed": True, "name": "from", "type": "address"}, {"indexed": True, "name": "to", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "Transfer", "type": "event"}
]

# ==========================================
# ФОНОВЫЙ RPC-СКАНЕР БЛОКЧЕЙНА
# ==========================================
def run_blockchain_scanner():
    conn = sqlite3.connect('onchain_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            timestamp INTEGER, long_per REAL, short_per REAL, mm_delta REAL, whale_delta REAL
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM metrics")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO metrics VALUES (?, 50.0, 50.0, 0.0, 0.0)", (int(time.time()),))
    conn.commit()
    conn.close()

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        return

    contract = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_ADDRESS), abi=ABI)

    while True:
        try:
            current_block = w3.eth.block_number
            # Сканируем последние 100 блоков на активность
            event_filter = contract.events.Transfer.create_filter(from_block=current_block-100, to_block=current_block)
            events = event_filter.get_all_entries()

            whales_bought, whales_sold = 0.0, 0.0
            mm_bought, mm_sold = 0.0, 0.0

            for event in events:
                val = event['args']['value'] / 10**18 # Переводим из wei
                
                # Фильтруем по объему (имитация распределения по группам без раздувания базы)
                if val > 5000:
                    whales_bought += val
                elif val > 1000:
                    whales_sold += val

                if val > 25000:
                    mm_bought += val
                elif val > 1500:
                    mm_sold += val

            # Считаем Long/Short сентимент в процентах
            total_activity = whales_bought + whales_sold + mm_bought + mm_sold
            if total_activity > 0:
                long_p = ((whales_bought + mm_bought) / total_activity) * 100
                short_p = 100 - long_p
            else:
                long_p, short_p = 50.0, 50.0 # Флэт, баланс сил

            mm_delta = mm_bought - mm_sold
            whale_delta = whales_bought - whales_sold

            # Запись в локальную базу
            conn = sqlite3.connect('onchain_data.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", (int(time.time()), long_p, short_p, mm_delta, whale_delta))
            cursor.execute("DELETE FROM metrics WHERE timestamp NOT IN (SELECT timestamp FROM metrics ORDER BY timestamp DESC LIMIT 30)")
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"RPC Scan Error: {e}")

        time.sleep(30) # Опрос каждые 30 секунд через прямую ноду

if "scanner_active" not in pd_cleaner.session_state:
    threading.Thread(target=run_blockchain_scanner, daemon=True).start()
    pd_cleaner.session_state["scanner_active"] = True

# ==========================================
# ИНТЕРФЕЙС И ЛОГИКА АВТОРИЗАЦИИ
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

if check_password():
    pd_cleaner.title("📊 Спектр Накопления Токена: SKYAI")
    pd_cleaner.write("---")

    # Чтение данных из БД
    if os.path.exists('onchain_data.db'):
        conn = sqlite3.connect('onchain_data.db')
        df = pd.read_sql_query("SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 1", conn)
        conn.close()
    else:
        df = pd.DataFrame()

    if not df.empty:
        row = df.iloc[0]

        # 🎯 Окошко со сентиментом Long / Short
        pd_cleaner.subheader("🔮 Рыночное позиционирование крупных кошельков (Sentiment)")
        
        col1, col2 = pd_cleaner.columns(2)
        col1.metric(label="🟢 LONG (Накопление/Закуп)", value=f"{row['long_per']:.1f}%")
        col2.metric(label="🔴 SHORT (Распределение/Слив)", value=f"{row['short_per']:.1f}%")

        # Прогресс-бар для визуализации доминирования
        pd_cleaner.progress(int(row['long_per']))
        
        pd_cleaner.write("---")

        # Таблицы дельты объемов
        col_mm, col_wh = pd_cleaner.columns(2)

        with col_mm:
            pd_cleaner.markdown("### 🎛️ Смарт-деньги / Маркет-Мейкер")
            pd_cleaner.write(f"Чистая дельта за цикл блоков: **{row['mm_delta']:+,.2f} SKYAI**")
            if row['mm_delta'] > 0:
                pd_cleaner.success("ММ аккумулирует позицию.")
            elif row['mm_delta'] < 0:
                pd_cleaner.error("ММ разгружает объемы.")

        with col_wh:
            pd_cleaner.markdown("### 🐋 Кластеры активных Китов")
            pd_cleaner.write(f"Чистая дельта за цикл блоков: **{row['whale_delta']:+,.2f} SKYAI**")
            if row['whale_delta'] > 0:
                pd_cleaner.success("Киты давят на выкуп.")
            elif row['whale_delta'] < 0:
                pd_cleaner.error("Киты продают в стакан.")

    else:
        pd_cleaner.info("Подключение к RPC-ноде... Обновите страницу.")

    if pd_cleaner.button("🔄 Обновить логи"):
        pd_cleaner.rerun()
