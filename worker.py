import sqlite3
import time
import requests
import os

# Инициализация чистой базы на сервере
def init_db():
    conn = sqlite3.connect('onchain_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summary_stats (
            timestamp INTEGER, 
            mm_bought REAL, 
            mm_sold REAL, 
            mm_to_cex REAL, 
            whales_bought REAL, 
            whales_sold REAL
        )
    ''')
    conn.commit()
    conn.close()

def get_real_market_data():
    """
    ЗДЕСЬ БУДЕТ ТВОЙ НАСТОЯЩИЙ ОН-ЧЕЙН КЛЮЧ / ЗАПРОС
    Пример структуры получения дельты Wintermute и кластера китов
    """
    try:
        # Пример: делаем запрос к API/RPC для получения актуальных объемов за последние блоки
        # response = requests.get("ТВОЙ_API_ЭНДПОИНТ_ДЛЯ_SKYAI").json()
        
        # Заглушка под реальную логику (сюда подставим твои формулы расчета)
        mm_bought = 210000.0   # Реальный объем покупок Wintermute на DEX
        mm_sold = 95000.0     # Реальный объем продаж Wintermute на DEX
        mm_to_cex = 1200000.0 # Сколько ушло на шлюзы CEX (Binance/Bybit)
        
        whales_bought = 680000.0
        whales_sold = 120000.0
        
        return mm_bought, mm_sold, mm_to_cex, whales_bought, whales_sold
    except Exception as e:
        print(f"Ошибка сбора данных: {e}")
        return None

def main():
    init_db()
    print("Фоновый парсер SKYAI успешно запущен на сервере...")
    
    while True:
        data = get_real_market_data()
        if data:
            mm_bought, mm_sold, mm_to_cex, whales_bought, whales_sold = data
            timestamp = int(time.time())
            
            conn = sqlite3.connect('onchain_data.db')
            cursor = conn.cursor()
            
            # Пишем свежий слепок рынка
            cursor.execute("""
                INSERT INTO summary_stats VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, mm_bought, mm_sold, mm_to_cex, whales_bought, whales_sold))
            
            # Чтобы база не разрасталась, храним только последние 100 слепков
            cursor.execute("""
                DELETE FROM summary_stats WHERE timestamp NOT IN (
                    SELECT timestamp FROM summary_stats ORDER BY timestamp DESC LIMIT 100
                )
            """)
            
            conn.commit()
            conn.close()
            print(f"[{time.strftime('%X')}] Данные по SKYAI обновлены в SQLite.")
            
        time.sleep(60) # Повторяем цикл раз в минуту (можно настроить чаще/реже)

if __name__ == "__main__":
    main()
