"""
🎤 Telegram-бот для сбора контактов вокальной школы
Собирает имя + телефон → выдает подарок (видео с упражнениями)
"""

import logging
from datetime import datetime, timedelta
import json
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import asyncio

# ============ КОНФИГУРАЦИЯ ============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Получить у @BotFather в Telegram
ADMIN_ID = 123456789  # Ваш Telegram ID (для получения уведомлений)
GIFTS_DIR = "gifts"  # Папка с подарками (видео, PDF)

# Состояния диалога
WAITING_NAME, WAITING_PHONE = range(2)

# ============ ЛОГИРОВАНИЕ ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ БАЗА ДАННЫХ (JSON) ============
CONTACTS_FILE = 'contacts.json'

def load_contacts():
    """Загрузить контакты из JSON"""
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_contact(name, phone, user_id, username):
    """Сохранить контакт в JSON"""
    contacts = load_contacts()
    contacts.append({
        'id': len(contacts) + 1,
        'name': name,
        'phone': phone,
        'user_id': user_id,
        'username': username,
        'date_registered': datetime.now().isoformat(),
        'day_0_sent': False,
        'day_1_sent': False,
        'day_2_sent': False,
        'day_3_sent': False,
        'day_5_sent': False,
        'day_7_sent': False,
    })
    with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Новый контакт: {name} | {phone}")

# ============ СИСТЕМА РАССЫЛКИ ============

MAILING_MESSAGES = {
    0: (
        "🎁 *День 0: Начинаем!*\n\n"
        "Привет, {name}! 👋\n\n"
        "Вы получили доступ к видео-диагностике вашего голоса.\n\n"
        "📹 Смотрите видео и узнайте, как за 4 недели вы начнёте петь красиво.\n\n"
        "Готовы? 💪"
    ),
    1: (
        "🎤 *День 1: Первые результаты*\n\n"
        "Привет, {name}! 🌟\n\n"
        "Если вы уже начали занятия, то заметили, что горло расслабилось?\n\n"
        "Это нормально! На первом уроке мы убираем 80% зажимов.\n\n"
        "Готовы на пробный урок? Нажмите /book"
    ),
    2: (
        "✨ *День 2: Методика работает*\n\n"
        "Привет, {name}! 🎵\n\n"
        "На день 2 люди уже чувствуют, что их голос меняется.\n\n"
        "Конечно, если они начали занятия 😉\n\n"
        "Запишитесь: /book"
    ),
    3: (
        "💪 *День 3: Ты можешь!*\n\n"
        "Привет, {name}! 🚀\n\n"
        "На день 3 становится ясно: это не просто упражнения, это РЕЗУЛЬТАТ.\n\n"
        "100% людей, которые приходят на урок, удивляются.\n\n"
        "Ты будешь в их числе? /book"
    ),
    5: (
        "📈 *День 5: Конверсия растёт*\n\n"
        "Привет, {name}! 📊\n\n"
        "На день 5 — это последний момент.\n\n"
        "Люди либо записываются, либо забывают о проекте.\n\n"
        "Запиши время: /book\n\n"
        "Скидка 30% ещё действует! (3500₽ вместо 5000₽)"
    ),
    7: (
        "🎯 *День 7: Финальное предложение*\n\n"
        "Привет, {name}! 🎤\n\n"
        "Это последний день, когда действует скидка 30%.\n\n"
        "После этого цена вернётся к 5000₽.\n\n"
        "Хочешь начать за 3500₽? /book\n\n"
        "Место осталось! Вызови админа: /support"
    ),
}

async def check_and_send_mailing(app: Application):
    """Проверить контакты и отправить письма по расписанию"""
    while True:
        try:
            contacts = load_contacts()
            current_time = datetime.now()

            for contact in contacts:
                user_id = contact['user_id']
                name = contact['name']
                registered_date = datetime.fromisoformat(contact['date_registered'])
                days_passed = (current_time - registered_date).days

                # Проверяем каждый день
                for day in [0, 1, 2, 3, 5, 7]:
                    day_key = f'day_{day}_sent'

                    if days_passed >= day and not contact.get(day_key, False):
                        if day in MAILING_MESSAGES:
                            message = MAILING_MESSAGES[day].format(name=name)
                            try:
                                await app.bot.send_message(
                                    chat_id=user_id,
                                    text=message,
                                    parse_mode='Markdown'
                                )
                                contact[day_key] = True
                                logger.info(f"📬 День {day}: {name} ({user_id})")
                            except Exception as e:
                                logger.error(f"❌ Ошибка отправки дня {day} для {name}: {e}")

            # Сохраняем обновленные данные
            with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(contacts, f, ensure_ascii=False, indent=2)

            # Проверяем раз в 1 час
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"❌ Ошибка в mailing loop: {e}")
            await asyncio.sleep(3600)

