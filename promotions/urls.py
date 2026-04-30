from django.urls import path
from . import views

app_name = "promotions"

urlpatterns = [
    path("", views.promotion_list, name="list"),
    path("create/", views.promotion_create, name="create"),
    path("<uuid:promotion_id>/update/", views.promotion_update, name="update"),
    path("<uuid:promotion_id>/delete/", views.promotion_delete, name="delete"),
]