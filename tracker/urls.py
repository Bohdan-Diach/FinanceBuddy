from django.urls import path

from .views import dashboard, delete_transaction, edit_transaction, profile_view

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("profile/", profile_view, name="profile"),
    path("transactions/<int:pk>/edit/", edit_transaction, name="edit_transaction"),
    path("transactions/<int:pk>/delete/", delete_transaction, name="delete_transaction"),
]
