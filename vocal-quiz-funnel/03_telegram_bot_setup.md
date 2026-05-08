# 🤖 TELEGRAM-БОТ: ИНСТРУКЦИЯ ЗАПУСКА

**Назначение:** Собирать контакты (имя + телефон) → выдавать подарок (5 упражнений)  
**Язык:** Python 3.8+  
**Зависимости:** python-telegram-bot 20+  

---

## ⚡ БЫСТРЫЙ СТАРТ (5 минут)

### Шаг 1: Получить BOT_TOKEN

1. Откройте Telegram
2. Найдите **@BotFather** (официальный бот Telegram)
3. Напишите `/start`
4. Нажмите `/newbot`
5. Следуйте инструкциям:
   - **Как назвать?** → `Vocal School Quiz Bot` (или своё имя)
   - **Как username?** → `vocal_school_bot_123` (уникальный, латиница)

6. **Получите TOKEN вида:**
   ```
   123456789:ABCDEfghIJKlmnopQRSTuvwxYZ
   ```
   Скопируйте этот токен!

### Шаг 2: Получить ADMIN_ID

1. Найдите бота **@userinfobot** в Telegram
2. Напишите `/start`
3. Вам выдаст `Your user ID: 123456789`
4. Скопируйте это число

### Шаг 3: Установить Python + зависимости

```bash
# Проверить Python (должна быть версия 3.8+)
python --version

# Установить библиотеку telegram-bot
pip install python-telegram-bot

# Или если используете poetry/pipenv:
poetry add python-telegram-bot
```

### Шаг 4: Настроить бот

Откройте файл `03_telegram_bot.py` и замените:

```python
# ДО:
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 123456789

# ПОСЛЕ (с вашими данными):
BOT_TOKEN = "123456789:ABCDEfghIJKlmnopQRSTuvwxYZ"
ADMIN_ID = 987654321
```

### Шаг 5: Запустить

```bash
# Из папки проекта:
python 03_telegram_bot.py

# Должно вывести:
# INFO:__main__:🚀 Бот запущен!
```

**Готово! Бот работает! ✅**

---

## 📱 ТЕСТИРОВАНИЕ БОТА

1. В Telegram найдите вашего бота по username (например, `@vocal_school_bot_123`)
2. Напишите `/start`
3. Введите имя
4. Введите телефон (или нажмите кнопку "Отправить номер")
5. **Получите подарок с ссылками на видео**
6. Вам (админу) придёт уведомление о новом контакте

---

## 🔧 НАСТРОЙКА ПОДАРКА

В функции `send_gift()` замените ссылки на свои:

### Вариант А: Видео на YouTube

```python
# Замените это:
"1️⃣ [Сирена (разогрев)](https://youtu.be/example1) — 3 мин\n"

# На это (ваша реальная ссылка):
"1️⃣ [Сирена (разогрев)](https://youtu.be/aBcDeFgHij) — 3 мин\n"
```

### Вариант Б: PDF из Google Drive

1. Загрузите PDF в Google Drive
2. Поделитесь (право "просмотр")
3. Скопируйте ID файла из ссылки
4. Подставьте:

```python
"[Скачать PDF](https://drive.google.com/uc?export=download&id=1a2b3c4d5e6f7g8h9i0j)"
```

### Вариант В: Видео в Telegram (напрямую)

```python
# Загрузьте видео в Telegram
# Отправьте боту, скопируйте file_id
# Используйте в коде:

await context.bot.send_video(
    chat_id=update.effective_chat.id,
    video="AgADAgADr6cxG...",  # file_id
    caption="🎁 Вот ваше упражнение!"
)
```

---

## 📊 ПРОСМОТР КОНТАКТОВ

Все контакты автоматически сохраняются в `contacts.json`:

```json
[
  {
    "id": 1,
    "name": "Анна",
    "phone": "+79991234567",
    "user_id": 123456789,
    "username": "anna_123",
    "date": "2026-05-08T18:30:45.123456"
  }
]
```

**Как использовать:**
- Откройте `contacts.json` в текстовом редакторе
- Экспортируйте в Excel (скопируйте в Google Sheets)
- Используйте для рассылки в Telegram-группу или отправки СМС

---

## 🌐 РАЗВЁРТЫВАНИЕ НА СЕРВЕР (для 24/7 работы)

Локально бот работает, только если ваш компьютер включен.  
Для 24/7 работы разместите на сервере:

### Вариант 1: Heroku (БЕСПЛАТНО, рекомендую)

