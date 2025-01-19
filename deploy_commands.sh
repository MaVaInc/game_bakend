# На сервере:

# 1. Установка Docker и Docker Compose
sudo apt update
sudo apt install docker.io docker-compose

# 2. Клонирование репозитория
git clone your_repository_url
cd your_project

# 3. Создание .env файла
cat > .env << EOL
DJANGO_SETTINGS_MODULE=your_project_name.settings
DATABASE_URL=postgresql://postgres:password@db:5432/game_db
SECRET_KEY=your_secret_key_here
BOT_TOKEN=your_telegram_bot_token
DEBUG=0
ALLOWED_HOSTS=your_domain.com,localhost,127.0.0.1
EOL

# 4. Запуск проекта
sudo docker-compose up -d

# 5. Применение миграций
sudo docker-compose exec web python manage.py migrate

# 6. Сбор статических файлов
sudo docker-compose exec web python manage.py collectstatic --noinput 