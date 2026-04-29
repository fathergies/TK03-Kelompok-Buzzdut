from django.urls import path

from . import views

app_name = 'ticketing'

urlpatterns = [
    # --- Artist URLs ---
    path('artist/', views.show_artists, name='show_artists'),
    path('artist/add/', views.create_artist, name='create_artist'),
    path('artist/<uuid:pk>/edit/', views.edit_artist, name='edit_artist'),
    path('artist/<uuid:pk>/delete/', views.delete_artist, name='delete_artist'),

    # --- Ticket Category URLs ---
    path('ticket-category/', views.show_ticket_categories, name='show_ticket_categories'),
    path('ticket-category/add/', views.create_ticket_category, name='create_ticket_category'),
    path('ticket-category/<uuid:pk>/edit/', views.edit_ticket_category, name='edit_ticket_category'),
    path('ticket-category/<uuid:pk>/delete/', views.delete_ticket_category, name='delete_ticket_category'),
]
