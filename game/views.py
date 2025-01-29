# file: game/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.conf import settings
from rest_framework.throttling import UserRateThrottle
from .serializers import UserSerializer
from django.http import JsonResponse
import json
from django.db import transaction
from django.db.models import F
import logging

from .models import PlayerState
from .services import (
    activate_altar,
    start_campfire,
    gather_food,
    gather_wood,
    activate_waterfall,
    waterfall_boost,
    enhance_player,
)

logger = logging.getLogger(__name__)

class GameActionThrottle(UserRateThrottle):
    rate = '100/hour'

class AltarActivateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [GameActionThrottle]

    @transaction.atomic
    def post(self, request):
        try:
            logger.info("=== Starting AltarActivateView ===")
            logger.info(f"User: {request.user}")
            
            player_state = PlayerState.objects.select_for_update().get(user=request.user)
            logger.info(f"Current player state: {player_state.__dict__}")
            
            success, message, cooldown = activate_altar(player_state)
            logger.info(f"Altar activation result: success={success}, message={message}, cooldown={cooldown}")
            
            # Проверяем, что player_state был сохранен
            player_state.refresh_from_db()
            logger.info(f"Updated player state: {player_state.__dict__}")
            
            return Response({
                "success": success,
                "message": message,
                "cooldown": cooldown  # Время в секундах до следующей возможной активации
            })
            
        except PlayerState.DoesNotExist:
            logger.error(f"PlayerState not found for user {request.user}")
            return Response(
                {"success": False, "message": "Состояние игрока не найдено"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error in AltarActivateView: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": f"Внутренняя ошибка сервера: {str(e)}",
                "cooldown": 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampfireStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = start_campfire(player_state)
        return Response({"success": success, "message": message})


class GatherFoodView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            player_state = PlayerState.objects.select_for_update().get(user=request.user)
            success, message = gather_food(player_state)
            return Response({"success": success, "message": message})
        except PlayerState.DoesNotExist:
            return Response(
                {"success": False, "message": "Состояние игрока не найдено"},
                status=status.HTTP_404_NOT_FOUND
            )


class GatherWoodView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            player_state = PlayerState.objects.select_for_update().get(user=request.user)
            success, message = gather_wood(player_state)
            return Response({"success": success, "message": message})
        except PlayerState.DoesNotExist:
            return Response(
                {"success": False, "message": "Состояние игрока не найдено"},
                status=status.HTTP_404_NOT_FOUND
            )


class WaterfallActivateView(APIView):
    """
    Активировать магический водопад
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = activate_waterfall(player_state)
        return Response({"success": success, "message": message})


class WaterfallBoostView(APIView):
    """
    Ускорить сбор определённого ресурса (еда или дерево)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Ожидаем поле "resource_type" в теле запроса
        resource_type = request.data.get("resource_type")
        if resource_type not in ["food", "wood"]:
            return Response({"success": False, "message": "Неверный тип ресурса."})

        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = waterfall_boost(player_state, resource_type)
        return Response({"success": success, "message": message})


class EnhancePlayerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = enhance_player(player_state)
        return Response({"success": success, "message": message})

