import json
import telebot
from datetime import datetime, timedelta
import os
from apscheduler.schedulers.background import BackgroundScheduler

# Замените на ваш токен бота
TOKEN = '7932190127:AAEK-QMVD3lSXnYzOKc6AEC5AzZLrDDMqeU'
bot = telebot.TeleBot(TOKEN)

# Файл для хранения расписания
SCHEDULE_FILE = 'schedule.json'

scheduler = BackgroundScheduler()
scheduler.start()

# Загрузка расписания из файла
def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    return {}

# Сохранение расписания в файл
def save_schedule():
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(user_events, f, default=str) 

# Инициализация расписания и режима мониторинга при запуске
user_events = load_schedule()
monitoring_mode = {}  # Словарь для хранения состояния мониторинга для каждого пользователя

# Предустановленное расписание для "Дневного мониторинга"
predefined_schedule = [
    ("9:00", "проверка дашбордов (не забыть eywa, dq_streaming)(сверки)"),
    ("9:30", "заполнение статистики по РУСПМ"),
    ("9:35", "проверка нового загрузчика"),
    ("10:00", "смотрим телеграм, должна придти отбивка, что не завис и на протяжении всего дня реагируем на алерты оттуда"),
    ("10:30", "проверка легаси загрузчика"),
    ("11:00", "проверка нового загрузчика"),
    ("11:10", "смотрим сверку late"),
    ("11:11", "проверка отправки референсов"),
    ("15:00", "смотрим проверку данных перед синхронизацией"),
    ("16:00", "проверка легси загрузчика - операция 299"),
    ("16:10", "проверка отправки референсов"),
    ("17:10", "смотрим на синхронизацию и ошибки"),
    ("17:50", "смотрим легаси производство - всего 10 операций на данный момент")
]

# Функция для отправки уведомления
def send_notification(chat_id, message):
    bot.send_message(chat_id, f"**Уведомление**\n{message}", parse_mode="Markdown")

# Функция для запуска таймера
def schedule_notification(chat_id, event_time, message):
    now = datetime.now()
    send_time = datetime.combine(now, event_time)
    if send_time < now:
        send_time += timedelta(days=1)

    scheduler.add_job(send_notification, 'date', run_date=send_time, args=[chat_id, message])



# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я могу помочь вам создать расписание с ежедневными уведомлениями.\n\n"
"Доступные команды:\n"
                                       "/add - Добавить события\n"
                                       "/view - Просмотреть расписание\n"
                                       "/edit - Изменить событие\n"
                                       "/delete - Удалить все события\n"
                                       "/monitoring_on - Включить Дневной мониторинг\n"
                                       "/monitoring_off - Отключить Дневной мониторинг")

# Обработчик команды /view
@bot.message_handler(commands=['view'])
def view_schedule(message):
    user_id = str(message.chat.id)
    events = user_events.get(user_id, [])
    if not events:
        bot.send_message(user_id, "У вас нет запланированных событий.")
    else:
        schedule_text = "\n".join([f"{event['time']} - {event['description']}" for event in events])
        bot.send_message(user_id, f"Ваше расписание:\n{schedule_text}")

# Обработчик команды /delete
@bot.message_handler(commands=['delete'])
def delete_schedule(message):
    user_id = str(message.chat.id)
    if user_id in user_events:
        del user_events[user_id]
        save_schedule()
        bot.send_message(user_id, "Ваше расписание удалено.")
    else:
        bot.send_message(user_id, "У вас нет запланированных событий для удаления.")

# Обработчик команды /add
@bot.message_handler(commands=['add'])
def add_events_prompt(message):
    bot.send_message(message.chat.id, "Введите события в формате 'HH:MM Описание' каждое с новой строки.\n"
                                      "Например:\n09:30 Вкусно покушать\n12:00 Сладко поспать\n17:00 Проверка теста")
    bot.register_next_step_handler(message, add_events)

# Функция добавления событий
def add_events(message):
    user_id = str(message.chat.id)
    events = message.text.splitlines()
    new_events = []
    
    for event in events:
        try:
            time_str, event_description = event.split(' ', 1)
            event_time = datetime.strptime(time_str, '%H:%M').time()
            new_events.append({"time": time_str, "description": event_description})
            schedule_notification(message.chat.id, event_time, event_description)
        except ValueError:
            bot.send_message(user_id, f"Неверный формат для строки: '{event}'. Используйте 'HH:MM Описание'.")
            return
    
    if user_id not in user_events:
        user_events[user_id] = []
    
    user_events[user_id].extend(new_events)
    save_schedule()  # Сохраняем расписание после добавления событий
    bot.send_message(user_id, "События добавлены в ваше расписание.")
# Дневной мониторинг
original_user_events = {} # Для хранения оригинального расписания при включении мониторинга

@bot.message_handler(commands=['monitoring_on'])
def activate_monitoring(message):
    user_id = str(message.chat.id)
    monitoring_mode[user_id] = True
    # Сохраняем оригинальное расписание
    original_user_events[user_id] = user_events.get(user_id, [])
    # Устанавливаем предустановленное расписание
    user_events[user_id] = [{"time": time_str, "description": desc} for time_str, desc in predefined_schedule]
    save_schedule() # Сохраняем расписание
    for event in user_events[user_id]:
        schedule_notification(message.chat.id, datetime.strptime(event['time'], "%H:%M").time(), event['description'])
    bot.send_message(message.chat.id, "Дневной мониторинг включен.")


@bot.message_handler(commands=['monitoring_off'])
def deactivate_monitoring(message):
    user_id = str(message.chat.id)
    if user_id in monitoring_mode:
        del monitoring_mode[user_id]
        # Восстанавливаем оригинальное расписание
        user_events[user_id] = original_user_events.get(user_id, [])
        del original_user_events[user_id]
        save_schedule() # Сохраняем расписание
        bot.send_message(message.chat.id, "Дневной мониторинг выключен.")
    else:
        bot.send_message(message.chat.id, "Дневной мониторинг не был включен.")


bot.polling(none_stop=True)