# file: game/services.py

"""
Обновлённый вариант, где все числовые значения и проценты вынесены в constants.py
и подключена логика из этого файла.
"""

import random
from datetime import timedelta
from django.utils import timezone
from .models import PlayerState
from . import constants as c  # Подключаем файл с константами
import logging
from django.db.models import F
from django.db import transaction
from typing import Tuple

logger = logging.getLogger(__name__)


@transaction.atomic
def activate_altar(player_state: PlayerState) -> tuple[bool, str, int]:
    """
    Активация алтаря:
    - Требует 1 энергии огня
    - Увеличивает энергию алтаря на 1
    """
    can_activate, cooldown = player_state.can_activate_altar()
    if not can_activate:
        return False, f"Нужно подождать {cooldown} секунд перед следующей активацией алтаря", cooldown

    if player_state.energy_fire < 1:
        return False, "Недостаточно энергии огня для активации алтаря", 0

    player_state.energy_fire = F('energy_fire') - 1
    player_state.energy_altar = F('energy_altar') + 1
    player_state.last_altar_activation = timezone.now()
    player_state.save()
    
    return True, "Алтарь успешно активирован", 0


def start_campfire(player_state: PlayerState):
    """
    Розжиг костра:
    - Требует 0.1 энергии огня, 0.1 энергии алтаря, 4 еды, 2 дерева
    - Горит 12 часов
    """
    if player_state.campfire_is_burning():
        return False, "Костёр уже горит."

    if player_state.energy_fire < c.CAMPFIRE_FIRE_ENERGY_COST or player_state.energy_altar < c.CAMPFIRE_ALTAR_ENERGY_COST:
        return False, "Недостаточно энергии (огня/алтаря) для розжига костра."

    if player_state.food < c.CAMPFIRE_FOOD_COST or player_state.wood < c.CAMPFIRE_WOOD_COST:
        return False, "Недостаточно ресурсов (еды/дерева) для розжига костра."

    # Списываем ресурсы
    player_state.energy_fire -= c.CAMPFIRE_FIRE_ENERGY_COST
    player_state.energy_altar -= c.CAMPFIRE_ALTAR_ENERGY_COST
    player_state.food -= c.CAMPFIRE_FOOD_COST
    player_state.wood -= c.CAMPFIRE_WOOD_COST

    player_state.last_campfire_start = timezone.now()
    player_state.save()
    return True, f"Костёр разожжён. Он будет гореть {c.CAMPFIRE_BURN_TIME_HOURS} часов."


@transaction.atomic
def gather_food(player_state: PlayerState) -> tuple[bool, str]:
    """
    Сбор еды:
    - Базовое количество 5 единиц
    - При активном водопаде удваивается
    """
    can_gather, cooldown = player_state.can_gather_food()
    if not can_gather:
        return False, f"Нужно подождать {cooldown} секунд перед следующим сбором еды"

    # Базовое количество еды
    food_amount = 5
    if player_state.waterfall_is_active():
        food_amount *= 2

    player_state.food = F('food') + food_amount
    player_state.last_food_gather = timezone.now()
    player_state.save()
    
    return True, f"Вы собрали {food_amount} единиц еды"


@transaction.atomic
def gather_wood(player_state: PlayerState) -> tuple[bool, str]:
    """
    Сбор дерева:
    - Требует 0.2 энергии огня
    - +3 дерева
    """
    can_gather, cooldown = player_state.can_gather_wood()
    if not can_gather:
        return False, f"Нужно подождать {cooldown} секунд перед следующим сбором дерева"

    if player_state.energy_fire < 0.2:
        return False, "Недостаточно энергии огня для сбора дерева"

    player_state.wood = F('wood') + c.GATHER_WOOD_AMOUNT
    player_state.energy_fire = F('energy_fire') - 0.2
    player_state.last_wood_gather = timezone.now()
    player_state.save()
    
    return True, f"Вы собрали {c.GATHER_WOOD_AMOUNT} единиц дерева"


