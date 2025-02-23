import traceback
import requests
import json
from typing import Dict, Any
import urllib.parse
import time
import hmac
import hashlib

def validate_init_data(init_data: str, bot_token: str) -> bool:
    try:
        print(f"\nValidating init_data: {init_data}")
        print(f"Using bot_token: {bot_token}")
        
        # Парсим данные
        init_data_dict = dict(urllib.parse.parse_qsl(init_data))
        print(f"Parsed init_data_dict: {json.dumps(init_data_dict, indent=2)}")
        
        # Получаем хэш
        hash_received = init_data_dict.pop('hash', None)
        print(f"Received hash: {hash_received}")
        
        # Создаем строку для проверки
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(init_data_dict.items())])
        print(f"Data check string:\n{data_check_string}")
        
        # Создаем секретный ключ
        secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        print(f"Secret key (hex): {secret_key.hex()}")
        
        # Вычисляем хэш
        hash_calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        print(f"Calculated hash: {hash_calculated}")
        
        # Проверяем время
        current_time = time.time()
        auth_time = int(init_data_dict.get('auth_date', 0))
        time_diff = current_time - auth_time
        print(f"Time check: current={current_time}, auth={auth_time}, diff={time_diff}")
        
        # Проверяем все условия
        hash_valid = hmac.compare_digest(hash_received, hash_calculated)
        time_valid = time_diff <= 86400
        
        print(f"Validation results: hash_valid={hash_valid}, time_valid={time_valid}")
        
        return hash_valid and time_valid
        
    except Exception as e:
        print(f"Validation error: {str(e)}")
        traceback.print_exc()  # Печатаем полный стек ошибки
        return False


class GameAPI:
    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url
        self.bot_token = '8093000259:AAE_TCJK6gu7_MC0t4fiHdllZGZEBEugROQ'
        self.access_token = None
        self.refresh_token = None

    def authenticate(self) -> Dict[str, Any]:
        """Аутентификация через Telegram"""
        try:
            # Формируем тестовые данные в точности как раньше
            user_data = {
                "id": 942725235,
                "first_name": "PyTorch",
                "last_name": "Love",
                "username": "mavainc",
                "language_code": "ru",
                "is_premium": True,
                "allows_write_to_pm": True,
                "photo_url": "https://t.me/i/userpic/320/ifVkHuoqKoec-tLyWu6fzwrej69yXrTXBDRfXjKGZW0.svg"
            }

            # Создаем словарь с данными
            init_data_dict = {
                "user": json.dumps(user_data),
                "chat_instance": "5919886264079046979",
                "chat_type": "sender",
                "auth_date": str(int(time.time()))
            }

            # Создаем строку для проверки
            data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(init_data_dict.items())])
            
            # Создаем секретный ключ и хэш
            secret_key = hmac.new(b'WebAppData', self.bot_token.encode(), hashlib.sha256).digest()
            hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            
            # Добавляем хэш к данным
            init_data_dict['hash'] = hash_value
            
            # Кодируем данные в URL-формат
            init_data = urllib.parse.urlencode(init_data_dict)

            # Отправляем запрос
            response = requests.post(
                f"{self.base_url}/game/auth/",
                headers={'Content-Type': 'application/json'},
                json={'initData': init_data}
            )

            if response.ok:
                data = response.json()
                if data.get('success'):
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    print(f"Токены получены: access={self.access_token[:20]}...")
                    return data
                return {"error": "Authentication failed"}
            return {"error": f"HTTP error: {response.status_code}"}

        except Exception as error:
            return {"error": str(error)}

    def _make_authorized_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Общий метод для авторизованных запросов"""
        if not self.access_token:
            print(f"Ошибка: отсутствует access_token")
            return {"error": "Not authenticated"}

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}/game/{endpoint}/"
        
        try:
            print(f"\n=== {method} {endpoint} ===")
            print(f"Request URL: {url}")
            print(f"Headers: {headers}")
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            else:
                response = requests.post(url, headers=headers, json=data if data else {})

            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

            if response.ok:
                return response.json()
            return {"error": f"Request failed: {response.status_code}"}

        except Exception as error:
            return {"error": str(error)}

    def get_player_state(self) -> Dict[str, Any]:
        """Получить состояние игрока"""
        return self._make_authorized_request('POST', 'player-state')

    def gather_food(self) -> Dict[str, Any]:
        """Собрать еду"""
        return self._make_authorized_request('POST', 'gather/food')

    def gather_wood(self) -> Dict[str, Any]:
        """Собрать дерево"""
        return self._make_authorized_request('POST', 'gather/wood')

    def activate_altar(self) -> Dict[str, Any]:
        """Активировать алтарь"""
        return self._make_authorized_request('POST', 'altar/activate')

    def start_campfire(self) -> Dict[str, Any]:
        """Разжечь костер"""
        return self._make_authorized_request('POST', 'campfire/start')

    def activate_waterfall(self) -> Dict[str, Any]:
        """Активировать водопад"""
        return self._make_authorized_request('POST', 'waterfall/activate')

    def boost_waterfall(self, resource_type: str) -> Dict[str, Any]:
        """Ускорить сбор ресурсов"""
        return self._make_authorized_request('POST', 'waterfall/boost', {'resource_type': resource_type})

    def enhance_player(self) -> Dict[str, Any]:
        """Улучшить игрока"""
        return self._make_authorized_request('POST', 'enhance')

    def set_username(self, username: str) -> Dict[str, Any]:
        """
        Установка username для нового пользователя
        """
        try:
            response = requests.post(
                f"{self.base_url}/set-username/",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {self.access_token}"
                },
                json={'username': username}
            )

            data = response.json()

            if not response.ok:
                raise Exception(data.get('message', 'Ошибка установки username'))

            return data

        except Exception as error:
            print(f"Ошибка установки username: {str(error)}")
            raise


def test_game_endpoints():
    try:
        print("=== Начинаем тестирование игровых эндпоинтов ===\n")
        
        api = GameAPI()
        auth_result = api.authenticate()
        
        if "error" in auth_result:
            print(f"Ошибка авторизации: {auth_result['error']}")
            return
            
        print(f"Авторизация успешна! Токен получен: {api.access_token[:20]}...")
        
        # Добавим паузу после авторизации
        time.sleep(1)
        
        # ... остальной код тестирования ...

    except Exception as error:
        print(f"Ошибка при тестировании: {str(error)}")


if __name__ == "__main__":
    test_game_endpoints()