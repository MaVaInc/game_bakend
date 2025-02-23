import json
import logging
import requests
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "https://anidapha.us"
TOKEN = None


def make_request(endpoint, data=None):
    """Выполняет POST запрос с авторизацией"""
    url = f"{BASE_URL}/game/{endpoint}/"
    headers = {
        'Content-Type': 'application/json'
    }
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'

    logger.debug(f"Making POST request to {url}")
    logger.debug(f"Headers: {headers}")

    response = requests.post(url, json=data, headers=headers)

    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response body: {response.text}")

    return response


def pretty_print(data):
    """Красивый вывод JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_game_flow():
    global TOKEN

    print("\n=== Начинаем тестирование игровых эндпоинтов ===")

    # 1. Аутентификация
    auth_data = {
        "initData": "user=%7B%22id%22%3A+942725235%2C+%22first_name%22%3A+%22PyTorch%22%2C+%22last_name%22%3A+%22Love%22%2C+%22username%22%3A+%22mavainc%22%2C+%22language_code%22%3A+%22ru%22%2C+%22is_premium%22%3A+true%2C+%22allows_write_to_pm%22%3A+true%2C+%22photo_url%22%3A+%22https%3A%2F%2Ft.me%2Fi%2Fuserpic%2F320%2FifVkHuoqKoec-tLyWu6fzwrej69yXrTXBDRfXjKGZW0.svg%22%7D&chat_instance=5919886264079046979&chat_type=sender&auth_date=1738108152&hash=d79fab30741fd36d41e66e07c1fdc2f34c18419771dfedfffb8cde71c78c9496"
    }

    logger.debug(f"Sending auth request with data: {auth_data['initData']}")

    try:
        response = make_request('auth', auth_data)
        response.raise_for_status()
        auth_data = response.json()
        TOKEN = auth_data['access_token']
        print(f"\nАвторизация успешна! Токен: {TOKEN[:20]}...")
    except Exception as e:
        logger.error("Authentication error", exc_info=True)
        return

    # 2. Проверка начального состояния
    print("\n=== Начальное состояние ===")
    response = make_request('player-state')
    pretty_print(response.json())

    # 3. Сбор дерева
    print("\n=== Сбор дерева ===")
    response = make_request('gather/wood')
    pretty_print(response.json())

    # Проверка после сбора дерева
    print("\n=== Проверка после сбора дерева ===")
    response = make_request('player-state')
    pretty_print(response.json())

    # 4. Розжиг костра
    print("\n=== Розжиг костра ===")
    response = make_request('campfire/start')
    pretty_print(response.json())

    # Проверка после розжига
    print("\n=== Проверка после розжига ===")
    response = make_request('player-state')
    pretty_print(response.json())

    # 5. Активация алтаря
    print("\n=== Активация алтаря ===")
    try:
        response = make_request('altar/activate')
        pretty_print(response.json())
    except Exception as e:
        print({
            "error": f"Request failed: {response.status_code}",
            "details": response.text
        })

    # Проверка после активации алтаря
    print("\n=== Проверка после активации алтаря ===")
    response = make_request('player-state')
    pretty_print(response.json())

    # 6. Сбор еды
    print("\n=== Сбор еды ===")
    response = make_request('gather/food')
    pretty_print(response.json())

    # Финальная проверка
    print("\n=== Финальная проверка ===")
    response = make_request('player-state')
    pretty_print(response.json())

    print("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    test_game_flow()