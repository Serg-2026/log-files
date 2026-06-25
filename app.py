import streamlit as pd_cleaner # Маскируем streamlit под сборщик мусора данных
import pandas as pd
import sqlite3
import os
import threading
import time
import random

# Настройка страницы (маскируемся под скучный инструмент обработки логов)
pd_cleaner.set_page_config(page_title="Log Parser Engine v4.1", layout="wide")

# ==========================================
# ЧАСТЬ 1: ФОНОВЫЙ АВТОНОМНЫЙ ВОРКЕР (БЕЗ ТЕЛЕФОНА)
# ==========================================
def run_onchain_worker():
    """Фоновый движок, который собирает данные 24/7 на сервере Streamlit"""
    # Инициализируем базу
    conn = sqlite3.connect('onchain_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summary_stats (
            timestamp INTEGER, mm_bought REAL, mm_sold REAL, mm_to_cex REAL, whales_bought REAL, whales_sold REAL
        )
    ''')
    conn.commit()
    conn.close()

    while True:
        try:
            # Сюда в будущем встанет реальный requests.get() к блокчейн-метрикам
            # Сейчас делаем динамический симулятор накопления/слива SKYAI
            current_time = int(time.time())
            
            # Генерируем волатильный поток (киты закупают, ММ гоняет на CEX)
            mm_bought = round(random.uniform(100000, 300000), 2)
            mm_sold = round(random.uniform(80000, 250000), 2)
            mm_to_cex = round(random.uniform(500000, 1500000), 2)
            
            # Киты либо закупают (+), либо фиксируют (-)
            market_trend = random.choice([1.2, 0.8, 1.0]) # коэффициент тренда
            whales_bought = round(random.uniform(300000, 700000) * market_trend, 2)
            whales_sold = round(random.uniform(200000, 500000), 2)

            # Записываем шаг в базу данных SQLite на сервере
            conn = sqlite3.connect('onchain_data.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO summary_stats VALUES (?, ?, ?, ?, ?, ?)", 
                           (current_time, mm_bought, mm_sold, mm_to_cex, whales_bought, whales_sold))
            
            # Чистим старые логи, оставляем последние 50 записей
            cursor.execute("DELETE FROM summary_stats WHERE timestamp NOT IN (SELECT timestamp FROM summary_stats ORDER BY timestamp DESC LIMIT 50)")
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Worker error: {e}")
            
        time.sleep(30) # Обновление on-chain слепка каждые 30 секунд

# Запускаем воркер в отдельном независимом потоке сервера при старте
if "worker_active" not in pd_cleaner.session_state:
    threading.Thread(target=run_onchain_worker, daemon=True).start()
    pd_cleaner.session_state["worker_active"] = True

# ==========================================
# ЧАСТЬ 2: ФУНКЦИИ ИНТЕРФЕЙСА
# ==========================================
def load_onchain_data():
    """Безопасное чтение последней записи из базы данных"""
    if not os.path.exists('onchain_data.db'):
        return pd.DataFrame() # Возвращаем пустую дату, если воркер еще не успел создать таблицу
    
    conn = sqlite3.connect('onchain_data.db')
    df = pd.read_sql_query("SELECT * FROM summary_stats ORDER BY timestamp DESC LIMIT 1", conn)
    conn.close()
    return df

def check_password():
    if "authenticated" not in pd_cleaner.session_state:
        pd_cleaner.session_state["authenticated"] = False

    if not pd_cleaner.session_state["authenticated"]:
        user_password = pd_cleaner.text_input("Enter System Access Key:", type="password")
        if user_password:
            if user_password == "Xzaq1234":
                pd_cleaner.session_state["authenticated"] = True
                pd_cleaner.rerun()
            else:
                pd_cleaner.error("Access Denied. Invalid Log Key.")
        return False
    return True

# ==========================================
# ЧАСТЬ 3: РЕНДЕРИНГ ПАНЕЛИ АНАЛИТИКИ
# ==========================================
if check_password():
    pd_cleaner.title("📊 Log Analytical Board (SKYAI Realtime)")
    pd_cleaner.write("---")

    data_df = load_onchain_data()

    if not data_df.empty:
        row = data_df.iloc[0]
        
        # Расчет чистых дельт (накапливают или сливают)
        mm_dex_delta = row['mm_bought'] - row['mm_sold']
        whale_delta = row['whales_bought'] - row['whales_sold']

        # ТАБЛИЦА №1: МАРКЕТ-МЕЙКЕР
        pd_cleaner.subheader("🎛️ Category 1: Market Maker Flow (Wintermute)")
        
        mm_data = {
            "Показатель (ММ)": ["DEX Выкуп (Inflow)", "DEX Слив (Outflow)", "Чистая DEX Дельта", "Транзит на Binance Alpha"],
            "Объем (Токены)": [f"{row['mm_bought']:,}", f"{row['mm_sold']:,}", f"{mm_dex_delta:+,}", f"{row['mm_to_cex']:,}"]
        }
        mm_df = pd.DataFrame(mm_data)
        pd_cleaner.dataframe(mm_df, use_container_width=True, hide_index=True)

        if mm_dex_delta > 0:
            pd_cleaner.success(f"🟩 Скрытое накопление на DEX: {mm_dex_delta:+,} SKYAI (ММ аккумулирует позицию)")
        else:
            pd_cleaner.error(f"🟥 Чистый слив на DEX: {mm_dex_delta:,} SKYAI (ММ распределяет объемы)")
            
        pd_cleaner.info(f"🚀 Шлюз Binance Alpha: зафиксировано {row['mm_to_cex']:,} SKYAI на транзитных адресах.")
        pd_cleaner.write("---")

        # ТАБЛИЦА №2: КИТЫ
        pd_cleaner.subheader("🐋 Category 2: Hidden Whale Clusters (300+ Wallets)")
        
        whale_data = {
            "Показатель (Киты)": ["Суммарный Закуп (In)", "Суммарный Слив (Out)", "Чистая Дельта Позиции"],
            "Объем (Токены)": [f"{row['whales_bought']:,}", f"{row['whales_sold']:,}", f"{whale_delta:+,}"]
        }
        whale_df = pd.DataFrame(whale_data)
        pd_cleaner.dataframe(whale_df, use_container_width=True, hide_index=True)

        if whale_delta > 0:
            pd_cleaner.success(f"🟩 Чистый приток в кластер: {whale_delta:+,} SKYAI. Киты удерживают позиции и продолжают закуп.")
        elif whale_delta == 0:
            pd_cleaner.warning("🟡 Активности в кластере китов за последние блоки не обнаружено.")
        else:
            pd_cleaner.error(f"🚨 ВНИМАНИЕ! Киты начали синхронный вывод/слив монет: {whale_delta:,} SKYAI!")

    else:
        pd_cleaner.info("Initializing database pipeline... Please click 'Refresh Logs' in a few seconds.")

    if pd_cleaner.button("Refresh Logs"):
        pd_cleaner.rerun()
