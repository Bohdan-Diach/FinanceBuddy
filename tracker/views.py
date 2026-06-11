from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from django import forms
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Achievement, Goal, Transaction, UserAchievement
from .utils import check_and_award_achievements


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["amount", "transaction_type", "category", "date"]
        labels = {
            "amount": "Сума",
            "transaction_type": "Тип",
            "category": "Категорія",
            "date": "Дата",
        }
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01", "class": "w-full min-h-[48px] rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-base text-slate-100 focus:border-cyan-400 focus:outline-none"}),
            "transaction_type": forms.Select(attrs={"class": "w-full min-h-[48px] rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-base text-slate-100 focus:border-cyan-400 focus:outline-none"}),
            "category": forms.Select(attrs={"class": "w-full min-h-[48px] rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-base text-slate-100 focus:border-cyan-400 focus:outline-none", "disabled": "disabled"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "w-full min-h-[48px] rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-base text-slate-100 focus:border-cyan-400 focus:outline-none"}),
        }


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["name", "target_amount"]
        labels = {
            "name": "Назва цілі",
            "target_amount": "Сума цілі",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full min-h-[48px] rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-base text-slate-100 focus:border-cyan-400 focus:outline-none"}),
            "target_amount": forms.NumberInput(attrs={"step": "0.01", "class": "w-full min-h-[48px] rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-base text-slate-100 focus:border-cyan-400 focus:outline-none"}),
        }


def _quantize(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _add_months(year, month, months):
    month_index = (year * 12) + (month - 1) + months
    new_year, new_month_index = divmod(month_index, 12)
    return new_year, new_month_index + 1


def _build_monthly_history(now, months=6):
    month_names = ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
    history = []
    current_year = now.year
    current_month = now.month

    for offset in range(months):
        target_year, target_month = _add_months(current_year, current_month, -offset)
        transactions = Transaction.objects.filter(date__year=target_year, date__month=target_month)
        income_total = transactions.filter(transaction_type="income").aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense_total = transactions.filter(transaction_type="expense").aggregate(total=Sum("amount"))["total"] or Decimal("0")
        history.append(
            {
                "label": f"{month_names[target_month - 1]} {target_year}",
                "income": income_total,
                "expense": expense_total,
            }
        )

    return history


def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, "Транзакцію оновлено.")
            return redirect("dashboard")
    else:
        form = TransactionForm(instance=transaction)

    return render(request, "tracker/edit_transaction.html", {"form": form, "transaction": transaction})


def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        transaction.delete()
        messages.success(request, "Транзакцію видалено.")

    return redirect("dashboard")


def profile_view(request):
    achievements = Achievement.objects.all()
    earned_achievement_ids = list(
        UserAchievement.objects.filter(user=request.user).values_list("achievement_id", flat=True)
    ) if request.user.is_authenticated else []

    return render(
        request,
        "tracker/profile.html",
        {
            "user": request.user,
            "achievements": achievements,
            "earned_achievement_ids": earned_achievement_ids,
        },
    )


