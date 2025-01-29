from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import json
import hmac
import hashlib
import time
import urllib.parse

from .models import PlayerState, User
from . import constants as c

class GameTestCase(TestCase):
    def setUp(self):
        """Подготовка данных для каждого теста"""
        self.client = APIClient()
        
        # Создаем тестового пользователя
        self.user_data = {
            "id": 942725235,
            "first_name": "Test",
            "last_name": "User",
            "username": "test_user",
            "language_code": "ru",
            "is_premium": True,
            "allows_write_to_pm": True,
            "photo_url": "https://t.me/test.jpg"
        }
        
        # Создаем init_data для авторизации
        self.init_data_dict = {
            "user": json.dumps(self.user_data),
            "chat_instance": "5919886264079046979",
            "chat_type": "sender",
            "auth_date": str(int(time.time()))
        }
        
        # Создаем хэш для init_data
        self.bot_token = '8093000259:AAE_TCJK6gu7_MC0t4fiHdllZGZEBEugROQ'
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(self.init_data_dict.items())])
        secret_key = hmac.new(b'WebAppData', self.bot_token.encode(), hashlib.sha256).digest()
        hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        self.init_data_dict['hash'] = hash_value
        
        # Кодируем данные в URL-формат
        self.init_data = urllib.parse.urlencode(self.init_data_dict)

    def authenticate(self):
        """Вспомогательный метод для авторизации"""
        response = self.client.post(
            reverse('tg-auth'),
            {'initData': self.init_data},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access_token']}")
        return data

    def test_authentication(self):
        """Тест процесса аутентификации"""
        # Тест успешной аутентификации
        response = self.client.post(
            reverse('tg-auth'),
            {'initData': self.init_data},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)

        # Тест с неверным хэшем
        invalid_init_data = self.init_data.replace(self.init_data_dict['hash'], 'invalid_hash')
        response = self.client.post(
            reverse('tg-auth'),
            {'initData': invalid_init_data},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_player_state(self):
        """Тест получения состояния игрока"""
        self.authenticate()
        
        # Получаем начальное состояние
        response = self.client.post(reverse('player-state'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Проверяем наличие всех необходимых полей
        self.assertIn('energy_altar', data)
        self.assertIn('energy_fire', data)
        self.assertIn('energy_waterfall', data)
        self.assertIn('food', data)
        self.assertIn('wood', data)
        self.assertIn('enhancements_count', data)
        self.assertIn('timers', data)

    def test_gather_resources(self):
        """Тест сбора ресурсов"""
        self.authenticate()
        
        # Тест сбора еды
        response = self.client.post(reverse('gather-food'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Проверяем кулдаун
        response = self.client.post(reverse('gather-food'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('cooldown', data)
        
        # Тест сбора дерева
        response = self.client.post(reverse('gather-wood'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])

    def test_altar_activation(self):
        """Тест активации алтаря"""
        self.authenticate()
        
        # Получаем игрока
        player = PlayerState.objects.get(user__telegram_id=self.user_data['id'])
        player.energy_fire = 1
        player.save()
        
        # Тест активации
        response = self.client.post(reverse('altar-activate'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Проверяем кулдаун
        response = self.client.post(reverse('altar-activate'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('cooldown', data)

    def test_campfire(self):
        """Тест розжига костра"""
        self.authenticate()
        
        # Подготавливаем ресурсы
        player = PlayerState.objects.get(user__telegram_id=self.user_data['id'])
        player.wood = c.CAMPFIRE_WOOD_COST
        player.food = c.CAMPFIRE_FOOD_COST
        player.energy_fire = c.CAMPFIRE_FIRE_ENERGY_COST
        player.energy_altar = c.CAMPFIRE_ALTAR_ENERGY_COST
        player.save()
        
        # Тест розжига
        response = self.client.post(reverse('campfire-start'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Проверяем, что костер горит
        player.refresh_from_db()
        self.assertTrue(player.campfire_is_burning())

    def test_waterfall(self):
        """Тест водопада"""
        self.authenticate()
        
        # Подготавливаем энергию алтаря
        player = PlayerState.objects.get(user__telegram_id=self.user_data['id'])
        player.energy_altar = c.WATERFALL_ACTIVATION_ALTAR_ENERGY_COST
        player.save()
        
        # Тест активации
        response = self.client.post(reverse('waterfall-activate'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Подготавливаем энергию водопада для буста
        player.refresh_from_db()
        player.energy_waterfall = c.WATERFALL_BOOST_WATERFALL_ENERGY_COST
        player.save()
        
        # Тест буста
        response = self.client.post(
            reverse('waterfall-boost'),
            {'resource_type': 'food'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])

    def test_enhance_player(self):
        """Тест улучшения игрока"""
        self.authenticate()
        
        # Подготавливаем энергию
        player = PlayerState.objects.get(user__telegram_id=self.user_data['id'])
        player.energy_fire = c.ENHANCE_FIRE_COST
        player.energy_altar = c.ENHANCE_ALTAR_COST
        player.energy_waterfall = c.ENHANCE_WATERFALL_COST
        player.save()
        
        # Тест улучшения
        response = self.client.post(reverse('enhance-player'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Проверяем счетчик улучшений
        player.refresh_from_db()
        self.assertEqual(player.enhancements_count, 1)

    def test_resource_limits(self):
        """Тест лимитов ресурсов"""
        self.authenticate()
        player = PlayerState.objects.get(user__telegram_id=self.user_data['id'])
        
        # Тест превышения лимитов
        max_tests = [
            ('food', 999999),
            ('wood', 999999),
            ('energy_altar', 999.99),
            ('energy_fire', 999.99),
            ('energy_waterfall', 999.99)
        ]
        
        for resource, value in max_tests:
            setattr(player, resource, value)
            try:
                player.save()
                self.fail(f"Should not allow {resource} value of {value}")
            except:
                pass

    def test_cooldowns(self):
        """Тест системы кулдаунов"""
        self.authenticate()
        player = PlayerState.objects.get(user__telegram_id=self.user_data['id'])
        
        # Тест кулдауна сбора еды
        response = self.client.post(reverse('gather-food'))
        self.assertTrue(response.json()['success'])
        
        response = self.client.post(reverse('gather-food'))
        self.assertFalse(response.json()['success'])
        
        # Симулируем прошествие времени
        player.last_food_gather = timezone.now() - timedelta(minutes=3)
        player.save()
        
        response = self.client.post(reverse('gather-food'))
        self.assertTrue(response.json()['success'])