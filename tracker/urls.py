from django.urls import path

from .views import dashboard, delete_transaction, edit_transaction

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("transactions/<int:pk>/edit/", edit_transaction, name="edit_transaction"),
    path("transactions/<int:pk>/delete/", delete_transaction, name="delete_transaction"),
]