# ============ КОМАНДЫ БОТА ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /start - начало диалога"""
    user = update.effective_user
    logger.info(f"👤 Новый пользователь: {user.first_name} (@{user.username})")

    message = (
        "🎤 *Привет! Добро пожаловать в вокальную школу!*\n\n"
        "Давайте начнём с простого:\n"
        "✨ Получите 5 бесплатных упражнений\n"
        "✨ Узнайте свой уровень\n"
        "✨ Запишитесь на бесплатный урок\n\n"
        "Для начала напишите ваше имя 👇"
    )

    await update.message.reply_text(message, parse_mode='Markdown')
    return WAITING_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получить имя"""
    name = update.message.text.strip()

    if len(name) < 2:
        await update.message.reply_text("❌ Имя слишком короткое. Напишите полное имя")
        return WAITING_NAME

    # Сохраняем в контекст
    context.user_data['name'] = name

    await update.message.reply_text(
        f"✅ Спасибо, {name}!\n\n"
        "Теперь напишите ваш номер телефона (или нажмите кнопку ниже):",
        reply_markup=ReplyKeyboardMarkup(
            [[{"text": "📱 Отправить номер", "request_contact": True}]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return WAITING_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получить телефон (текстом или контактом)"""

    # Если отправлен контакт через кнопку
    if update.message.contact:
        phone = update.message.contact.phone_number
    # Если отправлен текстом
    else:
        phone = update.message.text.strip()

    # Минимальная валидация
    if len(phone.replace('-', '').replace('+', '').replace(' ', '')) < 10:
        await update.message.reply_text(
            "❌ Номер выглядит неправильно. Проверьте и напишите ещё раз\n"
            "(формат: +79991234567 или 89991234567)"
        )
        return WAITING_PHONE

    # Форматируем телефон
    phone_clean = phone.replace('-', '').replace(' ', '')
    if not phone_clean.startswith('+'):
        phone_clean = '+' + phone_clean

    # Сохраняем контакт
    name = context.user_data['name']
    user_id = update.effective_user.id
    username = update.effective_user.username or "нет"

    save_contact(name, phone_clean, user_id, username)

    # Отправляем подарок
    await send_gift(update, context, name)

    # Уведомляем админа
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✅ *Новый контакт:*\n"
             f"👤 {name}\n"
             f"📱 {phone_clean}\n"
             f"🆔 @{username}",
        parse_mode='Markdown'
    )

    return ConversationHandler.END

async def send_gift(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str):
    """Отправить подарок клиенту"""

    # Убираем клавиатуру
    await update.message.reply_text(
        "⏳ Готовим подарок...",
        reply_markup=ReplyKeyboardRemove()
    )

    gift_message = (
        f"🎁 *Отлично, {name}!*\n\n"
        "Вы получили доступ к персональной видео-диагностике вашего голоса 🎤\n\n"
        "📹 *Видео-диагностика (15 мин):*\n"
        "🔗 [Смотри диагностику](https://youtu.be/YOUR_VIDEO_LINK)\n\n"
        "В видео я:\n"
        "✅ Диагностирую ваши проблемы с голосом\n"
        "✅ Показываю мою методику (за 4 недели вы будете петь красиво)\n"
        "✅ Даю скидку 30%: только *3 500₽* вместо 5 000₽\n\n"
        "⏱️ *Что дальше:*\n"
        "1. Посмотрите видео (15 мин)\n"
        "2. Нажмите /book и запишитесь на пробный урок\n"
        "3. Получите скидку 30% (3 500₽)\n\n"
        "💬 Вопросы? Напишите /help"
    )

    await update.message.reply_text(gift_message, parse_mode='Markdown')

async def book_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /book - запись на урок"""
    await update.message.reply_text(
        "📅 *Бронирование пробного урока*\n\n"
        "Выберите удобное время:\n"
        "🕙 Утро (9:00–12:00)\n"
        "🕐 День (12:00–17:00)\n"
        "🕕 Вечер (17:00–21:00)\n\n"
        "Или напишите время сами.",
        reply_markup=ReplyKeyboardMarkup(
            [["🕙 Утро", "🕐 День"], ["🕕 Вечер", "Своё время"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "❓ *Справка*\n\n"
        "Что я умею:\n"
        "🎁 /start — начать и получить подарок\n"
        "📅 /book — записаться на урок\n"
        "📞 /support — связаться с администратором\n"
        "❓ /help — эта справка\n\n"
        "Остались вопросы? Напишите /support"
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /support"""
    await update.message.reply_text(
        "👩‍🏫 *Поддержка*\n\n"
        "Директор школы: @YourUsername\n"
        "Телефон: +7 (999) 123-45-67\n"
        "Email: info@vocalskoola.ru\n\n"
        "Ответим в течение 1 часа 😊"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    await update.message.reply_text(
        "❌ Диалог отменён.\n"
        "Вы можете начать заново: /start"
    )
    return ConversationHandler.END

# ============ ОБРАБОТЧИК НЕИЗВЕСТНЫХ СООБЩЕНИЙ ============

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на неизвестные сообщения"""
    await update.message.reply_text(
        "Я не понял 😅\n"
        "Используйте команды:\n"
        "/start — начало\n"
        "/book — запись на урок\n"
        "/help — справка"
    )

# ============ ГЛАВНАЯ ФУНКЦИЯ ============

async def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Диалоговый обработчик (сбор контактов)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('book', book_lesson))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('support', support))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    logger.info("🚀 Бот запущен!")
    logger.info("📬 Система рассылки активирована (дни 0-7)")

    # Запускаем систему рассылки в фоне
    asyncio.create_task(check_and_send_mailing(application))

    # Запуск
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
