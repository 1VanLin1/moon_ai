# download_bybit_data_SAFE.py
import requests
import pandas as pd
from datetime import datetime
import time
import signal
import sys
import os

SYMBOL = "TONUSDT"
INTERVAL = "1"  # 1 минута
# INTERVAL = "1"  # 1 час
INTERVAL_SECONDS = int(INTERVAL) * 60   # Для правильной проверки целостности
START_DATE = "2023-01-23"
END_DATE = "2025-10-23"
LIMIT = 200

# Глобальные переменные для сохранения состояния
all_klines = []
seen_timestamps = set()
request_count = 0
current_start = 0
filename = ""

def save_progress():
    """Сохраняет текущий прогресс в CSV файл"""
    global all_klines, current_start, request_count, filename
    
    if not all_klines:
        print("ℹ️ Нет данных для сохранения")
        return
    
    try:
        df = pd.DataFrame(all_klines)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        df = df[~df.index.duplicated(keep='first')]  # Финальная очистка от дублей

        # Проверка целостности
        total_expected = 0
        total_actual = len(df)
        gaps = 0
        if len(df) > 1:
            total_expected = int((df.index[-1] - df.index[0]).total_seconds() / INTERVAL_SECONDS) + 1
            gaps = total_expected - total_actual

        # Определяем имя файла
        if not filename:
            filename = f"data/bybit_{SYMBOL.lower()}_{INTERVAL}_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}_PARTIAL.csv"

        # Создаем папку data если её нет
        os.makedirs('data', exist_ok=True)
        
        df.to_csv(filename)
        
        print(f"\n💾 ПРОГРЕСС СОХРАНЕН: {total_actual} свечей в {filename}")
        if len(df) > 1:
            print(f"📅 Диапазон: {df.index[0]} — {df.index[-1]}")
            print(f"📊 Ожидалось: {total_expected} минут")
            print(f"📉 Пропущено: {gaps} минут ({gaps/total_expected:.2%})")
        
        # Сохраняем также точку возобновления
        resume_info = {
            'last_timestamp': current_start,
            'total_records': len(all_klines),
            'last_request': request_count
        }
        resume_file = filename.replace('.csv', '_resume.json')
        pd.Series(resume_info).to_json(resume_file)
        print(f"📋 Точка возобновления сохранена: {resume_file}")
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении прогресса: {e}")

def signal_handler(sig, frame):
    """Обработчик сигнала прерывания (Ctrl+C)"""
    print(f"\n\n🛑 Получен сигнал прерывания...")
    print("💾 Сохраняем прогресс перед выходом...")
    save_progress()
    print("👋 Выход из программы")
    sys.exit(0)

def load_resume_info():
    """Загружает информацию для возобновления работы"""
    global all_klines, seen_timestamps, request_count, current_start
    
    resume_file = f"data/bybit_{SYMBOL.lower()}_{INTERVAL}_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}_PARTIAL_resume.json"
    if os.path.exists(resume_file):
        try:
            resume_data = pd.read_json(resume_file, typ='series')
            print(f"🔄 Найдена точка возобновления: {resume_file}")
            print(f"   Последний timestamp: {resume_data['last_timestamp']}")
            print(f"   Всего записей: {resume_data['total_records']}")
            print(f"   Запросов сделано: {resume_data['last_request']}")
            
            choice = input("   Продолжить с этой точки? (y/n): ").strip().lower()
            if choice == 'y':
                # Загружаем существующие данные если есть
                existing_file = f"data/bybit_{SYMBOL.lower()}_{INTERVAL}_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}_PARTIAL.csv"
                if os.path.exists(existing_file):
                    try:
                        existing_df = pd.read_csv(existing_file, index_col='timestamp', parse_dates=True)
                        for idx, row in existing_df.iterrows():
                            ts = int(idx.timestamp() * 1000)
                            all_klines.append({
                                "timestamp": ts,
                                "open": row['open'],
                                "high": row['high'],
                                "low": row['low'],
                                "close": row['close'],
                                "volume": row['volume'],
                            })
                            seen_timestamps.add(ts)
                        request_count = resume_data['last_request']
                        current_start = resume_data['last_timestamp']
                        print(f"📂 Загружено {len(all_klines)} существующих записей")
                        return current_start, len(all_klines), request_count
                    except Exception as e:
                        print(f"⚠️ Ошибка загрузки существующих данных: {e}")
                else:
                    current_start = resume_data['last_timestamp']
                    request_count = resume_data['last_request']
                    return current_start, resume_data['total_records'], request_count
        except Exception as e:
            print(f"⚠️ Ошибка загрузки точки возобновления: {e}")
    
    return None, 0, 0

def date_to_timestamp(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp() * 1000)

