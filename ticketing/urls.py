from django.urls import path

from . import views

app_name = 'ticketing'

urlpatterns = [
    # --- Artist URLs ---
    path('artist/', views.show_artists, name='show_artists'),
    path('artist/add/', views.create_artist, name='create_artist'),
    path('artist/<uuid:pk>/edit/', views.edit_artist, name='edit_artist'),
    path('artist/<uuid:pk>/delete/', views.delete_artist, name='delete_artist'),
    
    # --- Event URLs ---
    path('events/', views.event_list, name='event_list'),
    path('events/manage/', views.event_manage, name='event_manage'),
    path('events/add/', views.create_event, name='create_event'),
    path('events/<uuid:pk>/edit/', views.update_event, name='update_event'),

    # --- Ticket Category URLs ---
    path('ticket-category/', views.show_ticket_categories, name='show_ticket_categories'),
    path('ticket-category/add/', views.create_ticket_category, name='create_ticket_category'),
    path('ticket-category/<uuid:pk>/edit/', views.edit_ticket_category, name='edit_ticket_category'),
    path('ticket-category/<uuid:pk>/delete/', views.delete_ticket_category, name='delete_ticket_category'),

    # --- Seat URLs ---
    path('seats/', views.seat_list, name='seat_list'),
    path('seats/add/', views.create_seat, name='create_seat'),
    path('seats/<uuid:pk>/edit/', views.edit_seat, name='edit_seat'),
    path('seats/<uuid:pk>/delete/', views.delete_seat, name='delete_seat'),

    # --- Ticket URLs ---
    path('my-tickets/', views.ticket_list, name='ticket_list'),
    path('my-tickets/add/', views.create_ticket, name='create_ticket'),
    path('my-tickets/<uuid:pk>/edit/', views.edit_ticket, name='edit_ticket'),
    path('my-tickets/<uuid:pk>/delete/', views.delete_ticket, name='delete_ticket'),
]
