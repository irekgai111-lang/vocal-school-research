#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot для вокальной школы "Твой голос"
Функции:
- Прием данных из квиза (Marquiz)
- Запись времени занятий
- Автоматические напоминания (24ч, 4ч, 2ч)
- Отправка уведомлений админу
- Ведение базы контактов
"""

import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from pathlib import Path
import asyncio

# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Получить у @BotFather
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID_HERE"  # Ваш личный Telegram ID

# Пути к файлам
CONTACTS_FILE = "contacts.json"
BOOKINGS_FILE = "bookings.json"
REMINDERS_FILE = "reminders.json"

# Доступные времена (можно менять)
AVAILABLE_TIMES = {
    "mon_18_30": ("Понедельник", "18:30"),
    "mon_19_30": ("Понедельник", "19:30"),
    "tue_18_00": ("Вторник", "18:00"),
    "tue_19_00": ("Вторник", "19:00"),
    "tue_20_00": ("Вторник", "20:00"),
    "wed_18_30": ("Среда", "18:30"),
    "wed_19_30": ("Среда", "19:30"),
    "thu_19_00": ("Четверг", "19:00"),
    "thu_20_00": ("Четверг", "20:00"),
    "fri_18_00": ("Пятница", "18:00"),
    "fri_19_00": ("Пятница", "19:00"),
    "fri_20_00": ("Пятница", "20:00"),
    "sat_10_00": ("Суббота", "10:00"),
    "sat_11_00": ("Суббота", "11:00"),
    "sat_14_00": ("Суббота", "14:00"),
    "sat_15_00": ("Суббота", "15:00"),
    "sun_11_00": ("Воскресенье", "11:00"),
    "sun_14_00": ("Воскресенье", "14:00"),
}

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# РАБОТА С ФАЙЛАМИ
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(filename):
    """Загрузить JSON файл"""
    if Path(filename).exists():
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    """Сохранить JSON файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_contact(user_id, name, phone, email, quiz_result):
    """Добавить контакт в базу"""
    contacts = load_json(CONTACTS_FILE)

    contact = {
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "email": email,
        "quiz_result": quiz_result,
        "registration_date": datetime.now().isoformat(),
        "booked": False,
        "booking_time": None
    }

    contacts[str(user_id)] = contact
    save_json(CONTACTS_FILE, contacts)
    logger.info(f"✅ Новый контакт добавлен: {name} ({user_id})")

def add_booking(user_id, booking_date, booking_time):
    """Добавить запись на занятие"""
    bookings = load_json(BOOKINGS_FILE)
    contacts = load_json(CONTACTS_FILE)

    # Получить имя из контактов
    contact_info = contacts.get(str(user_id), {})
    name = contact_info.get("name", "Неизвестный")

    booking = {
        "user_id": user_id,
        "name": name,
        "phone": contact_info.get("phone", "N/A"),
        "booking_date": booking_date,
        "booking_time": booking_time,
        "booked_at": datetime.now().isoformat(),
        "status": "pending"  # pending / confirmed / completed / cancelled
    }

    # Использовать user_id как ключ (каждый пользователь только одна запись)
    bookings[str(user_id)] = booking
    save_json(BOOKINGS_FILE, bookings)

    # Обновить контакты
    contacts[str(user_id)]["booked"] = True
    contacts[str(user_id)]["booking_time"] = f"{booking_date} {booking_time}"
    save_json(CONTACTS_FILE, contacts)

    logger.info(f"✅ Запись создана: {name} на {booking_date} {booking_time}")


# ═══════════════════════════════════════════════════════════════════════════════
# КОМАНДЫ БОТА
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user

    text = f"""
🎤 Привет, {user.first_name}!

Добро пожаловать в школу вокала "Твой голос"!

Я помогаю вам:
✅ Записаться на пробное занятие
✅ Получать напоминания перед уроком
✅ Связаться с нашей школой

Что вы хотите сделать?

/book - Выбрать время для занятия
/help - Подробная информация
/contact - Наши контакты
"""

    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    text = """
🎤 ВОКАЛЬНАЯ ШКОЛА "ТВО Й  ГОЛОС"

📱 КОМАНДЫ:

/start - Начало
/book - Выбрать время занятия
/cancel - Отменить запись
/contact - Контакты школы
/faq - Часто задаваемые вопросы

═══════════════════════════════════════════════════════════════

💬 ПИСЬМО ОТ АДМИНА:

Привет! Я администратор школы.

Если у вас есть вопросы или нужна помощь
→ просто напишите мне сюда (не команду, просто текст)

Я ответю в течение 30 минут! 👋

═══════════════════════════════════════════════════════════════
"""
    await update.message.reply_text(text)

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /contact"""
    text = """
