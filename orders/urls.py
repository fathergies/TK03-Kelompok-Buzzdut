from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('', views.order_list, name='list'),
    path('checkout/<uuid:event_id>/', views.checkout, name='checkout'),
    path('<uuid:pk>/', views.order_detail, name='detail'),
    path('<uuid:pk>/update/', views.update_order, name='update_order'),
    path('update/<uuid:pk>/', views.update_order, name='update'),
    path('<uuid:pk>/delete/', views.delete_order, name='delete_order'),
    path('delete/<uuid:pk>/', views.delete_order, name='delete'),
]
