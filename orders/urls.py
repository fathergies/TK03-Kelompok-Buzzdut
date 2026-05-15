from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
<<<<<<< HEAD
    path('', views.order_list, name='order_list'),
    path('checkout/<uuid:event_id>/', views.checkout, name='checkout'),
    path('<uuid:pk>/update/', views.update_order, name='update_order'),
    path('<uuid:pk>/delete/', views.delete_order, name='delete_order'),
]
=======
    path('', views.order_list, name='list'),
    path('checkout/<uuid:event_id>/', views.checkout, name='checkout'),
    path('update/<uuid:pk>/', views.update_order, name='update'),
    path('delete/<uuid:pk>/', views.delete_order, name='delete'),
]
>>>>>>> 61b17254380ad6fb00b6f142da9d26deb3967168
