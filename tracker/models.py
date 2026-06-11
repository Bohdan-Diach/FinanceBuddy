from django.conf import settings
from django.db import models
from django.utils import timezone


class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals", null=True, blank=True)
    name = models.CharField(max_length=200, default="Накопичення на Ford Fusion")
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500000)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    CATEGORY_CHOICES = [
        ("Продукти", "Продукти"),
        ("Транспорт", "Транспорт"),
        ("Розваги", "Розваги"),
        ("Підписки", "Підписки"),
        ("Одяг", "Одяг"),
        ("Інше", "Інше"),
        ("Зарплата", "Зарплата"),
        ("Премія", "Премія"),
        ("Подарунок", "Подарунок"),
    ]
    TRANSACTION_TYPES = [
        ("income", "Дохід"),
        ("expense", "Витрата"),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} ({self.category})"