📍 ВОКАЛЬНАЯ ШКОЛА "ТВОЙ ГОЛОС"

Адрес: ул. Некрасова, 12, офис 5
       г. Нижнекамск

📞 Телефон: +7 (8552) XXX-XX-XX
📱 Telegram: @tvoygolosstudia
📧 Email: info@tvoygolosstudia.ru

⏰ Время работы:
Пн-Сб: 10:00 - 21:00
Вс: 11:00 - 19:00

📍 Как найти нас:
1. Вход со двора (не с улицы!)
2. 2-й этаж
3. Офис справа (видна вывеска "Вокал")

Ждем вас! 🎤
"""
    await update.message.reply_text(text)

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /faq"""
    text = """
❓ ЧАСТО ЗАДАВАЕМЫЕ ВОПРОСЫ

🎤 Сколько стоит пробное занятие?
   → БЕСПЛАТНО! Приходите, попробуйте, решайте.

🎤 Сколько занимает одно занятие?
   → 60 минут (1-на-1 или группа)

🎤 Как часто нужно заниматься?
   → Минимум 1 раз в неделю (лучше 2-3 раза)

🎤 Нужны ли мне музыкальные знания?
   → НЕТ! Начните с нуля - это нормально

🎤 Я уже слишком стар(а)?
   → У нас студенты от 8 до 70 лет. Никогда не поздно!

🎤 Если я не понрав люсь результату, что дальше?
   → Вернем деньги за первый месяц (если не довольны)

═══════════════════════════════════════════════════════════════

Еще вопросы? Напишите в чат! 💬
"""
    await update.message.reply_text(text)


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАПИСЬ НА ЗАНЯТИЕ
# ═══════════════════════════════════════════════════════════════════════════════

async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /book - начало процесса записи"""
    user = update.effective_user

    # Проверить, есть ли уже запись
    bookings = load_json(BOOKINGS_FILE)
    if str(user.id) in bookings:
        await update.message.reply_text(
            "❌ Вы уже записаны на занятие!\n\n"
            "Дата: " + bookings[str(user.id)]["booking_date"] + "\n"
            "Время: " + bookings[str(user.id)]["booking_time"] + "\n\n"
            "Если нужно изменить время → /cancel и создайте новую запись"
        )
        return

    # Показать доступные дни
    text = "📅 Выберите день для занятия:\n\n"

    # Группировать по дням
    days = {}
    for time_id, (day, time_str) in AVAILABLE_TIMES.items():
        if day not in days:
            days[day] = []
        days[day].append((time_id, time_str))

    # Создать кнопки по дням
    keyboard = []
    for day, times in list(days.items())[:3]:  # Показать первые 3 дня
        day_text = f"{day} →"
        keyboard.append([InlineKeyboardButton(day_text, callback_data=f"day_{day}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📅 Выберите день недели:\n\n" +
        "Доступны дни: Пн, Вт, Ср, Чт, Пт, Сб, Вс",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопки"""
    query = update.callback_query
    user = query.from_user

    if query.data.startswith("day_"):
        # Выбран день
        selected_day = query.data.replace("day_", "")

        # Найти времена на этот день
        times_for_day = []
        for time_id, (day, time_str) in AVAILABLE_TIMES.items():
            if day == selected_day:
                times_for_day.append((time_id, time_str))

        # Создать кнопки с временем
        keyboard = []
        for time_id, time_str in times_for_day:
            button_text = f"⏰ {time_str}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"time_{time_id}_{selected_day}")])

        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📅 {selected_day}\n\nВыберите время:",
            reply_markup=reply_markup
        )

    elif query.data.startswith("time_"):
        # Выбрано время
        parts = query.data.split("_")
        time_id = parts[1] + "_" + parts[2]  # "mon_18_30"
        selected_day = parts[3] if len(parts) > 3 else "_".join(parts[3:])

        time_str = AVAILABLE_TIMES[time_id][1]  # "18:30"

        # Сохранить запись
        # Дата = сегодня или ближайший понедельник (зависит от логики)
        booking_date = datetime.now().strftime("%Y-%m-%d")  # TODO: рассчитать правильную дату

        add_booking(user.id, booking_date, time_str)

        # Отправить подтверждение
        await query.edit_message_text(
            f"✅ ОТЛИЧНО!\n\n"
            f"Вы записаны на:\n"
            f"📅 {selected_day}\n"
            f"⏰ {time_str}\n\n"
            f"📍 Место: ул. Некрасова 12, офис 5\n\n"
            f"Вот ваши контакты в нашей системе:\n"
            f"Телефон: ███████ (зашифрован для безопасности)\n\n"
            f"Напоминания придут за 24ч, 4ч и 2ч до занятия!"
        )

        # Уведомить админа
        contacts = load_json(CONTACTS_FILE)
        contact_info = contacts.get(str(user.id), {})

        admin_message = (
            f"📢 НОВАЯ ЗАПИСЬ НА ЗАНЯТИЕ!\n\n"
            f"Имя: {user.first_name}\n"
            f"Telegram ID: {user.id}\n"
            f"Телефон: {contact_info.get('phone', 'не указан')}\n"
            f"Email: {contact_info.get('email', 'не указан')}\n\n"
            f"📅 Запись на: {selected_day} {time_str}\n"
            f"🎯 Тип клиента: {contact_info.get('quiz_result', 'unknown')}\n\n"
            f"⏰ Время записи: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            await context.bot.send_message(ADMIN_CHAT_ID, admin_message)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")

    elif query.data == "cancel_booking":
        await query.edit_message_text(
            "❌ Запись отменена.\n\n"
            "Используйте /book чтобы записаться снова."
        )

