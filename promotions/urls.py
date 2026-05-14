from django.urls import path
from . import views

app_name = "promotions"

urlpatterns = [
<<<<<<< HEAD
    path('', views.promotion_list, name='promotion_list'),
    path('add/', views.create_promotion, name='create_promotion'),
    path('<int:pk>/edit/', views.update_promotion, name='update_promotion'),
    path('<int:pk>/delete/', views.delete_promotion, name='delete_promotion'),
]
=======
    path("", views.promotion_list, name="list"),
    path("create/", views.promotion_create, name="promotion_create"),
    path("<int:pk>/update/", views.promotion_update, name="promotion_update"),
    path("<int:pk>/delete/", views.promotion_delete, name="promotion_delete"),
]
>>>>>>> 61b17254380ad6fb00b6f142da9d26deb3967168
