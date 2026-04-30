from django.urls import path
from . import views

app_name = "promotions"

urlpatterns = [
    path("", views.promotion_list, name="list"),
    path("create/", views.promotion_create, name="promotion_create"),
    path("<int:pk>/update/", views.promotion_update, name="promotion_update"),
    path("<int:pk>/delete/", views.promotion_delete, name="promotion_delete"),
]