# file: game/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import PlayerState
from .services import activate_altar

User = get_user_model()

class AltarActivationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.player_state = PlayerState.objects.create(user=self.user)

    def test_activate_altar_success(self):
        success, message = activate_altar(self.player_state)
        self.assertTrue(success)
        self.assertIn("Алтарь активирован", message)
        self.assertEqual(self.player_state.energy_altar, 1.0)

    def test_activate_altar_too_early(self):
        # Второй раз подряд (слишком рано)
        activate_altar(self.player_state)
        success, message = activate_altar(self.player_state)
        self.assertFalse(success)
        self.assertIn("Еще не прошло 6 часов", message)
