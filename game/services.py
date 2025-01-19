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

logger = logging.getLogger(__name__)


def activate_altar(player_state: PlayerState):
    """
    Активация алтаря:
    - Раз в 6-8 часов (мы проверяем минимум 6 часов,
      верхняя граница 8 часов может применяться по желанию).
    - Энергия алтаря: +1 (если костёр горит) или +0.5 (если не горит).
    - 3% шанс увеличения энергии водопада.
    """
    try:
        now = timezone.now()
        last_activation = player_state.last_altar_activation

        if last_activation:
            time_diff = now - last_activation
            if time_diff < timedelta(hours=c.ALTAR_ACTIVATION_MIN_HOURS):
                return False, "Еще не прошло 6 часов с последней активации алтаря."

        # Определяем, горит ли костёр
        if player_state.campfire_is_burning():
            altar_energy_gain = c.ALTAR_ENERGY_GAIN_WHEN_BURNING
        else:
            altar_energy_gain = c.ALTAR_ENERGY_GAIN_WHEN_NOT_BURNING

        player_state.energy_altar += altar_energy_gain
        player_state.last_altar_activation = now

        # Шанс 3% на "магический водопад"
        if random.random() < c.ALTAR_WATERFALL_ACTIVATION_CHANCE:
            player_state.energy_waterfall += c.ALTAR_WATERFALL_ENERGY_INCREASE

        player_state.save()

        logger.info(f"Алтарь активирован для пользователя {player_state.user.id}")
        return True, f"Алтарь активирован. Получено {altar_energy_gain} ед. энергии алтаря."
    except Exception as e:
        logger.error(f"Ошибка при активации алтаря: {str(e)}")
        return False, "Произошла ошибка при активации алтаря"


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


def gather_food(player_state: PlayerState):
    """
    Сбор еды раз в 3 часа:
    - Требует 0.15 энергии огня
    - +5 еды
    """
    now = timezone.now()
    last_food_time = player_state.last_food_gathering

    if last_food_time and (now - last_food_time) < timedelta(hours=c.FOOD_GATHER_INTERVAL_HOURS):
        return False, "Слишком рано для сбора еды."

    if player_state.energy_fire < c.GATHER_FOOD_FIRE_ENERGY_COST:
        return False, "Недостаточно энергии огня для сбора еды."

    # Списываем энергию и добавляем еду
    player_state.energy_fire -= c.GATHER_FOOD_FIRE_ENERGY_COST
    player_state.food += c.GATHER_FOOD_AMOUNT

    player_state.last_food_gathering = now
    player_state.save()
    return True, f"Вы собрали {c.GATHER_FOOD_AMOUNT} единиц еды."


def gather_wood(player_state: PlayerState):
    """
    Сбор дерева раз в 6 часов:
    - Требует 0.2 энергии огня
    - +3 дерева
    """
    now = timezone.now()
    last_wood_time = player_state.last_wood_gathering

    if last_wood_time and (now - last_wood_time) < timedelta(hours=c.WOOD_GATHER_INTERVAL_HOURS):
        return False, "Слишком рано для сбора дерева."

    if player_state.energy_fire < c.GATHER_WOOD_FIRE_ENERGY_COST:
        return False, "Недостаточно энергии огня для сбора дерева."

    player_state.energy_fire -= c.GATHER_WOOD_FIRE_ENERGY_COST
    player_state.wood += c.GATHER_WOOD_AMOUNT

    player_state.last_wood_gathering = now
    player_state.save()
    return True, f"Вы собрали {c.GATHER_WOOD_AMOUNT} единиц дерева."


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
