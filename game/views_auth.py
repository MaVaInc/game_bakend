# file: game/views_auth.py

"""
Пример реализации авторизации через Telegram InitData, с проверкой хеша
и выдачей JWT-токенов (refresh/access) при успешной авторизации.
Все данные о пользователе и его состоянии (PlayerState) возвращаются в ответ.
"""
import traceback
import urllib.parse
import json
import secrets
import hmac
import hashlib
import time
from datetime import datetime

from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PlayerState, User  # Модель состояния игрока из приложения game

@api_view(['POST'])
@permission_classes([AllowAny])
def auth_view(request):
    logger.info("=== Starting auth_view ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Request data: {request.data}")
    
    init_data = request.data.get('initData')
    bot_token = '8093000259:AAE_TCJK6gu7_MC0t4fiHdllZGZEBEugROQ'

    if not init_data:
        logger.error("No initData provided")
        return JsonResponse({
            'success': False, 
            'message': 'No initData provided'
        }, status=400)

    try:
        if validate_init_data(init_data, bot_token):
            user_info_dict = urllib.parse.parse_qs(init_data)
            try:
                user_info = json.loads(user_info_dict['user'][0])
                auth_date = int(user_info_dict['auth_date'][0])
            except (KeyError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing user info: {e}")
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid user info format'
                }, status=400)

            telegram_id = user_info['id']
            username = user_info.get('username', f"user_{telegram_id}")

            # Получаем или создаем пользователя
            user, created = User.objects.get_or_create(
                telegram_id=telegram_id,
                defaults={
                    'username': username,
                    'first_name': user_info.get('first_name', ''),
                    'last_name': user_info.get('last_name', ''),
                    'photo_url': user_info.get('photo_url'),
                    'auth_date': auth_date,
                }
            )

            # Обновляем данные пользователя
            if not created:
                user.auth_date = auth_date
                if user.username.startswith("user_"):
                    user.username = username
                user.save()

            # Создаем PlayerState если нужно
            if created:
                PlayerState.objects.create(user=user)

            # Проверяем username
            if created or not user.username or user.username.startswith("user_"):
                return JsonResponse({
                    'success': True,
                    'registered': False,
                    'welcome_message': "Welcome! Please choose a nickname.",
                    'suggested_username': 'x_' + user.username,
                })

            # Генерируем токены
            refresh = RefreshToken.for_user(user)
            player_state = PlayerState.objects.get(user=user)

            return JsonResponse({
                'success': True,
                'registered': True,
                'welcome_message': f"Welcome back, {user.username}!",
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'ton_balance': user.ton_balance,
                'platinum_balance': user.platinum_balance,
                'gold_balance': user.gold_balance,
                'energy_altar': player_state.energy_altar,
                'energy_fire': player_state.energy_fire,
                'energy_waterfall': player_state.energy_waterfall,
                'food': player_state.food,
                'wood': player_state.wood,
                'enhancements_count': player_state.enhancements_count,
            })
        else:
            logger.error("Invalid initData - validation failed")
            return JsonResponse({
                'success': False,
                'message': 'Invalid initData'
            }, status=401)

    except Exception as e:
        logger.error(f"Unexpected error in auth_view: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': 'Internal server error'
        }, status=500)

import logging

# Получаем логгер Django
logger = logging.getLogger('django')


def validate_init_data(init_data: str, bot_token: str) -> bool:
    try:
        logger.debug("=== Starting init_data validation ===")
        logger.debug(f"Raw init_data: {init_data}")
        logger.debug(f"Bot token: {bot_token}")

        # Парсим данные
        init_data_dict = dict(urllib.parse.parse_qsl(init_data))
        logger.debug(f"Parsed init_data_dict: {json.dumps(init_data_dict, indent=2)}")

        # Получаем хэш
        hash_received = init_data_dict.pop('hash', None)
        logger.debug(f"Received hash: {hash_received}")

        # Создаем строку для проверки
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(init_data_dict.items())])
        logger.debug(f"Data check string:\n{data_check_string}")

        # Создаем секретный ключ
        secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        logger.debug(f"Secret key (hex): {secret_key.hex()}")

        # Вычисляем хэш
        hash_calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        logger.debug(f"Calculated hash: {hash_calculated}")

        # Проверяем время
        current_time = time.time()
        auth_time = int(init_data_dict.get('auth_date', 0))
        time_diff = current_time - auth_time
        logger.debug(f"Time check: current={current_time}, auth={auth_time}, diff={time_diff}")

        # Проверяем все условия
        hash_valid = hmac.compare_digest(hash_received, hash_calculated)
        time_valid = time_diff <= 86400

        logger.debug(f"Validation results: hash_valid={hash_valid}, time_valid={time_valid}")

        return hash_valid and time_valid

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return False


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_username(request):
    """
    Устанавливает username текущему пользователю, если он ещё не установлен или нужно его сменить.
    Проверяем, что такой username не занят другими.
    """
    user = request.user
    new_username = request.data.get('username')

    if not new_username:
        return JsonResponse({'success': False, 'message': 'No username provided'}, status=400)

    # Проверяем, что такой username не занят
    if User.objects.filter(username=new_username).exclude(id=user.id).exists():
        return JsonResponse({'success': False, 'message': 'Username already taken'}, status=400)

    user.username = new_username
    user.save()
    return JsonResponse({'success': True, 'message': f'Username set to {new_username}'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_player_state(request):
    """
    Пример эндпоинта для получения текущего состояния игрока.
    """
    user = request.user
    player_state = PlayerState.objects.filter(user=user).first()
    if not player_state:
        # Если по каким-то причинам нет PlayerState — создаём
        player_state = PlayerState.objects.create(user=user)

    # Получаем все таймеры
    can_altar, altar_cooldown = player_state.can_activate_altar()
    can_food, food_cooldown = player_state.can_gather_food() 
    can_wood, wood_cooldown = player_state.can_gather_wood()
    can_waterfall, waterfall_cooldown = player_state.can_activate_waterfall()

    return JsonResponse({
        'success': True,
        'energy_altar': player_state.energy_altar,
        'energy_fire': player_state.energy_fire,
        'energy_waterfall': player_state.energy_waterfall,
        'food': player_state.food,
        'wood': player_state.wood,
        'enhancements_count': player_state.enhancements_count,
        'timers': {
            'altar': {
                'can_activate': can_altar,
                'cooldown_seconds': altar_cooldown
            },
            'food': {
                'can_gather': can_food,
                'cooldown_seconds': food_cooldown
            },
            'wood': {
                'can_gather': can_wood, 
                'cooldown_seconds': wood_cooldown
            },
            'waterfall': {
                'can_activate': can_waterfall,
                'cooldown_seconds': waterfall_cooldown
            },
            'campfire': {
                'is_burning': player_state.campfire_is_burning()
            }
        }
    })
