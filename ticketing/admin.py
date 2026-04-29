from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Artist, CustomUser, Event, Event_Artist, Ticket_Category, Venue


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'capacity')
    search_fields = ('name', 'city')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'organizer', 'category', 'status', 'start_date')
    list_filter = ('category', 'status')
    search_fields = ('title',)


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'genre')
    search_fields = ('name',)


@admin.register(Event_Artist)
class EventArtistAdmin(admin.ModelAdmin):
    list_display = ('event', 'artist', 'role')


@admin.register(Ticket_Category)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('tevent', 'category_name', 'price', 'quota')
    list_filter = ('tevent',)
