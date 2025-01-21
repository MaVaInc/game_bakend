# # file: game/tests.py
#
# from django.test import TestCase
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from .models import PlayerState
# from .services import activate_altar
#
# User = get_user_model()
#
# class AltarActivationTest(TestCase):
#     def setUp(self):
#         self.user = User.objects.create_user(username='testuser', password='testpass')
#         self.player_state = PlayerState.objects.create(user=self.user)
#
#     def test_activate_altar_success(self):
#         success, message = activate_altar(self.player_state)
#         self.assertTrue(success)
#         self.assertIn("Алтарь активирован", message)
#         self.assertEqual(self.player_state.energy_altar, 1.0)
#
#     def test_activate_altar_too_early(self):
#         # Второй раз подряд (слишком рано)
#         activate_altar(self.player_state)
#         success, message = activate_altar(self.player_state)
#         self.assertFalse(success)
#         self.assertIn("Еще не прошло 6 часов", message)


import requests
import json

def test_auth():
    # URL вашего API
    url = 'https://anidapha.us/game/auth/'
    
    # Тестовые данные initData (пример)
    init_data = {
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps({
            "id": 123456789,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser"
        }),
        "auth_date": "1677649836",
        "hash": "hash_value"
    }

    # Подготовка данных для отправки
    payload = {
        'initData': init_data
    }

    # Отправка запроса
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        # Вывод информации о запросе
        print("Status Code:", response.status_code)
        print("Response Headers:", response.headers)
        print("Response Body:", response.text)
        
        # Попытка распарсить JSON
        if response.text:
            print("JSON Response:", response.json())
        else:
            print("Empty response")
            
    except requests.exceptions.RequestException as e:
        print("Request Error:", e)
    except json.JSONDecodeError as e:
        print("JSON Decode Error:", e)
        print("Raw Response:", response.text)

if __name__ == "__main__":
    test_auth()