# file: game/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
# file: api/models.py

from datetime import datetime
from django.db import models, transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Кастомный менеджер пользователя, позволяющий создавать
    обычных пользователей и суперпользователей с учётом
    нашего поля telegram_id.
    """

    def create_user(self, telegram_id, username, password=None, **extra_fields):
        if not telegram_id:
            raise ValueError('Telegram ID must be set')
        if not username:
            raise ValueError('Username must be set')

        extra_fields.setdefault('is_active', True)
        user = self.model(
            telegram_id=telegram_id,
            username=username,
            **extra_fields
        )
        # Пароль можете генерировать случайно, если не нужен логин по паролю
        user.set_password(password or self.make_random_password())

        # Сохраняем в транзакции
        with transaction.atomic():
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
    telegram_id = models.BigIntegerField(unique=True)
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
        Если auth_date - это целое число (Unix timestamp), преобразуем его в datetime.
        Приводим к aware datetime, если дата была наивной (без таймзоны).
        """
        if self.auth_date and isinstance(self.auth_date, int):
            self.auth_date = datetime.fromtimestamp(self.auth_date)

        if self.auth_date and timezone.is_naive(self.auth_date):
            self.auth_date = timezone.make_aware(self.auth_date)

        super().save(*args, **kwargs)

    def __str__(self):
        """
        При наличии имени/фамилии выводим их, иначе username.
        """
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username

    class Meta:
        indexes = [
            models.Index(fields=['telegram_id']),
        ]

class PlayerState(models.Model):
    """
    Модель хранит текущее состояние игрока:
    - Энергии (алтаря, огня, водопада)
    - Ресурсы (еда, дерево)
    - Метки времени для последней активации/розжига/сбора
    - Счетчик усилений
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Энергии
    energy_altar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    energy_fire = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    energy_waterfall = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Ресурсы
    food = models.IntegerField(default=0)
    wood = models.IntegerField(default=0)

    # Время последней активации алтаря
    last_altar_activation = models.DateTimeField(null=True)
    # Время последнего розжига костра
    last_campfire_start = models.DateTimeField(null=True)
    # Время последнего сбора еды
    last_food_gathering = models.DateTimeField(null=True)
    # Время последнего сбора дерева
    last_wood_gathering = models.DateTimeField(null=True)
    # Время последнего ускорения от водопада (если нужно)
    last_waterfall_boost = models.DateTimeField(null=True)

    # Количество усилений
    enhancements_count = models.IntegerField(default=0)

    # При желании можно хранить отдельное поле для общей эффективности
    # efficiency = models.FloatField(default=1.0)

    def __str__(self):
        return f"PlayerState for user: {self.user.username}"

    def campfire_is_burning(self) -> bool:
        """
        Проверяет, горит ли костёр: если прошло менее 12 часов с момента розжига.
        """
        if not self.last_campfire_start:
            return False
        time_diff = timezone.now() - self.last_campfire_start
        return time_diff.total_seconds() < 12 * 3600  # 12 часов в секундах

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['last_altar_activation']),
            models.Index(fields=['last_campfire_start']),
        ]


