from decimal import Decimal

from django.db.models import Sum

from .models import Achievement, Goal, Transaction, UserAchievement


def _ensure_default_achievements():
    definitions = [
        {
            "title": "Перший крок",
            "description": "Додайте вашу першу транзакцію, щоб розпочати шлях до фінансової впевненості.",
            "icon": "✨",
            "condition_key": "first_step",
        },
        {
            "title": "Поставити ціль",
            "description": "Створіть фінансову ціль і почніть рухатися до неї з усвідомленістю.",
            "icon": "🎯",
            "condition_key": "goal_setter",
        },
        {
            "title": "Крупний дохід",
            "description": "Покажіть, що ваші доходи перевищили 10 000, і отримайте нагороду за прогрес.",
            "icon": "💸",
            "condition_key": "big_money",
        },
    ]

    for values in definitions:
        Achievement.objects.get_or_create(condition_key=values["condition_key"], defaults=values)

    return list(Achievement.objects.order_by("id"))


def check_and_award_achievements(user):
    if not user or not getattr(user, "is_authenticated", False):
        return []

    achievements = _ensure_default_achievements()
    awarded = []

    for achievement in achievements:
        if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            continue

        if achievement.condition_key == "first_step":
            qualifies = Transaction.objects.filter(user=user).exists()
        elif achievement.condition_key == "goal_setter":
            qualifies = Goal.objects.filter(user=user).exists()
        elif achievement.condition_key == "big_money":
            total_income = (
                Transaction.objects.filter(user=user, transaction_type="income").aggregate(total=Sum("amount"))["total"]
                or Decimal("0")
            )
            qualifies = total_income > Decimal("10000")
        else:
            qualifies = False

        if qualifies:
            UserAchievement.objects.create(user=user, achievement=achievement)
            awarded.append(achievement)

    return awarded