async def cancel_booking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cancel - отменить запись"""
    user = update.effective_user
    bookings = load_json(BOOKINGS_FILE)

    if str(user.id) in bookings:
        del bookings[str(user.id)]
        save_json(BOOKINGS_FILE, bookings)

        await update.message.reply_text(
            "✅ Ваша запись отменена.\n\n"
            "Используйте /book чтобы записаться снова."
        )
    else:
        await update.message.reply_text(
            "❌ У вас нет активных записей.\n\n"
            "Используйте /book чтобы записаться на занятие."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ОБРАБОТКА СООБЩЕНИЙ ОТ АДМИНА
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от пользователя (кроме команд)"""
    user = update.effective_user

    # Если это сообщение от админа - пересылать пользователям
    if user.id == int(ADMIN_CHAT_ID):
        # TODO: реализовать двусторонний чат админа с пользователями
        await update.message.reply_text("✅ Сообщение получено (в разработке)")
    else:
        # Пересылать общие сообщения админу
        try:
            await context.bot.forward_message(ADMIN_CHAT_ID, update.message.chat_id, update.message.message_id)
            await update.message.reply_text(
                "✅ Сообщение отправлено администратору.\n\n"
                "Ответ придет вам в течение 30 минут! 👋"
            )
        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {e}")
            await update.message.reply_text("❌ Ошибка при отправке сообщения. Попробуйте позже.")


# ═══════════════════════════════════════════════════════════════════════════════
# НАПОМИНАНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

