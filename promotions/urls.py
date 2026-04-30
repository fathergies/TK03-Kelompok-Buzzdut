from django.urls import path
from . import views

app_name = "promotions"

urlpatterns = [
    path("", views.promotion_list, name="list"),
    path("<uuid:promotion_id>/", views.promotion_detail, name="detail"),
]