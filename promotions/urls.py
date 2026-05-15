from django.urls import path

from . import views

app_name = "promotions"

urlpatterns = [
    path("", views.promotion_list, name="promotion_list"),
    path("", views.promotion_list, name="list"),
    path("add/", views.create_promotion, name="create_promotion"),
    path("create/", views.promotion_create, name="promotion_create"),
    path("<uuid:pk>/edit/", views.update_promotion, name="update_promotion"),
    path("<uuid:pk>/update/", views.promotion_update, name="promotion_update"),
    path("<uuid:pk>/delete/", views.delete_promotion, name="delete_promotion"),
    path("<uuid:pk>/delete/", views.promotion_delete, name="promotion_delete"),
]
