from django.urls import path
from . import views

app_name = 'promotions'
urlpatterns = [
    path('', views.promotion_list, name='promotion_list'),
    path('add/', views.create_promotion, name='create_promotion'),
    path('<int:pk>/edit/', views.update_promotion, name='update_promotion'),
    path('<int:pk>/delete/', views.delete_promotion, name='delete_promotion'),
]
