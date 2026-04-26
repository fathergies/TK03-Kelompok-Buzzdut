from django.shortcuts import render, redirect, get_object_or_404
from .models import Venue
from .forms import VenueForm

def venue_list(request):
    venues = Venue.objects.all()
    return render(request, 'venue/venue_list.html', {'venues': venues})

def venue_create(request):
    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('venue_list')
    else:
        form = VenueForm()
    return render(request, 'venue/venue_form.html', {'form': form, 'title': 'Tambah Venue'})

def venue_update(request, venue_id):
    venue = get_object_or_404(Venue, venue_id=venue_id)
    if request.method == 'POST':
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            return redirect('venue_list')
    else:
        form = VenueForm(instance=venue)
    return render(request, 'venue/venue_form.html', {'form': form, 'title': 'Edit Venue'})

def venue_delete(request, venue_id):
    venue = get_object_or_404(Venue, venue_id=venue_id)
    if request.method == 'POST':
        venue.delete()
        return redirect('venue_list')
    return render(request, 'venue/venue_confirm_delete.html', {'venue': venue})
