import streamlit as pd_cleaner
import pandas as pd
import sqlite3
import requests
import os
import time

# Компактный режим
pd_cleaner.set_page_config(page_title="Autonomous Scanner v6.0", layout="wide")

TOKENS = {
    "SKYAI": "0x92aa03137385F18539301349dcfC9EbC923fFb10",
    "POPCAT": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "RE": "0x526526528F35AC738177003b8773B402B8Df8143"
}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('history_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_logs (
            timestamp INTEGER, token TEXT, m5_val TEXT, h1_val TEXT, h6_val TEXT, trend TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(token_name, m5, h1, h6, trend):
    conn = sqlite3.connect('history_data.db')
    cursor = conn.cursor()
    # Храним только последние 100 записей для каждого токена, чтобы не перегружать память
    cursor.execute("INSERT INTO token_logs VALUES (?, ?, ?, ?, ?, ?)", (int(time.time()), token_name, m5, h1, h6, trend))
    cursor.execute("""
        DELETE FROM token_logs WHERE timestamp NOT IN (
            SELECT timestamp FROM token_logs WHERE token = ? ORDER BY timestamp DESC LIMIT 100
        ) AND token = ?
    """, (token_name, token_name))
    conn.commit()
    conn.close()

def parse_and_store_all():
    for name, addr in TOKENS.items():
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
        try:
            data = requests.get(url, timeout=5).json()
            pairs = data.get('pairs', [])
            if pairs:
                p = pairs[0]
                tx = p.get('txns', {})
                
                res = {}
                for tf in ["m5", "h1", "h6"]:
                    b = float(tx.get(tf, {}).get('buys', 0))
                    s = float(tx.get(tf, {}).get('sells', 0))
                    total = b + s
                    display_tf = "5m" if tf == "m5" else tf
                    res[display_tf] = f"{int((b / total) * 100)}%" if total > 0 else "50%"
                
                b_h1 = float(tx.get('h1', {}).get('buys', 0))
                s_h1 = float(tx.get('h1', {}).get('sells', 0))
                
                if b_h1 > s_h1 * 1.2:
                    trend = "🟩 Закуп"
                elif s_h1 > b_h1 * 1.2:
                    trend = "🟥 Слив"
                else:
                    trend = "🟨 Флэт"
                
                save_to_db(name, res["5m"], res["1h"], res["6h"], trend)
        except:
            pass

# Инициализируем и делаем один прогон сбора при запуске
init_db()
if "last_sync" not in pd_cleaner.session_state or time.time() - pd_cleaner.session_state["last_sync"] > 300:
    parse_and_store_all()
    pd_cleaner.session_state["last_sync"] = time.time()

# Логика авторизации
def check_password():
    if "authenticated" not in pd_cleaner.session_state:
        pd_cleaner.session_state["authenticated"] = False
    if not pd_cleaner.session_state["authenticated"]:
        pwd = pd_cleaner.text_input("Access Key:", type="password")
        if pwd == "Xzaq1234":
            pd_cleaner.session_state["authenticated"] = True
            pd_cleaner.rerun()
        return False
    return True

if check_password():
    pd_cleaner.subheader("⚡ Автономный сканер Smart Money (Данные из базы)")
    
    if pd_cleaner.button("🔄 Синхронизировать пулы"):
        parse_and_store_all()
        pd_cleaner.rerun()

    # Чтение истории из базы данных для вывода на экран
    conn = sqlite3.connect('history_data.db')
    cursor = conn.cursor()
    
    table_rows = []
    for name in TOKENS.keys():
        cursor.execute("SELECT m5_val, h1_val, h6_val, trend FROM token_logs WHERE token = ? ORDER BY timestamp DESC LIMIT 1", (name,))
        res = cursor.fetchone()
        if res:
            table_rows.append({
                "Актив": name,
                "LONG (5 мин)": res[0],
                "LONG (1 час)": res[1],
                "LONG (6 часов)": res[2],
                "Действия ММ / Направление": res[3]
            })
    conn.close()

    if table_rows:
        df = pd.DataFrame(table_rows)
        pd_cleaner.dataframe(df, use_container_width=True, hide_index=True)
    else:
        pd_cleaner.info("База данных пуста. Нажмите кнопку синхронизации для первого наполнения.")
