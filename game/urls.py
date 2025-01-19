# file: game/urls.py

"""
Маршруты для приложения game, включая эндпоинты авторизации и управления username.
"""

from django.urls import path
from .views import (
    AltarActivateView,
    CampfireStartView,
    GatherFoodView,
    GatherWoodView,
    WaterfallActivateView,
    WaterfallBoostView,
    EnhancePlayerView,
)
from .views_auth import (
    auth_view,
    set_username,
    get_player_state
)
from .views import debug_view

urlpatterns = [
    # Авторизация и профиль
    path('auth/', auth_view, name='tg-auth'),
    path('set-username/', set_username, name='set-username'),
    path('player-state/', get_player_state, name='player-state'),

    # Игровые механики
    path('altar/activate/', AltarActivateView.as_view(), name='altar-activate'),
    path('campfire/start/', CampfireStartView.as_view(), name='campfire-start'),
    path('gather/food/', GatherFoodView.as_view(), name='gather-food'),
    path('gather/wood/', GatherWoodView.as_view(), name='gather-wood'),
    path('waterfall/activate/', WaterfallActivateView.as_view(), name='waterfall-activate'),
    path('waterfall/boost/', WaterfallBoostView.as_view(), name='waterfall-boost'),
    path('enhance/', EnhancePlayerView.as_view(), name='enhance-player'),
    path('debug/', debug_view, name='debug'),
]
