# file: game_backend/urls.py

"""game_backend URL Configuration"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('game/', include('game.urls')),  # Подключаем роуты приложения game
]
