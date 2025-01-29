# file: game/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
# file: api/models.py

from datetime import datetime, timedelta
from django.db import models, transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    """
    Кастомный менеджер пользователя, позволяющий создавать
    обычных пользователей и суперпользователей с учётом
    нашего поля telegram_id.
    """

    def create_user(self, telegram_id, username=None, password=None, **extra_fields):
        if not telegram_id:
            raise ValueError('Telegram ID must be set')
            
        # Если username не передан, используем telegram_id
        if not username:
            username = f"user_{telegram_id}"
            
        extra_fields.setdefault('is_active', True)
        user = self.model(
            telegram_id=telegram_id,
            username=username,
            **extra_fields
        )
        user.set_password(password or self.make_random_password())
        user.save(using=self._db)
        return user

    def create_superuser(self, telegram_id, username, password=None, **extra_fields):
        """
        Создаёт суперпользователя. Пригодится для админки Django.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(
            telegram_id=telegram_id,
            username=username,
            password=password,
            **extra_fields
        )



class User(AbstractUser):
    """
    Кастомная модель пользователя, наследуемся от AbstractUser,
    чтобы переопределить некоторые поля и добавить telegram_id.

    В логике игры имя пользователя (username) может автоматически
    задаваться из initData или генерироваться, если нужно.
    """
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    username = models.CharField(max_length=150, unique=True)  # Переопределяем поле username
    photo_url = models.URLField(null=True, blank=True)
    auth_date = models.IntegerField(null=True)
    ton_balance = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    platinum_balance = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    gold_balance = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Используем кастомный менеджер
    objects = UserManager()

    # Поле USERNAME_FIELD указывает, что для аутентификации
    # мы используем username (из AbstractUser).
    USERNAME_FIELD = 'username'
    # Дополнительные обязательные поля при создании superuser
    REQUIRED_FIELDS = ['telegram_id']

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set'
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set'
    )

    def save(self, *args, **kwargs):
        """
        Переопределяем метод save, чтобы сохранять auth_date как число
        """
        super().save(*args, **kwargs)

    def __str__(self):
        """
        При наличии имени/фамилии выводим их, иначе username.
        """
        return f"{self.username} (TG: {self.telegram_id})"

    class Meta:
        indexes = [
            models.Index(fields=['telegram_id']),
        ]

class PlayerState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    energy_altar = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    energy_fire = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    energy_waterfall = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    food = models.IntegerField(default=0)
    wood = models.IntegerField(default=0)
    enhancements_count = models.IntegerField(default=0)
    
    # Добавляем новые поля для отслеживания времени
    last_wood_gather = models.DateTimeField(null=True, blank=True)
    last_food_gather = models.DateTimeField(null=True, blank=True)
    last_altar_activation = models.DateTimeField(null=True, blank=True)
    last_waterfall_activation = models.DateTimeField(null=True, blank=True)
    last_fire_activation = models.DateTimeField(null=True, blank=True)
    last_campfire_start = models.DateTimeField(null=True, blank=True)  # Добавили это поле

    def __str__(self):
        return f"PlayerState for {self.user.username}"

    def can_activate_altar(self) -> tuple[bool, int]:
        if not self.last_altar_activation:
            return True, 0
        time_passed = timezone.now() - self.last_altar_activation
        cooldown = timedelta(minutes=30)
        if time_passed >= cooldown:
            return True, 0
        return False, int((cooldown - time_passed).total_seconds())

    def can_gather_food(self) -> tuple[bool, int]:
        if not self.last_food_gather:
            return True, 0
        time_passed = timezone.now() - self.last_food_gather
        cooldown = timedelta(minutes=5)
        if time_passed >= cooldown:
            return True, 0
        return False, int((cooldown - time_passed).total_seconds())

    def can_gather_wood(self) -> tuple[bool, int]:
        if not self.last_wood_gather:
            return True, 0
        time_passed = timezone.now() - self.last_wood_gather
        cooldown = timedelta(minutes=5)
        if time_passed >= cooldown:
            return True, 0
        return False, int((cooldown - time_passed).total_seconds())

    def can_activate_waterfall(self) -> tuple[bool, int]:
        """Проверяет, можно ли активировать водопад"""
        cooldown = timedelta(minutes=10)
        if not self.last_waterfall_activation:
            return True, 0
        
        time_passed = timezone.now() - self.last_waterfall_activation
        if time_passed >= cooldown:
            return True, 0
        
        seconds_left = int((cooldown - time_passed).total_seconds())
        return False, seconds_left

    def save(self, *args, **kwargs):
        try:
            logger.info(f"Saving PlayerState for user {self.user}")
            logger.info(f"Current state: {self.__dict__}")
            super().save(*args, **kwargs)
            logger.info("PlayerState saved successfully")
        except Exception as e:
            logger.error(f"Error saving PlayerState: {str(e)}", exc_info=True)
            raise

    def campfire_is_burning(self) -> bool:
        """
        Проверяет, горит ли костёр: если прошло менее 12 часов с момента розжига.
        """
        if not self.last_campfire_start:
            return False
        time_diff = timezone.now() - self.last_campfire_start
        return time_diff.total_seconds() < 12 * 3600  # 12 часов в секундах

    def waterfall_is_active(self) -> bool:
        """Проверяет, активен ли водопад"""
        if not self.last_waterfall_activation:
            return False
        time_diff = timezone.now() - self.last_waterfall_activation
        return time_diff.total_seconds() < 3600  # 1 час в секундах

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['last_altar_activation']),
            models.Index(fields=['last_campfire_start']),
        ]


