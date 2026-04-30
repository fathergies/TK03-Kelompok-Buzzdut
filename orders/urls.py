from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='list'),
    path('update/<uuid:pk>/', views.update_order, name='update'),
    path('delete/<uuid:pk>/', views.delete_order, name='delete'),
]