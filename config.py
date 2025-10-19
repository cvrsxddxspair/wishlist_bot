import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Получаем токен из переменной окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    raise ValueError('TELEGRAM_TOKEN не найден. Проверьте .env файл')