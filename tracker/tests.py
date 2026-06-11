from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Achievement, Goal, Transaction, UserAchievement


class DashboardMonthlyHistoryTests(TestCase):
    def test_dashboard_includes_monthly_history_for_previous_months(self):
        def month_date(offset):
            today = date.today()
            year = today.year + (today.month - 1 + offset) // 12
            month = (today.month - 1 + offset) % 12 + 1
            return date(year, month, 15)

        Transaction.objects.create(amount=Decimal("1200.00"), transaction_type="income", category="Зарплата", date=month_date(0))
        Transaction.objects.create(amount=Decimal("300.00"), transaction_type="expense", category="Продукти", date=month_date(0))
        Transaction.objects.create(amount=Decimal("800.00"), transaction_type="income", category="Премія", date=month_date(-1))
        Transaction.objects.create(amount=Decimal("150.00"), transaction_type="expense", category="Транспорт", date=month_date(-1))

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("monthly_history", response.context)
        history = response.context["monthly_history"]
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[0]["income"], Decimal("1200.00"))
        self.assertEqual(history[0]["expense"], Decimal("300.00"))


class TransactionEditDeleteTests(TestCase):
    def test_edit_and_delete_transaction_work(self):
        transaction = Transaction.objects.create(amount=Decimal("100.00"), transaction_type="expense", category="Продукти", date=date.today())

        edit_response = self.client.post(
            reverse("edit_transaction", args=[transaction.pk]),
            {
                "amount": "150.50",
                "transaction_type": "expense",
                "category": "Транспорт",
                "date": transaction.date.isoformat(),
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal("150.50"))
        self.assertEqual(transaction.category, "Транспорт")

        delete_response = self.client.post(reverse("delete_transaction", args=[transaction.pk]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=transaction.pk).exists())


class MultiPageNavigationTests(TestCase):
    def test_core_pages_render(self):
        for view_name in ["dashboard", "analytics", "history", "goals", "profile"]:
            with self.subTest(view_name=view_name):
                response = self.client.get(reverse(view_name))
                self.assertEqual(response.status_code, 200)


class GoalEmptyStateTests(TestCase):
    def test_dashboard_shows_empty_state_when_no_goal_exists(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["goal"])
        self.assertContains(response, "У вас ще немає активної фінансової цілі")
        self.assertContains(response, "Встановити ціль")
        self.assertFalse(Goal.objects.exists())

    def test_dashboard_uses_goal_for_current_user(self):
        user = get_user_model().objects.create_user(username="alice", password="secret123")
        other_user = get_user_model().objects.create_user(username="bob", password="secret123")
        Goal.objects.create(user=other_user, name="Чужа ціль", target_amount=Decimal("3000.00"))
        current_goal = Goal.objects.create(user=user, name="Моя ціль", target_amount=Decimal("5000.00"))

        self.client.login(username="alice", password="secret123")
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["goal"], current_goal)
        self.assertEqual(response.context["goal_name"], "Моя ціль")


class AchievementTests(TestCase):
    def test_achievements_are_awarded_for_key_actions(self):
        user = get_user_model().objects.create_user(username="charlie", password="secret123")

        Transaction.objects.create(amount=Decimal("15000.00"), transaction_type="income", category="Премія", user=user)
        Goal.objects.create(user=user, name="Подорож", target_amount=Decimal("20000.00"))

        from .utils import check_and_award_achievements

        check_and_award_achievements(user)

        self.assertTrue(Achievement.objects.filter(condition_key="first_step").exists())
        self.assertTrue(Achievement.objects.filter(condition_key="goal_setter").exists())
        self.assertTrue(Achievement.objects.filter(condition_key="big_money").exists())
        self.assertEqual(UserAchievement.objects.filter(user=user).count(), 3)
        self.assertEqual(
            set(UserAchievement.objects.filter(user=user).values_list("achievement__condition_key", flat=True)),
            {"first_step", "goal_setter", "big_money"},
        )
