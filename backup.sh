#!/bin/bash

# Создание бэкапа
backup_db() {
    docker-compose exec -T db pg_dump -U postgres game_db > "./backups/backup_$(date +%Y%m%d_%H%M%S).sql"
}

# Восстановление из бэкапа
restore_db() {
    if [ -z "$1" ]; then
        echo "Укажите файл бэкапа"
        exit 1
    }
    
    docker-compose exec -T db psql -U postgres game_db < "$1"
}

# Очистка старых бэкапов (оставляем последние 7 дней)
cleanup_old_backups() {
    find ./backups -name "backup_*.sql" -mtime +7 -delete
}

case "$1" in
    "backup")
        backup_db
        ;;
    "restore")
        restore_db "$2"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    *)
        echo "Использование: $0 {backup|restore|cleanup}"
        exit 1
        ;;
esac 