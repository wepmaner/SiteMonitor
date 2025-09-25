import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен Telegram бота
token = os.getenv('BOT_TOKEN')

# Настройки базы данных MySQL
host = os.getenv('DB_HOST')
port = int(os.getenv('DB_PORT'))
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')
admin_id = 312731525

# Настройки логирования
log_file = os.getenv('LOG_FILE', 'app.log')
log_level = os.getenv('LOG_LEVEL', 'INFO')
