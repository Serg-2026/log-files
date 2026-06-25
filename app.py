import streamlit as pd_cleaner
import pandas as pd
import requests

# Компактный режим во весь экран
pd_cleaner.set_page_config(page_title="Core Scanner", layout="wide")

TOKENS = {
    "SKYAI": "0x92aa03137385F18539301349dcfC9EbC923fFb10",
    "POPCAT": "7gc14MGBwX89LSv9WuWw5fWRLDZFC8C2u167meQHpump",
    "RE": "0xbbC44297136Bb6292323aAA74360e2B325Be83D2"
}

def get_signal(token_addr):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
    res = {"5m": "0%", "1h": "0%", "6h": "0%", "MM_Trend": "⚠️ Нейтрально", "Action": "Наблюдение"}
    try:
        data = requests.get(url, timeout=8).json()
        pairs = data.get('pairs', [])
        if pairs:
            p = pairs[0]
            tx = p.get('txns', {})
            
            # Расчет сентимента для разных таймфреймов
            for tf in ["m5", "h1", "h6"]:
                b = float(tx.get(tf, {}).get('buys', 0))
                s = float(tx.get(tf, {}).get('sells', 0))
                total = b + s
                display_tf = "5m" if tf == "m5" else tf
                if total > 0:
                    res[display_tf] = f"{int((b / total) * 100)}%"
            
            # Определение чистого направления Смарт-мани за 1 час
            b_h1 = float(tx.get('h1', {}).get('buys', 0))
            s_h1 = float(tx.get('h1', {}).get('sells', 0))
            
            if b_h1 > s_h1 * 1.2:
                res["MM_Trend"] = "🟩 Ликвидация продаж (Закуп)"
                res["Action"] = "🔥 НАКОПЛЕНИЕ КИТАМИ"
            elif s_h1 > b_h1 * 1.2:
                res["MM_Trend"] = "🟥 Дистрибуция (Слив)"
                res["Action"] = "🚨 Выход крупняка"
            else:
                res["MM_Trend"] = "🟨 Флэт / Удержание"
                res["Action"] = "Удержание зоны"
    except:
        pass
    return res

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
    # Кнопка обновления в самом верху, компактная
    if pd_cleaner.button("🔄 Синхронизировать"):
        pd_cleaner.rerun()

    # Сбор данных по всем активам в один клик
    table_rows = []
    for name, addr in TOKENS.items():
        metrics = get_signal(addr)
        table_rows.append({
            "Актив": name,
            "LONG (5 мин)": metrics["5m"],
            "LONG (1 час)": metrics["1h"],
            "LONG (6 часов)": metrics["6h"],
            "Действия ММ (1ч)": metrics["MM_Trend"],
            "СТАТУС СИГНАЛА": metrics["Action"]
        })

    # Отрисовка одной плотной таблицы без прокрутки
    df = pd.DataFrame(table_rows)
    pd_cleaner.subheader("⚡ Живой тренд Smart Money по открытым позициям")
    pd_cleaner.dataframe(df, use_container_width=True, hide_index=True)