def activate_waterfall(player_state: PlayerState):
    """
    Активация магического водопада:
    - Требует 0.25 энергии алтаря
    - Увеличивает энергию водопада на 0.2 (пример)
    """
    if player_state.energy_altar < c.WATERFALL_ACTIVATION_ALTAR_ENERGY_COST:
        return False, "Недостаточно энергии алтаря для активации водопада."

    player_state.energy_altar -= c.WATERFALL_ACTIVATION_ALTAR_ENERGY_COST
    player_state.energy_waterfall += c.WATERFALL_ENERGY_INCREASE_ON_ACTIVATION
    player_state.save()
    return True, f"Магический водопад активирован. Энергия водопада увеличена."


def waterfall_boost(player_state: PlayerState, resource_type: str):
    """
    Ускорение сбора ресурса на 85%, доступно раз в 24 часа:
    - Требует 0.35 энергии водопада
    - resource_type: 'food' или 'wood'
    """
    now = timezone.now()
    if player_state.last_waterfall_boost:
        if (now - player_state.last_waterfall_boost) < timedelta(hours=c.WATERFALL_BOOST_INTERVAL_HOURS):
            return False, "Ещё рано использовать ускорение водопада повторно."

    if player_state.energy_waterfall < c.WATERFALL_BOOST_WATERFALL_ENERGY_COST:
        return False, "Недостаточно энергии водопада для ускорения."

    player_state.energy_waterfall -= c.WATERFALL_BOOST_WATERFALL_ENERGY_COST
    player_state.last_waterfall_boost = now
    player_state.save()

    # На практике нужно где-то хранить статус "ускорения" для выбранного ресурса,
    # чтобы при сборе пищи/дерева учитывалась 85%-ная прибавка (или сокращение времени).
    # Здесь ограничимся сообщением:
    return True, f"Ускорение для {resource_type} включено: +{c.WATERFALL_BOOST_AMOUNT * 100}% к скорости сбора."


def enhance_player(player_state: PlayerState):
    """
    Усиление персонажа:
    - Базовые затраты: 0.15 энергии огня, алтаря и водопада
    - Каждое 10-е усиление: +1.5% к стоимости, но даёт больший прирост
    """
    next_enhancement = player_state.enhancements_count + 1

    # Базовые стоимости
    cost_fire = c.ENHANCE_FIRE_COST
    cost_altar = c.ENHANCE_ALTAR_COST
    cost_waterfall = c.ENHANCE_WATERFALL_COST

    # Каждое 10-е усиление дороже на 1.5%
    if next_enhancement % 10 == 0:
        cost_fire *= c.ENHANCE_COST_INCREASE_EVERY_10
        cost_altar *= c.ENHANCE_COST_INCREASE_EVERY_10
        cost_waterfall *= c.ENHANCE_COST_INCREASE_EVERY_10

    # Проверяем энергии
    if (
            player_state.energy_fire < cost_fire or
            player_state.energy_altar < cost_altar or
            player_state.energy_waterfall < cost_waterfall
    ):
        return False, "Недостаточно энергии для усиления."

    # Списываем
    player_state.energy_fire -= cost_fire
    player_state.energy_altar -= cost_altar
    player_state.energy_waterfall -= cost_waterfall

    # Прирост
    # Для примера: +0.0001% за обычные усиления, +0.001% за каждое 10-е
    if next_enhancement % 10 == 0:
        # player_state.efficiency += c.ENHANCE_TENTH_INCREASE  # Пример
        pass
    else:
        # player_state.efficiency += c.ENHANCE_BASE_INCREASE   # Пример
        pass

    player_state.enhancements_count = next_enhancement
    player_state.save()

    return True, f"Усиление проведено. Всего усилений: {next_enhancement}."


def can_gather_resource(player_state, resource_type):
    last_gathering = getattr(player_state, f'last_{resource_type}_gathering')
    if not last_gathering:
        return True
    cooldown = timezone.timedelta(minutes=5)  # настройте время как нужно
    return timezone.now() - last_gathering > cooldown


@transaction.atomic
def start_campfire(player_state):
    if player_state.wood < 1:
        return False, "Недостаточно дерева для розжига костра"
    
    player_state.wood = F('wood') - 1
    player_state.energy_fire = F('energy_fire') + 1
    player_state.last_campfire_start = timezone.now()
    player_state.save()
    return True, "Костер успешно разожжен"
