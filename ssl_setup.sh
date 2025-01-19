# Установка certbot
sudo apt install certbot

# Получение сертификата
sudo certbot certonly --webroot -w ./certbot/www -d your_domain.com

# Настройка автообновления сертификата
sudo certbot renew --dry-run 