def _get_dashboard_context(request, now=None):
    now = now or timezone.now()
    current_month = now.month
    current_year = now.year

    if request.user.is_authenticated:
        goal = Goal.objects.filter(user=request.user).first()
    else:
        goal = None

    transactions = Transaction.objects.all()[:5]
    total_income = Transaction.objects.filter(transaction_type="income").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_expense = Transaction.objects.filter(transaction_type="expense").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    balance = total_income - total_expense

    monthly_income = Transaction.objects.filter(transaction_type="income", date__month=current_month, date__year=current_year).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    monthly_expense = Transaction.objects.filter(transaction_type="expense", date__month=current_month, date__year=current_year).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    monthly_net_savings = monthly_income - monthly_expense

    expense_by_category = list(
        Transaction.objects.filter(transaction_type="expense", date__month=current_month, date__year=current_year)
        .values("category")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    expense_transactions = Transaction.objects.filter(transaction_type="expense", date__month=current_month, date__year=current_year)
    expense_count = expense_transactions.count()
    total_monthly_expenses = expense_transactions.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    average_expense = total_monthly_expenses / Decimal(expense_count) if expense_count else Decimal("0")

    insights = []
    if expense_by_category:
        biggest_category = max(expense_by_category, key=lambda item: item["total"])
        insights.append(
            f"Найбільше коштів цього місяця йде на {biggest_category['category']}. Можливо, тут можна трохи зекономити?"
        )

    if balance < 0 or monthly_net_savings <= 0:
        insights.append("Попередження: ваші витрати перевищують доходи. У такому темпі досягти цілі неможливо.")
    elif goal is not None and goal.target_amount > Decimal("0"):
        remaining_to_goal = max(goal.target_amount - balance, Decimal("0"))
        if remaining_to_goal <= 0:
            insights.append("Ви вже досягли своєї фінансової мети. Продовжуйте в тому ж темпі.")
        else:
            months_to_goal = int((remaining_to_goal / monthly_net_savings).to_integral_value(rounding=ROUND_CEILING)) if monthly_net_savings > 0 else 0
            target_year, target_month = _add_months(current_year, current_month, months_to_goal)
            month_names = ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
            insights.append(
                f"При поточному темпі заощаджень ви досягнете своєї цілі через {months_to_goal} місяців (орієнтовно у {month_names[target_month - 1]} {target_year})."
            )
    else:
        insights.append("Поки що немає витрат у цьому місяці. Додайте транзакцію, щоб побачити аналітику.")

    if expense_count:
        extra_savings = average_expense * Decimal("0.1") * Decimal(expense_count)
        insights.append(
            f"Ваш середній чек однієї витрати становить {_quantize(average_expense)} ₴. Зменшення цієї цифри всього на 10% дозволить заощадити додатково {_quantize(extra_savings)} ₴ до кінця місяця."
        )

    if goal is not None:
        progress_percentage = min(max((balance / goal.target_amount * Decimal("100")), Decimal("0")), Decimal("100")) if goal.target_amount > 0 else Decimal("0")
        remaining_to_goal = max(goal.target_amount - balance, Decimal("0"))
        goal_name = goal.name
        goal_target = goal.target_amount
    else:
        progress_percentage = Decimal("0")
        remaining_to_goal = Decimal("0")
        goal_name = ""
        goal_target = Decimal("0")

    return {
        "transactions": transactions,
        "balance": balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_history": _build_monthly_history(now),
        "expense_labels": [item["category"] for item in expense_by_category],
        "expense_values": [float(item["total"]) for item in expense_by_category],
        "insights": insights,
        "goal": goal,
        "goal_name": goal_name,
        "goal_target": goal_target,
        "progress_percentage": progress_percentage,
        "remaining_to_goal": remaining_to_goal,
    }


def dashboard_view(request):
    transaction_form = TransactionForm()

    if request.method == "POST":
        transaction_form = TransactionForm(request.POST)
        if transaction_form.is_valid():
            transaction = transaction_form.save(commit=False)
            if request.user.is_authenticated:
                transaction.user = request.user
            transaction.save()
            if request.user.is_authenticated:
                check_and_award_achievements(request.user)
            messages.success(request, "Транзакцію додано успішно.")
            return redirect("dashboard")

    context = _get_dashboard_context(request)
    context["transaction_form"] = transaction_form
    return render(request, "tracker/dashboard.html", context)


def analytics_view(request):
    context = _get_dashboard_context(request)
    return render(request, "tracker/analytics.html", context)


def history_view(request):
    transactions = Transaction.objects.all()
    return render(request, "tracker/history.html", {"transactions": transactions})


def goals_view(request):
    goal = Goal.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    goal_form = GoalForm(instance=goal) if goal is not None else GoalForm()

    if request.method == "POST":
        goal_form = GoalForm(request.POST, instance=goal)
        if goal_form.is_valid():
            saved_goal = goal_form.save(commit=False)
            if request.user.is_authenticated:
                saved_goal.user = request.user
            else:
                saved_goal.user = None
            saved_goal.save()
            goal = saved_goal
            if request.user.is_authenticated:
                check_and_award_achievements(request.user)
            messages.success(request, "Ціль успішно оновлено.")
            return redirect("goals")

    context = _get_dashboard_context(request)
    context.update({
        "goal": goal,
        "goal_form": goal_form,
        "goal_name": goal.name if goal else "",
        "goal_target": goal.target_amount if goal else Decimal("0"),
        "progress_percentage": min(max((context["balance"] / goal.target_amount * Decimal("100")), Decimal("0")), Decimal("100")) if goal and goal.target_amount > 0 else Decimal("0"),
        "remaining_to_goal": max(goal.target_amount - context["balance"], Decimal("0")) if goal else Decimal("0"),
    })
    return render(request, "tracker/goals.html", context)
