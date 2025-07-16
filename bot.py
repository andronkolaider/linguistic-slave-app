import json
import random
import time
import threading
import schedule
import requests
import logging
from datetime import datetime
import os
import sys
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

TOKEN = '5365827881:AAEJj1aGmwhj2weyqDtXgxPNBiCDcQ2DthI'
CHAT_ID = '-1001220348544'
WORDS_FILE = 'words.json'

CHANCE_GROUPS = {
    1: {"chance": 0.934, "suffix": ""},
    2: {"chance": 0.05, "suffix": "[золотий🥇, 5%]"},
    3: {"chance": 0.01, "suffix": "[☆☆☆легендарний☆☆☆, 1%]"},
    4: {"chance": 0.005, "suffix": "[🕯️🥷🏿таємничий✡️🤘🏿, 0.5%]"},
    5: {"chance": 0.001, "suffix": "[0.1%🥹]"}
}

# === Функции ===

def load_words():
    with open(WORDS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def group_words_by_chance(words):
    groups = defaultdict(list)
    for word_data in words:
        groups[word_data["chanceGroup"]].append(word_data)
    return groups

def choose_chance_group():
    rand_val = random.random()
    cumulative = 0.0
    for group_id in range(1, 6):
        cumulative += CHANCE_GROUPS[group_id]["chance"]
        if rand_val <= cumulative:
            chance_percent = CHANCE_GROUPS[group_id]["chance"] * 100
            logging.info(f"Выбрана группа шанса: {group_id} (шанс: {chance_percent:.1f}%)")
            return group_id
    logging.warning("Не удалось определить группу шанса, используется группа 1 по умолчанию.")
    return 1

def choose_word(words):
    if not words:
        logging.error("Список слов пуст.")
        return None

    groups = group_words_by_chance(words)

    chosen_group = choose_chance_group()
    candidates = groups.get(chosen_group)

    if not candidates:
        non_empty_groups = [g for g in groups if groups[g]]
        if not non_empty_groups:
            logging.error("Нет доступных слов ни в одной группе.")
            return None
        chosen_group = random.choice(non_empty_groups)
        candidates = groups[chosen_group]
        logging.warning(f"Группа {chosen_group} пустая, используется другая группа: {chosen_group}")

    logging.info(f"Найдено слов в группе: {len(candidates)}")

    selected_word = random.choice(candidates)
    logging.info(f"Выбрано слово: \"{selected_word['word']}\"")
    return selected_word

def generate_message(word_data):
    suffix = CHANCE_GROUPS[word_data["chanceGroup"]]["suffix"]
    if word_data.get("isSpecial", False):
        logging.info(f"Формат: isSpecial → отправляется как есть")
        return f"{word_data['word']} {suffix}"
    
    message = f"{word_data['word']} нєгр {suffix}"
    logging.info(f"Формат: обычный → суффикс: {suffix or 'отсутствует'}")
    return message

def send_message(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage' 
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        logging.info(f"Отправлено: {message}")
        return response.json()
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение: {e}")

def job():
    words = load_words()
    chosen = choose_word(words)
    if chosen:
        msg = generate_message(chosen)
        send_message(msg)

# === Telegram Long Polling ===

def handle_updates():
    offset = 0
    while True:
        try:
            url = f'https://api.telegram.org/bot{TOKEN}/getUpdates' 
            params = {'offset': offset, 'timeout': 60}
            response = requests.get(url, params=params)
            data = response.json()

            if data.get('ok'):
                for update in data.get('result', []):
                    offset = update['update_id'] + 1
                    message = update.get('message', {})
                    text = message.get('text')
                    chat_id = message.get('chat', {}).get('id')

                    if text and '/negr' in text.lower() and str(chat_id) == CHAT_ID:
                        words = load_words()
                        chosen = choose_word(words)
                        if chosen:
                            msg = generate_message(chosen)
                            send_message(msg)
        except Exception as e:
            print(f"[Ошибка] Ошибка получения обновлений: {e}")
        time.sleep(1)

# === Планировщик задач ===

schedule.every(6).hours.do(job)

# === Запуск ===

if __name__ == '__main__':
    print("Бот запущен...")

    # Запуск планировщика в отдельном потоке
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(1)

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Обработка команд
    handle_updates()