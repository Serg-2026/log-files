import streamlit as pd_cleaner
import pandas as pd
import requests
import time

# Настройка интерфейса
pd_cleaner.set_page_config(page_title="Log Parser Engine v4.6", layout="wide")

TOKEN_ADDRESS = "0x92aa03137385F18539301349dcfC9EbC923fFb10"

# ==========================================
# ПРЯМОЙ И СТАБИЛЬНЫЙ СБОР ДАННЫХ (БЕЗ ПОТОКОВ)
# ==========================================
def fetch_realtime_sentiment():
    """Прямой запрос к агрегатору крупных сделок без использования багующих библиотек"""
    url = f"https://api.geckoterminal.com/api/v2/networks/bsc/tokens/{TOKEN_ADDRESS}/trades"
    
    # Дефолтные значения (Баланс сил), если на рынке штиль
    metrics = {"long_per": 50.0, "short_per": 50.0, "mm_delta": 0.0, "whale_delta": 0.0}
    
    try:
        response = requests.get(url, headers={"Accept": "application/json;version=20230302"}, timeout=10)
        if response.status_code == 200:
            trades = response.json().get('data', [])
            
            whales_bought, whales_sold = 0.0, 0.0
            mm_bought, mm_sold = 0.0, 0.0

            for trade in trades:
                attrs = trade.get('attributes', {})
                trade_type = attrs.get('trade_to_token_amount_sign') # "buy" или "sell"
                volume_usd = float(attrs.get('volume_in_usd', 0))
                token_amount = float(attrs.get('to_token_amount', 0))

                # Убираем жесткие рамки: считаем ВСЕ крупные ордера в кучу, чтобы видеть микро-накопление роботами
                if volume_usd >= 300: 
                    if trade_type == "buy":
                        whales_bought += token_amount
                    elif trade_type == "sell":
                        whales_sold += token_amount

                if volume_usd >= 2000:
                    if trade_type == "buy":
                        mm_bought += token_amount
                    elif trade_type == "sell":
                        mm_sold += token_amount

            total_volume = whales_bought + whales_sold + mm_bought + mm_sold
            if total_volume > 0:
                long_p = ((whales_bought + mm_bought) / total_volume) * 100
                metrics["long_per"] = round(long_p, 1)
                metrics["short_per"] = round(100 - long_p, 1)
                metrics["mm_delta"] = round(mm_bought - mm_sold, 2)
                metrics["whale_delta"] = round(whales_bought - whales_sold, 2)
                
    except Exception as e:
        pass # Защита от падения интерфейса при ошибках сети
        
    return metrics

# ==========================================
# ЛОГИКА АВТОРИЗАЦИИ
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
# ОТРИСОВКА ИНТЕРФЕЙСА
# ==========================================
if check_password():
    pd_cleaner.title("📊 Спектр Накопления Токена: SKYAI")
    pd_cleaner.write("---")

    # Получаем данные «здесь и сейчас» напрямую при обновлении
    data = fetch_realtime_sentiment()

    # 🎯 Окошко со сентиментом Long / Short
    pd_cleaner.subheader("🔮 Рыночное позиционирование крупных кошельков (Sentiment)")
    
    col1, col2 = pd_cleaner.columns(2)
    col1.metric(label="🟢 LONG (Накопление/Закуп)", value=f"{data['long_per']}%")
    col2.metric(label="🔴 SHORT (Распределение/Слив)", value=f"{data['short_per']}%")

    # Прогресс-бар доминирования сил
    pd_cleaner.progress(int(data['long_per']))
    
    pd_cleaner.write("---")

    # Таблицы дельты объемов
    col_mm, col_wh = pd_cleaner.columns(2)

    with col_mm:
        pd_cleaner.markdown("### 🎛️ Смарт-деньги / Сверхкрупные ордера")
        pd_cleaner.write(f"Чистая дельта: **{data['mm_delta']:+,.2f} SKYAI**")
        if data['mm_delta'] > 0:
            pd_cleaner.success("Идет скрытая аккумуляция блоками.")
        elif data['mm_delta'] < 0:
            pd_cleaner.error("Крупный игрок разгружает позиции.")
        else:
            pd_cleaner.warning("Крупных блоковых ордеров в пуле за последнее время не найдено.")

    with col_wh:
        pd_cleaner.markdown("### 🐋 Активные кошельки (Ордера от $300)")
        pd_cleaner.write(f"Чистая дельта: **{data['whale_delta']:+,.2f} SKYAI**")
        if data['whale_delta'] > 0:
            pd_cleaner.success("Покупатели удерживают перевес.")
        elif data['whale_delta'] < 0:
            pd_cleaner.error("Идет каскадный слив мелких китов.")
        else:
            pd_cleaner.warning("Активности средних кошельков в текущем цикле нет.")

    if pd_cleaner.button("🔄 Обновить логи и пересчитать дельту"):
        pd_cleaner.rerun()
