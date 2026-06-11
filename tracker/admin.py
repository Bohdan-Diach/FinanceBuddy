from django.contrib import admin

from .models import Achievement, Goal, Transaction, UserAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "condition_key", "icon")
    search_fields = ("title", "condition_key")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "date_earned")
    list_filter = ("date_earned",)
    search_fields = ("user__username", "achievement__title")


admin.site.register(Goal)
admin.site.register(Transaction)
