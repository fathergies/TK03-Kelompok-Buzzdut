from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('add/', views.event_create, name='event_create'),
    path('<uuid:pk>/edit/', views.event_update, name='event_update'),
]
