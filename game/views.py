# file: game/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.conf import settings
from rest_framework.throttling import UserRateThrottle

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

class GameActionThrottle(UserRateThrottle):
    rate = '100/hour'

class AltarActivateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [GameActionThrottle]

    def post(self, request):
        try:
            player_state = get_object_or_404(PlayerState, user=request.user)
            success, message = activate_altar(player_state)
            return Response(
                {"success": success, "message": message},
                status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"success": False, "message": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CampfireStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = start_campfire(player_state)
        return Response({"success": success, "message": message})


class GatherFoodView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = gather_food(player_state)
        return Response({"success": success, "message": message})


class GatherWoodView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        player_state = get_object_or_404(PlayerState, user=request.user)
        success, message = gather_wood(player_state)
        return Response({"success": success, "message": message})


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
