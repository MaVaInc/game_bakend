# file: game/views_auth.py

"""
Пример реализации авторизации через Telegram InitData, с проверкой хеша
и выдачей JWT-токенов (refresh/access) при успешной авторизации.
Все данные о пользователе и его состоянии (PlayerState) возвращаются в ответ.
"""

import urllib.parse
import json
import secrets
import hmac
import hashlib
import time

from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PlayerState, User  # Модель состояния игрока из приложения game


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_view(request):
    """
    Принимает initData из Telegram MiniApp (request.data['initData']),
    проверяет корректность хеша с помощью bot_token,
    регистрирует/авторизует пользователя и выдает JWT-токены.

    Если у пользователя ещё нет username (или он только что создан),
    возвращаем registered=False и предлагаем установить username.
    Иначе возвращаем registered=True и основные данные о пользователе и его состоянии.
    """
    init_data = request.data.get('initData')

    # Замените на свой реальный bot_token
    bot_token = 'REPLACE_WITH_YOUR_BOT_TOKEN'

    if not init_data:
        return JsonResponse({'success': False, 'message': 'No initData provided'}, status=400)

    if validate_init_data(init_data, bot_token):
        user_info_dict = urllib.parse.parse_qs(init_data)
        # user (JSON-строка с полями id, first_name, last_name, username и т.д.)
        try:
            user_info = json.loads(user_info_dict['user'][0])
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({
                'success': False, 
                'message': 'Некорректные данные пользователя'
            }, status=400)
        auth_date = int(user_info_dict['auth_date'][0])

        # Добавьте проверку срока действия auth_date сразу после его получения
        try:
            if time.time() - auth_date > 86400:
                return JsonResponse({
                    'success': False,
                    'message': 'Срок действия авторизации истек'
                }, status=401)
        except (KeyError, ValueError):
            return JsonResponse({
                'success': False,
                'message': 'Некорректная дата авторизации'
            }, status=400)

        # auth_date в человекочитаемом формате (необязательно)
        user_info['auth_date'] = timezone.datetime.fromtimestamp(auth_date).strftime('%Y-%m-%d %H:%M:%S')

        # По Telegram ID определяем пользователя
        telegram_id = user_info['id']
        user, created = User.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                # При создании — генерируем какое-то временное имя,
                # чтобы у пользователя было уникальное username в БД.
                'username': f"user_{secrets.token_hex(3)}",
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'photo_url': None,
                'auth_date': auth_date,
            }
        )

        # Если пользователь только что создан -> создаём PlayerState (если не создаётся сигналами)
        if created:
            PlayerState.objects.create(user=user)

        # Проверяем, есть ли у пользователя полноценный username
        if created or not user.username or user.username.startswith("user_"):
            # Предлагаем установить желаемый username
            return JsonResponse({
                'success': True,
                'registered': False,
                'welcome_message': "Welcome! Please choose a nickname.",
                # Предлагаем временный вариант
                'suggested_username': 'x_' + user.username,
            })
        else:
            # Пользователь уже имеет нормальный username
            refresh = RefreshToken.for_user(user)

            # Получаем состояние игрока (PlayerState), чтобы вернуть актуальные данные по ресурсам
            player_state = PlayerState.objects.filter(user=user).first()
            if not player_state:
                # Если почему-то нет PlayerState (например, не создался), то создаём
                player_state = PlayerState.objects.create(user=user)

            return JsonResponse({
                'success': True,
                'registered': True,
                'welcome_message': f"Welcome back, {user.username}!",
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),

                # Доп. поля из вашей User-модели (пример)
                'ton_balance': user.ton_balance,
                'platinum_balance': user.platinum_balance,
                'gold_balance': user.gold_balance,

                # Данные из PlayerState
                'energy_altar': player_state.energy_altar,
                'energy_fire': player_state.energy_fire,
                'energy_waterfall': player_state.energy_waterfall,
                'food': player_state.food,
                'wood': player_state.wood,
                'enhancements_count': player_state.enhancements_count,
            })
    else:
        return JsonResponse({'success': False, 'message': 'Invalid initData'}, status=401)


def validate_init_data(init_data: str, bot_token: str) -> bool:
    """
    Валидация init_data, присланных Telegram MiniApp:
    - Проверка хеша, сгенерированного HMAC.
    - Проверка срока давности (не более 24 часов).
    """
    try:
        init_data_dict = dict(urllib.parse.parse_qsl(init_data))
        hash_received = init_data_dict.pop('hash', None)

        # Формируем data_check_string в алфавитном порядке ключей
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(init_data_dict.items()))

        # Генерируем секретный ключ
        secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        # Вычисляем ожидаемый хеш
        hash_calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # Сравниваем
        if not hmac.compare_digest(hash_received, hash_calculated):
            return False

        # Проверяем срок давности (auth_date + 86400 секунд = 24 часа)
        auth_time = int(init_data_dict.get('auth_date', 0))
        if time.time() - auth_time > 86400:
            return False

        return True
    except Exception as e:
        print(f"Validation error: {e}")
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

    return JsonResponse({
        'success': True,
        'energy_altar': player_state.energy_altar,
        'energy_fire': player_state.energy_fire,
        'energy_waterfall': player_state.energy_waterfall,
        'food': player_state.food,
        'wood': player_state.wood,
        'enhancements_count': player_state.enhancements_count,
        # Если есть другие поля — добавьте
    })
