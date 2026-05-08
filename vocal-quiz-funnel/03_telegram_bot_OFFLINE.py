"""
🎤 Telegram-бот для вокальной школы (ОФЛАЙН-МОДЕЛЬ)
Собирает контакты → Рассылает напоминания → Конвертит в пробное занятие → Оплата
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

# Ссылки на платежи
PAYMENT_LINK = "https://your-payment-link.com"
SUPPORT_USERNAME = "YourUsername"
SUPPORT_PHONE = "+7 (999) 123-45-67"

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
        'username': username or "нет",
        'date_registered': datetime.now().isoformat(),
        'trial_lesson_scheduled': False,
        'trial_lesson_date': None,
        'trial_lesson_time': None,
        'paid': False,
        'payment_date': None,
        'day_0_sent': False,
        'day_1_sent': False,
        'day_3_sent': False,
        'day_5_sent': False,
        'day_7_sent': False,
    })
    with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Новый контакт: {name} | {phone}")

def find_contact(user_id):
    """Найти контакт по user_id"""
    contacts = load_contacts()
    for contact in contacts:
        if contact['user_id'] == user_id:
            return contact
    return None

def update_contact(user_id, **kwargs):
    """Обновить контакт"""
    contacts = load_contacts()
    for contact in contacts:
        if contact['user_id'] == user_id:
            contact.update(kwargs)
            with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(contacts, f, ensure_ascii=False, indent=2)
            return True
    return False

# ============ ПЕРЕРАБОТАННАЯ СИСТЕМА РАССЫЛКИ (ОФЛАЙН-МОДЕЛЬ) ============

MAILING_MESSAGES = {
    0: (
        "🎉 Спасибо, {name}!\n\n"
        "Я проверила твои ответы 🎯\n\n"
        "Вот что я вижу: ты именно та, кому нужна эта программа.\n\n"
        "✅ Вот что дальше:\n\n"
        "1️⃣ Запиши БЕСПЛАТНОЕ пробное занятие\n"
        "   (Реальный голос, реальные результаты за 60 минут)\n\n"
        "2️⃣ Приходи в студию и увидишь сам(а)\n\n"
        "3️⃣ Если понравилось → Оплати в день пробного и получи:\n"
        "   💝 Пакет из 8 уроков\n"
        "   💝 + 2 урока в подарок (итого 10 уроков!)\n\n"
        "🎤 Запишись на урок: /book"
    ),
    1: (
        "🌟 {name}, твой пробный урок завтра! \n\n"
        "Я уверена, что тебе понравится 🎵\n\n"
        "Что ты получишь за 60 минут:\n"
        "✅ Диагностика твоего голоса (прямо на уроке)\n"
        "✅ Первые упражнения (ты сразу почувствуешь разницу)\n"
        "✅ Индивидуальный план развития\n\n"
        "Помни: первый урок БЕСПЛАТНЫЙ! \n\n"
        "Если не можешь прийти → напиши /reschedule"
    ),
    3: (
        "💪 {name}!\n\n"
        "Как прошёл твой пробный урок? 🎤\n\n"
        "Если прошёл:\n"
        "✅ Отлично! При оплате в день пробного получи:\n"
        "✅ Пакет из 8 уроков + 2 урока в подарок (итого 10!)\n\n"
        "Ссылка для оплаты: /pay\n\n"
        "Если не пришёл:\n"
        "❓ Что случилось? Могу я чем-то помочь?\n"
        "📞 Напиши /support или позвони: {support_phone}"
    ),
    5: (
        "⏰ {name}, ВНИМАНИЕ! \n\n"
        "Специальное предложение действует ещё 2 дня! \n\n"
        "При оплате в день пробного:\n"
        "✅ Пакет из 8 уроков + 2 урока в подарок (итого 10!)\n\n"
        "После 2 дней предложение закончится.\n\n"
        "Оплати сейчас: /pay"
    ),
    7: (
        "🎯 {name}, это последний день!\n\n"
        "Специальное предложение заканчивается СЕГОДНЯ в 23:59\n\n"
        "Сегодня при оплате в день пробного:\n"
        "✅ Пакет из 8 уроков + 2 урока в подарок (итого 10!)\n\n"
        "После сегодня предложение закончится.\n\n"
        "Начни свой путь в вокале СЕЙЧАС! 🚀\n\n"
        "Оплати: /pay\n"
        "Вопросы: /support"
    ),
}

async def check_and_send_mailing(app: Application):
    """Проверить контакты и отправить рассылку по расписанию"""
    while True:
        try:
            contacts = load_contacts()
            current_time = datetime.now()

            for contact in contacts:
                user_id = contact['user_id']
                name = contact['name']
                registered_date = datetime.fromisoformat(contact['date_registered'])
                days_passed = (current_time - registered_date).days

                # Проверяем каждый день рассылки
                for day in [0, 1, 3, 5, 7]:
                    day_key = f'day_{day}_sent'

                    if days_passed >= day and not contact.get(day_key, False):
                        if day in MAILING_MESSAGES:
                            message = MAILING_MESSAGES[day].format(
                                name=name,
                                support_phone=SUPPORT_PHONE
                            )
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
        "🎤 *Привет! Добро пожаловать в вокальную школу!* 👋\n\n"
        "Спасибо, что прошёл(а) тест! 🌟\n\n"
        "Давайте начнём с простого:\n"
        "✨ Получи БЕСПЛАТНОЕ пробное занятие\n"
        "✨ Узнайте свой уровень\n"
        "✨ Начни петь правильно!\n\n"
        "Для начала напишите ваше имя 👇"
    )

    await update.message.reply_text(message, parse_mode='Markdown')
    return 0  # WAITING_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получить имя"""
    name = update.message.text.strip()

    if len(name) < 2:
        await update.message.reply_text("❌ Имя слишком короткое. Напишите полное имя")
        return 0

    context.user_data['name'] = name

    await update.message.reply_text(
        f"✅ Спасибо, {name}!\n\n"
        "Теперь напишите ваш номер телефона:",
        reply_markup=ReplyKeyboardMarkup(
            [[{"text": "📱 Отправить номер", "request_contact": True}]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return 1  # WAITING_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получить телефон"""
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    if len(phone.replace('-', '').replace('+', '').replace(' ', '')) < 10:
        await update.message.reply_text(
            "❌ Номер выглядит неправильно. Проверьте и напишите ещё раз\n"
            "(формат: +79991234567 или 89991234567)"
        )
        return 1

    phone_clean = phone.replace('-', '').replace(' ', '')
    if not phone_clean.startswith('+'):
        phone_clean = '+' + phone_clean

    name = context.user_data['name']
    user_id = update.effective_user.id
    username = update.effective_user.username or "нет"

    save_contact(name, phone_clean, user_id, username)

    await update.message.reply_text(
        "⏳ Спасибо! Сейчас тебе всё отправлю...",
        reply_markup=ReplyKeyboardRemove()
    )

    gift_message = (
        f"🎉 Отлично, {name}!\n\n"
        "Вот что дальше 👇\n\n"
        "📅 Запиши БЕСПЛАТНОЕ пробное занятие:\n"
        "/book\n\n"
        "Что ты получишь:\n"
        "✅ Полная диагностика твоего голоса\n"
        "✅ Первые упражнения (результат за 60 мин)\n"
        "✅ Индивидуальный план\n\n"
        "И если понравится - оплати в день пробного:\n"
        "💝 Пакет из 8 уроков\n"
        "💝 + 2 урока в подарок (итого 10 уроков!)\n\n"
        "Начинаем! 🚀"
    )

    await update.message.reply_text(gift_message, parse_mode='Markdown')

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

async def book_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /book - запись на пробное занятие"""
    user_id = update.effective_user.id
    contact = find_contact(user_id)

    if not contact:
        await update.message.reply_text(
            "❌ Сначала напиши /start и пройди регистрацию!"
        )
        return

    message = (
        "📅 *Бронирование пробного занятия*\n\n"
        "Выбери удобное время:\n\n"
        "🕙 Утро (9:00–12:00)\n"
        "🕐 День (12:00–17:00)\n"
        "🕕 Вечер (17:00–21:00)\n\n"
        "Ответь цифрой: 1 (утро), 2 (день), 3 (вечер)"
    )

    await update.message.reply_text(message, parse_mode='Markdown')
    context.user_data['booking_step'] = 1
    context.user_data['user_id'] = user_id

async def handle_booking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени бронирования"""
    if not context.user_data.get('booking_step'):
        return

    user_id = update.effective_user.id
    choice = update.message.text.strip()

    time_slots = {
        '1': '9:00–12:00 (Утро)',
        '2': '12:00–17:00 (День)',
        '3': '17:00–21:00 (Вечер)'
    }

    if choice in time_slots:
        time_slot = time_slots[choice]
        context.user_data['booking_step'] = 2
        context.user_data['time_slot'] = time_slot

        await update.message.reply_text(
            f"✅ Выбрано время: {time_slot}\n\n"
            "Какую дату предпочитаешь?\n"
            "(Напиши дату: ДД.MM или \"завтра\", \"послезавтра\")"
        )
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, выбери: 1 (утро), 2 (день) или 3 (вечер)"
        )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /pay - оплата"""
    user_id = update.effective_user.id
    contact = find_contact(user_id)

    if not contact:
        await update.message.reply_text("❌ Сначала напиши /start!")
        return

    payment_message = (
        f"💳 *При оплате в день пробного:*\n"
        f"*Пакет из 8 уроков + 2 урока в подарок (итого 10!)*\n\n"
        f"*{contact['name']}*, вот варианты оплаты:\n\n"
        f"1️⃣ Перевод на карту\n"
        f"2️⃣ Яндекс.Касса\n"
        f"3️⃣ СБП (Система быстрых платежей)\n\n"
        f"🔗 Ссылка: {PAYMENT_LINK}\n\n"
        f"После оплаты:\n"
        f"✅ Напиши /paid и укажи сумму\n"
        f"❓ Вопросы? /support"
    )

    await update.message.reply_text(payment_message, parse_mode='Markdown')

async def reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reschedule - перенос пробного"""
    user_id = update.effective_user.id
    contact = find_contact(user_id)

    if not contact:
        await update.message.reply_text("❌ Сначала напиши /start!")
        return

    message = (
        f"📅 *Перенос пробного занятия*\n\n"
        f"Хочешь перенести пробное занятие, {contact['name']}?\n\n"
        f"Какая дата тебе удобна?\n"
        f"(Напиши: ДД.MM или \"завтра\", \"послезавтра\")\n\n"
        f"А что случилось?\n"
        f"- Работа\n"
        f"- Болезнь\n"
        f"- Другое\n\n"
        f"Мы перенесём! 💜"
    )

    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = (
        "❓ *Справка*\n\n"
        "Что я умею:\n"
        "🎤 /start — начать и зарегистрироваться\n"
        "📅 /book — записаться на пробное занятие\n"
        "💳 /pay — оплатить\n"
        "📆 /reschedule — перенести пробное\n"
        "👩‍🏫 /support — контакты директора\n"
        "❓ /help — эта справка"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /support"""
    support_text = (
        f"👩‍🏫 *Поддержка*\n\n"
        f"Директор: @{SUPPORT_USERNAME}\n"
        f"Телефон: {SUPPORT_PHONE}\n"
        f"Email: info@vocalschool.ru\n\n"
        f"Ответим в течение 1 часа! 😊"
    )
    await update.message.reply_text(support_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    await update.message.reply_text(
        "❌ Диалог отменён.\n"
        "Вы можете начать заново: /start"
    )
    return ConversationHandler.END

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ на неизвестные сообщения"""

    # Если это сообщение после /book
    if context.user_data.get('booking_step') == 2:
        await handle_booking_time(update, context)
        return

    await update.message.reply_text(
        "Я не понял 😅\n\n"
        "Используй команды:\n"
        "/start — начало\n"
        "/book — запись на урок\n"
        "/help — справка\n"
        "/support — контакты"
    )

# ============ ГЛАВНАЯ ФУНКЦИЯ ============

async def main():
    """Запуск бота"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Диалоговый обработчик (сбор контактов)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            1: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('book', book_lesson))
    application.add_handler(CommandHandler('pay', pay))
    application.add_handler(CommandHandler('reschedule', reschedule))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('support', support))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    logger.info("🚀 Бот запущен!")
    logger.info("📬 Система рассылки активирована (дни 0, 1, 3, 5, 7)")

    # Запускаем систему рассылки в фоне
    asyncio.create_task(check_and_send_mailing(application))

    # Запуск
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