```bash
# 1. Установите Heroku CLI
# 2. Создайте файл Procfile:
echo "worker: python 03_telegram_bot.py" > Procfile

# 3. Создайте requirements.txt:
echo "python-telegram-bot==20.3" > requirements.txt

# 4. Загрузьте на Heroku:
heroku login
heroku create your-bot-name
git push heroku main
```

### Вариант 2: Yandex Cloud / VPS ($5–15/месяц)

```bash
# Подключитесь по SSH
ssh root@your_server_ip

# Установите Python
apt update && apt install python3-pip

# Установите зависимости
pip3 install python-telegram-bot

# Скопируйте файл бота
scp 03_telegram_bot.py root@your_server_ip:/home/bot/

# Запустите через screen (чтоб работал в фоне):
screen -S telegram-bot
python3 /home/bot/03_telegram_bot.py
# Нажмите Ctrl+A, потом D (выход из screen)

# Проверка:
screen -ls
```

### Вариант 3: systemd (Linux сервер)

Создайте файл `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Vocal Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/bot
ExecStart=/usr/bin/python3 /home/bot/03_telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot  # Проверка
```

---

## 📞 ИНТЕГРАЦИЯ С КВИЗОМ

### Через Webhook (квиз → Telegram)

Если используете **Marquiz** или **Quiz Please**, можно настроить автоматическую отправку контактов в Telegram-бот.

**В боте добавьте endpoint для приема данных от квиза:**

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/quiz-webhook', methods=['POST'])
async def receive_quiz_data(request):
    """Получить данные из квиза"""
    data = request.json
    
    name = data.get('name')
    phone = data.get('phone')
    quiz_segment = data.get('segment')
    
    # Сохраняем
    save_contact(name, phone, user_id=None, username=quiz_segment)
    
    # Отправляем уведомление админу
    await app.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✅ Контакт из квиза:\n{name} | {phone}\nСегмент: {quiz_segment}"
    )
    
    return {"status": "ok"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

**URL webhook для квиза:** `https://your-domain.com/quiz-webhook`

---

## ⚠️ БЕЗОПАСНОСТЬ

### Защитить BOT_TOKEN

❌ **НИКОГДА не выкладывайте токен на GitHub!**

Используйте переменные окружения:

```python
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
```

Создайте файл `.env` (в .gitignore):

```
BOT_TOKEN=123456789:ABCDEfghIJKlmnopQRSTuvwxYZ
ADMIN_ID=987654321
```

Установите:

```bash
pip install python-dotenv
```

### Ограничить доступ к contacts.json

```bash
chmod 600 contacts.json  # Только владелец может читать/писать
```

---

## 🐛 ОТЛАДКА (что делать если не работает)

### Ошибка: "No module named 'telegram'"

```bash
pip install --upgrade python-telegram-bot
```

### Ошибка: "Invalid token"

- Проверьте, что токен скопирован правильно (без пробелов)
- Не истекла ли лицензия бота (переделайте в @BotFather)

### Ошибка: "Connection timeout"

- Проверьте интернет
- Если вы в России, может быть блокировка — используйте VPN или разместите на сервере

### Бот не отвечает на /start

- Проверьте логи: `tail bot_logs.log`
- Убедитесь, что бот запущен: `ps aux | grep telegram`

---

## 📈 МАСШТАБИРОВАНИЕ

Когда контактов будет 1000+:

1. **Перейти на базу данных:**
   - PostgreSQL или MongoDB (вместо JSON)
   - Код уже готов, просто замените `load_contacts()` / `save_contact()`

2. **Добавить распределённую обработку:**
   - Redis для кэша
   - Celery для рассылок

3. **Аналитика:**
   - Отслеживать, сколько людей прошли по ссылкам подарка
   - Сегментировать по типам клиентов

---

## ✅ ЧЕК-ЛИСТ ЗАПУСКА

- [ ] Получен BOT_TOKEN и ADMIN_ID
- [ ] Установлен Python 3.8+
- [ ] Установлена библиотека `python-telegram-bot`
- [ ] Заполнены значения в коде (BOT_TOKEN, ADMIN_ID)
- [ ] Тестирование: бот отвечает на `/start`
- [ ] Тестирование: контакт сохраняется в `contacts.json`
- [ ] Тестирование: админ получает уведомление
- [ ] Изменены ссылки на видео/PDF подарка
- [ ] Развернуто на сервер (если нужно 24/7)
- [ ] Интегрировано с квизом (если используется)

**Готово! Бот работает! 🚀**