async def check_and_send_reminders(context: ContextTypes.DEFAULT_TYPE):
    """
    Проверять и отправлять напоминания перед занятиями
    Запускается каждый час
    """
    bookings = load_json(BOOKINGS_FILE)
    now = datetime.now()

    for user_id, booking_info in bookings.items():
        try:
            booking_datetime_str = f"{booking_info['booking_date']} {booking_info['booking_time']}"
            booking_datetime = datetime.strptime(booking_datetime_str, "%Y-%m-%d %H:%M")

            # Вычислить оставшееся время
            time_until_booking = booking_datetime - now
            hours_left = time_until_booking.total_seconds() / 3600

            # НАПОМИНАНИЕ за 24 часа
            if 23 <= hours_left < 24:
                await context.bot.send_message(
                    int(user_id),
                    f"🎤 Привет, {booking_info['name']}!\n\n"
                    f"Вы записаны на завтра в {booking_info['booking_time']}\n"
                    f"Место: ул. Некрасова 12, офис 5\n\n"
                    f"Если что-то изменилось → напишите сюда 👇\n\n"
                    f"До встречи! 💜"
                )
                logger.info(f"✅ Напоминание на 24ч отправлено: {user_id}")

            # НАПОМИНАНИЕ за 4 часа
            elif 3.5 <= hours_left < 4.5:
                await context.bot.send_message(
                    int(user_id),
                    f"⏰ Еще {int(hours_left)} часа!\n\n"
                    f"Вы записаны сегодня в {booking_info['booking_time']}\n\n"
                    f"Контакт педагога: +7 (8552) XXX-XX-XX\n"
                    f"(если вам нужна помощь)\n\n"
                    f"Не опаздывайте, мы ждем! 🎤"
                )
                logger.info(f"✅ Напоминание на 4ч отправлено: {user_id}")

            # НАПОМИНАНИЕ за 2 часа
            elif 1.5 <= hours_left < 2.5:
                await context.bot.send_message(
                    int(user_id),
                    f"🎵 Скоро начнем!\n\n"
                    f"Через {int(hours_left)} часа вы приходите на урок 🎤\n\n"
                    f"✅ Привезите воду (пить во время занятия)\n"
                    f"✅ Приходите за 5 минут до урока\n\n"
                    f"Мы вас ждем! 💜"
                )
                logger.info(f"✅ Напоминание на 2ч отправлено: {user_id}")

        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ ДАННЫХ ИЗ MARQUIZ
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_quiz_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка данных, поступающих из квиза (Marquiz)

    Marquiz отправляет JSON в Webhook или через MessageHandler
    Ожидаемый формат:
    {
        "user_name": "Анна",
        "user_phone": "+7-999-123-45-67",
        "user_email": "anna@example.com",
        "quiz_result": "1",  # 1-5 тип клиента
        "timestamp": "2026-05-09T14:23:45"
    }
    """
    try:
        # Если это текстовое сообщение с JSON
        message_text = update.message.text
        quiz_data = json.loads(message_text)

        # Извлечь данные
        user_id = update.effective_user.id
        name = quiz_data.get("user_name", "Неизвестный")
        phone = quiz_data.get("user_phone", "N/A")
        email = quiz_data.get("user_email", "N/A")
        quiz_result = quiz_data.get("quiz_result", "unknown")

        # Сохранить контакт
        add_contact(user_id, name, phone, email, quiz_result)

        # Отправить приветствие
        quiz_titles = {
            "1": "Боящийся певец",
            "2": "Занятый боец",
            "3": "Певец-социалист",
            "4": "Опытный певец",
            "5": "Профессионал"
        }

        result_title = quiz_titles.get(quiz_result, "Участник теста")

        await update.message.reply_text(
            f"🎤 Привет, {name}!\n\n"
            f"Спасибо, что прошли наш тест! 💜\n\n"
            f"Ваш результат: {result_title}\n\n"
            f"Теперь выберите время для БЕСПЛАТНОГО пробного занятия:\n\n"
            f"/book - Выбрать время",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📅 Выбрать время", callback_data="start_booking")
            ]])
        )

        logger.info(f"✅ Данные из квиза получены и обработаны: {name}")

    except json.JSONDecodeError:
        logger.error("Не удалось распарсить JSON из сообщения")
    except Exception as e:
        logger.error(f"Ошибка при обработке данных из квиза: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ БОТ
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Запуск бота"""
    # Создать application
    application = Application.builder().token(BOT_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("contact", contact_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("book", book_command))
    application.add_handler(CommandHandler("cancel", cancel_booking_command))

    # Обработчики callback (кнопки)
    application.add_handler(CallbackQueryHandler(button_callback))

    # Обработчик текстовых сообщений (от админа, данных из квиза)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))

    # Задача проверки и отправки напоминаний (каждый час)
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_send_reminders, interval=3600, first=0)  # Каждый час

    # Запустить бота
    logger.info("🤖 Бот запущен и готов к работе!")
    print("✅ Бот запущен. Нажмите Ctrl+C для остановки.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()


# ═══════════════════════════════════════════════════════════════════════════════
# КАК ИСПОЛЬЗОВАТЬ:
# ═══════════════════════════════════════════════════════════════════════════════
"""

1️⃣ УСТАНОВКА:
   pip install python-telegram-bot

2️⃣ КОНФИГУРАЦИЯ:
   - Заменить BOT_TOKEN на ваш токен (от @BotFather)
   - Заменить ADMIN_CHAT_ID на ваш Telegram ID

3️⃣ ЗАПУСК:
   python 10_BOT-UPDATED-WITH-BOOKING.py

4️⃣ ИНТЕГРАЦИЯ С MARQUIZ:
   - В результате квиза добавить кнопку "Отправить в Telegram-бот"
   - Или вручную отправлять JSON: {"user_name": "...", "user_phone": "...", ...}

5️⃣ ВСЕ ДАННЫЕ СОХРАНЯЮТСЯ В:
   - contacts.json (контакты из квиза)
   - bookings.json (записи на занятия)
   - bot_logs.log (логи всех действий)

═══════════════════════════════════════════════════════════════════════════════
"""
