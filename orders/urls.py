from django.urls import path
from . import views

app_name = 'orders'
urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('checkout/<uuid:event_id>/', views.checkout, name='checkout'),
    path('<uuid:pk>/update/', views.update_order, name='update_order'),
    path('<uuid:pk>/delete/', views.delete_order, name='delete_order'),
]
