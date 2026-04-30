from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Min, Q
from django.contrib import messages
from datetime import timedelta

from ticketing.models import Event, Ticket_Category, Venue, Artist, Event_Artist
from .forms import EventForm

def get_event_list_context(request):
    query = request.GET.get('q', '')
    venue_filter = request.GET.get('venue', '')
    artist_filter = request.GET.get('artist', '')

    # Fetch events with their lowest ticket price
    events = Event.objects.select_related('venue').annotate(
        min_price=Min('ticket_categories__price')
    ).prefetch_related('event_artists__artist', 'ticket_categories')

    if query:
        events = events.filter(
            Q(title__icontains=query) | Q(event_artists__artist__name__icontains=query)
        ).distinct()
    
    if venue_filter:
        events = events.filter(venue_id=venue_filter)
    
    if artist_filter:
        events = events.filter(event_artists__artist_id=artist_filter)

    events = events.order_by('start_date')

    venues = Venue.objects.all().order_by('name')
    artists = Artist.objects.all().order_by('name')

    return {
        'events': events,
        'venues': venues,
        'artists': artists,
        'query': query,
        'venue_filter': venue_filter,
        'artist_filter': artist_filter,
    }

def event_list(request):
    context = get_event_list_context(request)
    context['form'] = EventForm()
    context['show_modal'] = False
    return render(request, 'events/event_list.html', context)

@login_required
@transaction.atomic
def event_create(request):
    # Only Admin and Organizer can create events (Based on PRD)
    if request.user.role not in ['ADMIN', 'ORGANIZER']:
        messages.error(request, 'Hanya Admin dan Organizer yang dapat membuat acara.')
        return redirect('events:event_list')

    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.start_date = form.cleaned_data['start_datetime']
            event.end_date = event.start_date + timedelta(hours=3) # Default duration
            event.save()
            
            # Save artists
            artists = form.cleaned_data['artists']
            for artist in artists:
                Event_Artist.objects.create(event=event, artist=artist)
                
            # Process ticket categories
            category_names = request.POST.getlist('category_name[]')
            prices = request.POST.getlist('price[]')
            quotas = request.POST.getlist('quota[]')
            
            for i in range(len(category_names)):
                name = category_names[i].strip()
                price = prices[i]
                quota = quotas[i]
                if name and price and quota:
                    Ticket_Category.objects.create(
                        tevent=event,
                        category_name=name,
                        price=price,
                        quota=quota
                    )
            
            messages.success(request, 'Acara berhasil dibuat!')
            return redirect('events:event_list')
        else:
            context = get_event_list_context(request)
            context['form'] = form
            context['show_modal'] = True
            return render(request, 'events/event_list.html', context)
            
    return redirect('events:event_list')

@login_required
@transaction.atomic
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    # Check permissions
    if event.organizer != request.user and request.user.role != 'ADMIN':
        messages.error(request, 'Anda tidak memiliki akses untuk mengubah acara ini.')
        return redirect('events:event_list')

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.start_date = form.cleaned_data['start_datetime']
            event.end_date = event.start_date + timedelta(hours=3)
            event.save()
            
            # Update artists
            Event_Artist.objects.filter(event=event).delete()
            artists = form.cleaned_data['artists']
            for artist in artists:
                Event_Artist.objects.create(event=event, artist=artist)
                
            # Update ticket categories
            existing_cats = {c.category_name: c for c in event.ticket_categories.all()}
            category_names = request.POST.getlist('category_name[]')
            prices = request.POST.getlist('price[]')
            quotas = request.POST.getlist('quota[]')
            
            for i in range(len(category_names)):
                name = category_names[i].strip()
                price = prices[i]
                quota = quotas[i]
                if name and price and quota:
                    if name in existing_cats:
                        c = existing_cats[name]
                        c.price = price
                        c.quota = quota
                        c.save()
                    else:
                        Ticket_Category.objects.create(
                            tevent=event,
                            category_name=name,
                            price=price,
                            quota=quota
                        )
            
            messages.success(request, 'Acara berhasil diperbarui!')
            return redirect('events:event_list')
    else:
        initial_data = {
            'start_datetime': event.start_date,
            'artists': Artist.objects.filter(event_artists__event=event)
        }
        form = EventForm(instance=event, initial=initial_data)
        
    categories = event.ticket_categories.all()
        
    return render(request, 'events/event_form.html', {
        'title': 'Edit Acara', 
        'form': form,
        'event': event,
        'categories': categories
    })
