from django.urls import path

from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_select, name='register_select'),
    path('register/<str:role>/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
