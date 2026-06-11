from django.urls import path

from .views import analytics_view, dashboard_view, delete_transaction, edit_transaction, goals_view, history_view, profile_view

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("analytics/", analytics_view, name="analytics"),
    path("history/", history_view, name="history"),
    path("goals/", goals_view, name="goals"),
    path("profile/", profile_view, name="profile"),
    path("transactions/<int:pk>/edit/", edit_transaction, name="edit_transaction"),
    path("transactions/<int:pk>/delete/", delete_transaction, name="delete_transaction"),
]