def make_api_request(url, params, max_retries=3):
    """Безопасный запрос к API с повторными попытками"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            
            # Проверяем статус код
            if response.status_code != 200:
                print(f"❌ HTTP ошибка {response.status_code}: {response.text[:100]}")
                time.sleep(2)
                continue
                
            # Проверяем что ответ не пустой
            if not response.text.strip():
                print(f"❌ Пустой ответ от сервера")
                time.sleep(2)
                continue
                
            # Пытаемся распарсить JSON
            try:
                data = response.json()
                return data
            except ValueError as e:
                print(f"❌ Ошибка парсинга JSON (попытка {attempt + 1}/{max_retries}): {e}")
                print(f"📄 Ответ сервера: {response.text[:200]}...")
                time.sleep(2)
                continue
                
        except requests.exceptions.Timeout:
            print(f"⏰ Таймаут запроса (попытка {attempt + 1}/{max_retries})")
            time.sleep(3)
        except requests.exceptions.ConnectionError:
            print(f"🔌 Ошибка подключения (попытка {attempt + 1}/{max_retries})")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Неожиданная ошибка запроса (попытка {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)
    
    return None

def main():
    global all_klines, seen_timestamps, request_count, current_start, filename
    
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)

    start_ts = date_to_timestamp(START_DATE)
    end_ts = date_to_timestamp(END_DATE)

    print(f"📥 Загрузка {INTERVAL}-минутных свечей {SYMBOL} с {START_DATE} по {END_DATE}...")
    print(f"⏱️ Целевой диапазон: {start_ts} — {end_ts} (мс)")

    # Пытаемся загрузить точку возобновления
    resume_ts, resume_records, resume_requests = load_resume_info()
    if resume_ts:
        current_start = resume_ts
        print(f"🔄 Продолжаем с timestamp: {current_start}")
    else:
        current_start = start_ts
        print("🆕 Начинаем новую загрузку")

    base_url = "https://api.bybit.com"
    endpoint = "/v5/market/kline"

    MAX_REQUESTS = 10000  # 🛡️ Жёсткий лимит запросов, чтобы не уйти в бесконечность

    # Автосохранение каждые N запросов
    AUTOSAVE_INTERVAL = 50
    last_save_count = 0

    try:
        while current_start < end_ts and request_count < MAX_REQUESTS:
            params = {
                "category": "linear",
                "symbol": SYMBOL,
                "interval": INTERVAL,
                "start": current_start,
                "limit": LIMIT,
            }

            # Используем безопасный запрос
            data = make_api_request(base_url + endpoint, params)
            
            if data is None:
                print("❌ Не удалось получить данные после всех попыток, пропускаем...")
                current_start += 60 * 1000  # пропускаем 1 минуту
                continue

            if data.get("retCode") != 0:
                print(f"❌ Ошибка API: {data.get('retMsg')}")
                time.sleep(1)
                continue  # попробуем ещё раз

            klines = data["result"]["list"]
            if not klines:
                print("ℹ️ Данные закончились (пустой ответ)")
                break

            # Сортируем свечи по времени (на всякий случай)
            klines.sort(key=lambda x: int(x[0]))

            new_klines = 0
            last_ts_in_batch = 0
            for k in klines:
                ts = int(k[0])
                last_ts_in_batch = max(last_ts_in_batch, ts)
                if ts < current_start:
                    continue  # пропускаем свечи ДО текущей границы
                if ts in seen_timestamps:
                    continue  # пропускаем дубли
                if ts >= end_ts:
                    continue  # пропускаем свечи ПОСЛЕ конца периода

                seen_timestamps.add(ts)
                all_klines.append({
                    "timestamp": ts,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
                new_klines += 1

            # Продвигаем current_start на основе МАКСИМАЛЬНОГО timestamp в батче
            if last_ts_in_batch >= current_start:
                current_start = last_ts_in_batch + 1
            else:
                print(f"⚠️ Предупреждение: last_ts_in_batch ({last_ts_in_batch}) < current_start ({current_start})")
                current_start += 60 * 1000  # пропускаем 1 минуту вперёд, чтобы не зациклиться

            request_count += 1
            print(f"✅ Запрос {request_count}: +{new_klines} свечей, всего: {len(all_klines)}, next_start: {current_start}")

            # Автосохранение каждые N запросов
            if request_count - last_save_count >= AUTOSAVE_INTERVAL:
                print("💾 Автосохранение прогресса...")
                save_progress()
                last_save_count = request_count

            if new_klines == 0:
                print("ℹ️ Нет новых свечей в батче — пропускаем 1 минуту")
                current_start += 60 * 1000

            time.sleep(0.2)  # уважаем rate limit

        if request_count >= MAX_REQUESTS:
            print(f"🚨 Достигнут лимит запросов ({MAX_REQUESTS}) — возможно, зацикливание. Прерываем.")

        # Финальное сохранение
        if all_klines:
            # Сохраняем финальную версию без _PARTIAL в имени
            final_filename = f"data/bybit_{SYMBOL.lower()}_{INTERVAL}_{START_DATE.replace('-', '')}_{END_DATE.replace('-', '')}.csv"
            
            df = pd.DataFrame(all_klines)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            df = df[~df.index.duplicated(keep='first')]  # Финальная очистка от дублей

            # Проверка целостности
            total_expected = 0
            total_actual = len(df)
            gaps = 0
            if len(df) > 1:
                total_expected = int((df.index[-1] - df.index[0]).total_seconds() / INTERVAL_SECONDS) + 1
                gaps = total_expected - total_actual

            df.to_csv(final_filename)

            print(f"\n🎉 ФИНАЛЬНОЕ СОХРАНЕНИЕ: {total_actual} уникальных свечей в {final_filename}")
            if len(df) > 1:
                print(f"📅 Диапазон: {df.index[0]} — {df.index[-1]}")
                print(f"📊 Ожидалось: {total_expected} минут")
                print(f"📉 Пропущено: {gaps} минут ({gaps/total_expected:.2%})")

            # Удаляем временные файлы
            if filename and os.path.exists(filename):
                os.remove(filename)
                print(f"🗑️ Удален временный файл: {filename}")
            resume_file = filename.replace('.csv', '_resume.json') if filename else ""
            if resume_file and os.path.exists(resume_file):
                os.remove(resume_file)
                print(f"🗑️ Удален файл возобновления: {resume_file}")
                
            if len(all_klines) > 1_100_000:
                print(f"🚨 ВНИМАНИЕ: данных больше 1.1M — проверь, нет ли ошибок в логике!")
        else:
            print("❌ Не удалось загрузить данные")

    except Exception as e:
        print(f"❌ Критическая ошибка в основном цикле: {e}")
        print("💾 Пытаемся сохранить прогресс...")
        save_progress()

if __name__ == "__main__":
    main()