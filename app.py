import streamlit as pd_cleaner # Маскируем streamlit под сборщик мусора данных
import pandas as pd
import sqlite3
import os

# Настройка страницы (маскируемся под скучный инструмент обработки логов)
pd_cleaner.set_page_config(page_title="Log Parser Engine v4.1", layout="wide")

# Простая, но надежная авторизация
def check_password():
    if "authenticated" not in pd_cleaner.session_state:
        pd_cleaner.session_state["authenticated"] = False

    if not pd_cleaner.session_state["authenticated"]:
        # Скучное поле ввода без лишнего пафоса
        user_password = pd_cleaner.text_input("Enter System Access Key:", type="password")
        if user_password:
            # Сюда вы потом вставите свой секретный пароль (пока для теста оставим 'my_secret_key_2026')
            if user_password == "Xzaq1234":
                pd_cleaner.session_state["authenticated"] = True
                pd_cleaner.rerun()
            else:
                pd_cleaner.error("Access Denied. Invalid Log Key.")
        return False
    return True

if check_password():
    pd_cleaner.title("📊 Log Analytical Board (SKYAI Realtime)")
    pd_cleaner.write("---")

    # Функция чтения данных из нашей live-базы SQLite
    def load_onchain_data():
        if not os.path.exists('onchain_data.db'):
            # Если базы еще нет, создаем временную заглушку для теста интерфейса
            conn = sqlite3.connect('onchain_data.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summary_stats (
                    timestamp INTEGER, mm_bought REAL, mm_sold REAL, mm_to_cex REAL, whales_bought REAL, whales_sold REAL
                )
            ''')
            # Тестовая строка: ММ накопил на DEX 45k монет и завел 1.06M на Binance Alpha
            cursor.execute("INSERT INTO summary_stats VALUES (1780000000, 150000.0, 105000.0, 1061000.0, 450000.0, 0.0)")
            conn.commit()
            conn.close()

        conn = sqlite3.connect('onchain_data.db')
        df = pd.read_sql_query("SELECT * FROM summary_stats ORDER BY timestamp DESC LIMIT 1", conn)
        conn.close()
        return df

    # Загружаем последнюю live-строку из базы
    data_df = load_onchain_data()

    if not data_df.empty:
        row = data_df.iloc[0]
        
        # РАСЧЕТ ДЕЛЬТЫ (Чистая математика, которую мы обсуждали)
        mm_dex_delta = row['mm_bought'] - row['mm_sold']
        whale_delta = row['whales_bought'] - row['whales_sold']

        # ТАБЛИЦА №1: МАРКЕТ-МЕЙКЕР (Wintermute & Binance Alpha Шлюзы)
        pd_cleaner.subheader("🎛️ Category 1: Market Maker Flow (Wintermute)")
        
        mm_data = {
            "Показатель (ММ)": ["DEX Выкуп (Inflow)", "DEX Слив (Outflow)", "Чистая DEX Дельта", "Транзит на Binance Alpha"],
            "Объем (Токены)": [f"{row['mm_bought']:,}", f"{row['mm_sold']:,}", f"{mm_dex_delta:,}", f"{row['mm_to_cex']:,}"]
        }
        mm_df = pd.DataFrame(mm_data)
        pd_cleaner.dataframe(mm_df, use_container_width=True, hide_index=True)

        # Выводим быструю индикацию состояния ММ
        if mm_dex_delta > 0:
            pd_cleaner.success(f"🟩 Скрытое накопление на DEX: +{mm_dex_delta:,} SKYAI (ММ покупает больше, чем продает)")
        else:
            pd_cleaner.error(f"🟥 Чистый слив на DEX: {mm_dex_delta:,} SKYAI")
            
        pd_cleaner.info(f"🚀 Шлюз Binance Alpha: зафиксировано {row['mm_to_cex']:,} SKYAI на транзитных адресах.")

        pd_cleaner.write("---")

        # ТАБЛИЦА №2: СКРЫТЫЙ КЛАСТЕР КИТОВ (Ваши 300+ адресов)
        pd_cleaner.subheader("🐋 Category 2: Hidden Whale Clusters (300+ Wallets)")
        
        whale_data = {
            "Показатель (Киты)": ["Суммарный Закуп (In)", "Суммарный Слив (Out)", "Чистая Дельта Позиции"],
            "Объем (Токены)": [f"{row['whales_bought']:,}", f"{row['whales_sold']:,}", f"{whale_delta:,}"]
        }
        whale_df = pd.DataFrame(whale_data)
        pd_cleaner.dataframe(whale_df, use_container_width=True, hide_index=True)

        if whale_delta > 0:
            pd_cleaner.success("🟩 Кластер китов держит позиции и продолжает скрытый закуп.")
        elif whale_delta == 0:
            pd_cleaner.warning("🟡 Активности в кластере китов за последние блоки не обнаружено.")
        else:
            pd_cleaner.error("🚨 ВНИМАНИЕ! Киты начали синхронный вывод/слив монет!")

    else:
        pd_cleaner.info("Waiting for database pipeline updates...")

    # Маленькая неприметная кнопка ручного обновления данных
    if pd_cleaner.button("Refresh Logs"):
        pd_cleaner.rerun()
