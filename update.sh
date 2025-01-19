#!/bin/bash
# Создайте файл update.sh на сервере

cd /var/www/game

# Получаем изменения из git
git pull

# Перезапускаем с новыми изменениями
docker-compose down
docker-compose build web
docker-compose up -d

# Применяем миграции
docker-compose exec web python manage.py migrate

# Собираем статику если нужно
docker-compose exec web python manage.py collectstatic --noinput

echo "Обновление завершено" 