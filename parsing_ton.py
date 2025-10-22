import requests
import pandas as pd
import time
from datetime import datetime
import os

class ByBitTONCollector1s:
    def __init__(self, symbol='TONUSDT', csv_filename='bybit_tonusdt_1s.csv'):
        self.symbol = symbol
        self.csv_filename = csv_filename
        self.base_url = 'https://api.bybit.com'
        self.initialize_csv()
    
    def initialize_csv(self):
        """Создает CSV файл с заголовками"""
        if not os.path.exists(self.csv_filename):
            df = pd.DataFrame(columns=[
                'symbol', 'timestamp', 'time_utc', 'time_local', 
                'open', 'high', 'low', 'close', 'volume'
            ])
            df.to_csv(self.csv_filename, index=False)
            print(f"Создан файл для данных ByBit: {self.csv_filename}")
    
    def get_bybit_ticker_data(self):
        """Получает тикерные данные с ByBit"""
        try:
            url = f"{self.base_url}/v5/market/tickers"
            params = {
                'category': 'spot',
                'symbol': self.symbol
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['retCode'] == 0 and data['result']['list']:
                ticker = data['result']['list'][0]
                current_time = datetime.now()
                
                # БЕЗ ОКРУГЛЕНИЯ - сохраняем все цифры как есть
                record = {
                    'symbol': self.symbol,
                    'timestamp': int(current_time.timestamp() * 1000),
                    'time_utc': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'time_local': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'open': float(ticker['lastPrice']),     # БЕЗ ОКРУГЛЕНИЯ
                    'high': float(ticker['highPrice24h']),  # БЕЗ ОКРУГЛЕНИЯ
                    'low': float(ticker['lowPrice24h']),    # БЕЗ ОКРУГЛЕНИЯ
                    'close': float(ticker['lastPrice']),    # БЕЗ ОКРУГЛЕНИЯ
                    'volume': float(ticker['volume24h'])    # БЕЗ ОКРУГЛЕНИЯ
                }
                
                return record
        except Exception as e:
            print(f"Ошибка получения данных с ByBit: {e}")
        return None
    
    def save_to_csv(self, data):
        """Сохраняет данные в CSV"""
        try:
            df = pd.DataFrame([data])
            # Сохраняем без округления
            df.to_csv(self.csv_filename, mode='a', header=False, index=False, float_format='%.10f')
            return True
        except Exception as e:
            print(f"Ошибка сохранения в CSV: {e}")
            return False
    
    def run_collector_1s(self):
        """Запускает сбор данных каждую секунду"""
        print("=" * 60)
        print("СБОРЩИК ДАННЫХ BYBIT - TON/USDT")
        print("ИНТЕРВАЛ: 1 СЕКУНДА")
        print("ОКРУГЛЕНИЕ: НЕТ (все цифры полностью)")
        print("=" * 60)
        
        collection_count = 0
        start_time = time.time()
        
        while True:
            try:
                collection_count += 1
                
                # Получаем данные
                ticker_data = self.get_bybit_ticker_data()
                
                if ticker_data:
                    # Сохраняем данные
                    if self.save_to_csv(ticker_data):
                        current_time = datetime.now().strftime('%H:%M:%S')
                        print(f"#{collection_count} | {current_time} | "
                              f"Price: {ticker_data['close']} | "
                              f"Volume: {ticker_data['volume']}")
                
                # Точная пауза на 1 секунду
                elapsed = time.time() - start_time
                sleep_time = 1.0 - (elapsed % 1.0)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                print(f"\n\nОстановлено пользователем")
                print(f"Всего собрано записей: {collection_count}")
                print(f"Данные сохранены в: {self.csv_filename}")
                break
            except Exception as e:
                print(f"Ошибка: {e}")
                time.sleep(1)

# Упрощенная версия для максимальной скорости
def simple_1s_collector():
    """Простой сборщик данных каждую секунду без округления"""
    csv_file = 'tonusdt_1s_fullprecision.csv'
    
    if not os.path.exists(csv_file):
        df = pd.DataFrame(columns=['symbol', 'timestamp', 'time_utc', 'time_local', 'price', 'volume'])
        df.to_csv(csv_file, index=False)
        print("Создан новый файл для данных")
    
    print("Запуск сбора данных каждую секунду...")
    print("Режим: БЕЗ ОКРУГЛЕНИЯ")
    count = 0
    
    try:
        while True:
            count += 1
            current_time = datetime.now()
            
            # Быстрый запрос к ByBit API
            url = "https://api.bybit.com/v5/market/tickers"
            params = {'category': 'spot', 'symbol': 'TONUSDT'}
            
            response = requests.get(url, params=params, timeout=3)
            data = response.json()
            
            if data['retCode'] == 0 and data['result']['list']:
                ticker = data['result']['list'][0]
                
                # БЕЗ ОКРУГЛЕНИЯ - все цифры полностью
                record = {
                    'symbol': 'TONUSDT',
                    'timestamp': int(current_time.timestamp() * 1000),
                    'time_utc': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'time_local': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'price': float(ticker['lastPrice']),    # Все цифры полностью
                    'volume': float(ticker['volume24h'])    # Все цифры полностью
                }
                
                # Сохраняем без округления
                df = pd.DataFrame([record])
                df.to_csv(csv_file, mode='a', header=False, index=False, float_format='%.10f')
                
                print(f"#{count} | {record['time_local']} | Price: {record['price']} | Volume: {record['volume']}")
            
            # Точная задержка на 1 секунду
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print(f"\nОстановлено. Собрано записей: {count}")

# Версия с Kline данными каждую секунду
def kline_1s_collector():
    """Сбор Kline данных каждую секунду без округления"""
    csv_file = 'tonusdt_kline_1s.csv'
    
    if not os.path.exists(csv_file):
        df = pd.DataFrame(columns=['symbol', 'timestamp', 'time_utc', 'time_local', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv(csv_file, index=False)
    
    print("Сбор Kline данных каждую секунду...")
    count = 0
    
    try:
        while True:
            count += 1
            current_time = datetime.now()
            
            url = "https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': 'TONUSDT',
                'interval': '1',
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data['retCode'] == 0 and data['result']['list']:
                kline = data['result']['list'][0]
                
                # БЕЗ ОКРУГЛЕНИЯ
                record = {
                    'symbol': 'TONUSDT',
                    'timestamp': int(kline[0]),
                    'time_utc': datetime.utcfromtimestamp(int(kline[0])/1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'time_local': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    'open': float(kline[1]),    # Все цифры полностью
                    'high': float(kline[2]),    # Все цифры полностью
                    'low': float(kline[3]),     # Все цифры полностью
                    'close': float(kline[4]),   # Все цифры полностью
                    'volume': float(kline[5])   # Все цифры полностью
                }
                
                df = pd.DataFrame([record])
                df.to_csv(csv_file, mode='a', header=False, index=False, float_format='%.10f')
                
                print(f"#{count} | {record['time_local']} | Close: {record['close']} | High: {record['high']} | Low: {record['low']}")
            
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print(f"\nОстановлено. Записей: {count}")

# ЗАПУСК СКРИПТА
if __name__ == "__main__":
    print("Выберите режим сбора данных:")
    print("1 - Тикерные данные каждую секунду (рекомендуется)")
    print("2 - Kline данные каждую секунду")
    print("3 - Простая версия (только цена и объем)")
    
    choice = input("Введите номер (1-3): ").strip()
    
    if choice == "1":
        collector = ByBitTONCollector1s()
        collector.run_collector_1s()
    elif choice == "2":
        kline_1s_collector()
    else:
        simple_1s_collector()