import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from django.contrib.auth.decorators import login_required
from django.db import models, transaction, IntegrityError
from django.db.models import Q, Min
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render


from .forms import ArtistForm, EventForm, SeatForm, TicketCategoryForm, TicketForm
from .models import Artist, Event, Event_Artist, HasRelationship, Seat, Ticket, Ticket_Category
from ticketing.models import Venue

# =============================================================================
# Helper: Role Checks
# =============================================================================

def _is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


def _is_admin_or_organizer(user):
    return user.is_authenticated and user.role in ('ADMIN', 'ORGANIZER')

def _get_valid_event_organizer(request):
    UserModel = Event._meta.get_field('organizer').remote_field.model

    organizer = UserModel.objects.filter(pk=request.user.pk).first()
    if organizer:
        return organizer

    organizer = UserModel.objects.filter(username=request.user.username).first()
    if organizer:
        return organizer

    organizer = UserModel.objects.filter(role__in=['ADMIN', 'ORGANIZER']).first()
    if organizer:
        return organizer

    raise ValidationError('Organizer tidak ditemukan di tabel user yang dipakai Event.')

def _get_artist_from_post_value(artist_value):
    artist_value = str(artist_value).strip()

    if not artist_value:
        raise ValidationError('Artist wajib dipilih.')

    # Kalau yang terkirim UUID, cari pakai artist_id / pk
    try:
        artist_uuid = uuid.UUID(artist_value)
        artist = Artist.objects.filter(pk=artist_uuid).first()

        if artist:
            return artist

        artist = Artist.objects.filter(artist_id=artist_uuid).first()

        if artist:
            return artist
    except ValueError:
        pass

    # Kalau yang terkirim nama artist, cari pakai nama
    artist = Artist.objects.filter(name__iexact=artist_value).first()

    if artist:
        return artist

    raise ValidationError(f'Artist tidak ditemukan. Value yang terkirim: {artist_value}')


# =============================================================================
# Artist Views
# =============================================================================

def show_artists(request):
    """List all artists. Accessible by logged-in users."""
    artists = Artist.objects.all()
    total_artists = artists.count()
    unique_genres = artists.exclude(genre='').values('genre').distinct().count()
    # Count how many artists appear in at least one event
    from .models import Event_Artist
    artists_in_events = Event_Artist.objects.values('artist').distinct().count()

    context = {
        'artists': artists,
        'total_artists': total_artists,
        'unique_genres': unique_genres,
        'artists_in_events': artists_in_events,
        'user_role': getattr(request.user, 'role', None),
        'can_manage': _is_admin(request.user) if request.user.is_authenticated else False,
    }
    return render(request, 'ticketing/show_artists.html', context)


@login_required
def create_artist(request):
    """Create a new artist. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        form = ArtistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Artist created successfully!')
            return redirect('ticketing:show_artists')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ArtistForm()

    context = {
        'form': form,
        'form_title': 'Add New Artist',
        'submit_label': 'Create Artist',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/artist_form.html', context)


@login_required
def edit_artist(request, pk):
    """Edit an existing artist. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    artist = get_object_or_404(Artist, pk=pk)

    if request.method == 'POST':
        form = ArtistForm(request.POST, instance=artist)
        if form.is_valid():
            form.save()
            messages.success(request, f'Artist "{artist.name}" updated successfully!')
            return redirect('ticketing:show_artists')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ArtistForm(instance=artist)

    context = {
        'form': form,
        'form_title': f'Edit Artist: {artist.name}',
        'submit_label': 'Save Changes',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/artist_form.html', context)


@login_required
def delete_artist(request, pk):
    """Delete an artist. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    artist = get_object_or_404(Artist, pk=pk)

    if request.method == 'POST':
        name = artist.name
        artist.delete()
        messages.success(request, f'Artist "{name}" deleted successfully!')
        return redirect('ticketing:show_artists')

    context = {
        'object': artist,
        'object_type': 'Artist',
        'cancel_url': 'ticketing:show_artists',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/delete_confirm.html', context)

# =============================================================================
# Event Views
# =============================================================================

@login_required
def event_list(request):
    """R - Event: semua user login bisa melihat daftar event."""
    events = (
        Event.objects
        .select_related('venue', 'organizer')
        .prefetch_related('event_artists__artist', 'ticket_categories')
        .annotate(min_price=Min('ticket_categories__price'))
        .all()
        .order_by('start_date')
    )

    query = request.GET.get('q', '').strip()
    venue_filter = request.GET.get('venue', '').strip()
    artist_filter = request.GET.get('artist', '').strip()

    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__name__icontains=query) |
            Q(event_artists__artist__name__icontains=query)
        ).distinct()

    if venue_filter:
        events = events.filter(venue_id=venue_filter)

    if artist_filter:
        events = events.filter(event_artists__artist_id=artist_filter)

    total_events = events.count()
    scheduled_count = events.filter(status=Event.StatusChoices.SCHEDULED).count()
    ongoing_count = events.filter(status=Event.StatusChoices.ONGOING).count()

    context = {
        'events': events,
        'venues': Venue.objects.all().order_by('name'),
        'artists': Artist.objects.all().order_by('name'),
        'query': query,
        'venue_filter': venue_filter,
        'artist_filter': artist_filter,
        'total_events': total_events,
        'scheduled_count': scheduled_count,
        'ongoing_count': ongoing_count,
        'can_manage': _is_admin_or_organizer(request.user),
        'user_role': request.user.role,
    }

    return render(request, 'ticketing/event_list.html', context)


@login_required
def event_manage(request):
    """CU - Event: Admin melihat semua event, Organizer hanya event miliknya."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to access this page.")

    events = (
        Event.objects
        .select_related('venue', 'organizer')
        .prefetch_related('event_artists__artist')
        .all()
        .order_by('start_date')
    )

    if request.user.role == 'ORGANIZER':
        events = events.filter(organizer=request.user)

    query = request.GET.get('q', '').strip()
    venue_filter = request.GET.get('venue', '').strip()
    artist_filter = request.GET.get('artist', '').strip()

    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__name__icontains=query) |
            Q(event_artists__artist__name__icontains=query)
        ).distinct()

    if venue_filter:
        events = events.filter(venue_id=venue_filter)

    if artist_filter:
        events = events.filter(event_artists__artist_id=artist_filter)

    context = {
        'events': events,
        'venues': Venue.objects.all().order_by('name'),
        'artists': Artist.objects.all().order_by('name'),
        'query': query,
        'venue_filter': venue_filter,
        'artist_filter': artist_filter,
        'total_events': events.count(),
        'scheduled_count': events.filter(status=Event.StatusChoices.SCHEDULED).count(),
        'ongoing_count': events.filter(status=Event.StatusChoices.ONGOING).count(),
        'finished_count': events.filter(status=Event.StatusChoices.FINISHED).count(),
        'category_choices': Event.CategoryChoices.choices,
        'status_choices': Event.StatusChoices.choices,
        'can_manage': True,
        'user_role': request.user.role,
    }

    return render(request, 'ticketing/event_manage.html', context)


@login_required
def create_event(request):
    """Create Event: Admin dan Organizer."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method != 'POST':
        return redirect('ticketing:event_manage')

    try:
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        status = request.POST.get('status', '').strip()
        venue_id = request.POST.get('venue', '').strip()
        artist_id = request.POST.get('artist', '').strip()
        start_date = parse_datetime(request.POST.get('start_date', ''))
        end_date = parse_datetime(request.POST.get('end_date', ''))

        if not title:
            raise ValidationError('Judul acara wajib diisi.')

        if not venue_id:
            raise ValidationError('Venue wajib dipilih.')

        if not artist_id:
            raise ValidationError('Artist wajib dipilih.')

        if not start_date or not end_date:
            raise ValidationError('Tanggal mulai dan tanggal selesai wajib diisi.')

        if end_date <= start_date:
            raise ValidationError('Tanggal selesai harus setelah tanggal mulai.')

        venue = Venue.objects.get(pk=venue_id)
        artist = _get_artist_from_post_value(artist_id)

        organizer = _get_valid_event_organizer(request)

        with transaction.atomic():
            event = Event.objects.create(
                title=title,
                description=description,
                category=category,
                status=status,
                venue=venue,
                organizer=organizer,
                start_date=start_date,
                end_date=end_date,
            )

            Event_Artist.objects.create(
                event_id=event.id,
                artist_id=artist.artist_id,
                role='Main Performer'
            )

        messages.success(request, 'Event berhasil ditambahkan.')

    except Venue.DoesNotExist:
        messages.error(request, 'Event gagal ditambahkan: venue tidak ditemukan.')
    except ValidationError as e:
        messages.error(request, f'Event gagal ditambahkan: {e.messages[0]}')
    except IntegrityError as e:
        messages.error(request, f'Event gagal ditambahkan: database relation error ({str(e)}).')
    except Exception as e:
        messages.error(request, f'Event gagal ditambahkan: {str(e)}')

    return redirect('ticketing:event_manage')


@login_required
def update_event(request, pk):
    """Update Event: Admin semua event, Organizer hanya event miliknya."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    event = get_object_or_404(Event, pk=pk)

    if request.user.role == 'ORGANIZER' and event.organizer_id != request.user.id:
        return HttpResponseForbidden("Organizer hanya dapat mengubah event miliknya sendiri.")

    if request.method != 'POST':
        return redirect('ticketing:event_manage')

    try:
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        status = request.POST.get('status', '').strip()
        venue_id = request.POST.get('venue', '').strip()
        artist_id = request.POST.get('artist', '').strip()
        start_date = parse_datetime(request.POST.get('start_date', ''))
        end_date = parse_datetime(request.POST.get('end_date', ''))

        if not title:
            raise ValidationError('Judul acara wajib diisi.')

        if not venue_id:
            raise ValidationError('Venue wajib dipilih.')

        if not artist_id:
            raise ValidationError('Artist wajib dipilih.')

        if not start_date or not end_date:
            raise ValidationError('Tanggal mulai dan tanggal selesai wajib diisi.')

        if end_date <= start_date:
            raise ValidationError('Tanggal selesai harus setelah tanggal mulai.')

        venue = Venue.objects.get(pk=venue_id)
        artist = _get_artist_from_post_value(artist_id)

        event.title = title
        event.description = description
        event.category = category
        event.status = status
        event.venue = venue
        event.start_date = start_date
        event.end_date = end_date
        event.save()

        with transaction.atomic():
            event.title = title
            event.description = description
            event.category = category
            event.status = status
            event.venue = venue
            event.start_date = start_date
            event.end_date = end_date
            event.save()

            Event_Artist.objects.filter(event=event).delete()
            Event_Artist.objects.create(
                event_id=event.id,
                artist_id=artist.artist_id,
                role='Main Performer'
            )

        messages.success(request, 'Event berhasil diperbarui.')

    except Venue.DoesNotExist:
        messages.error(request, 'Event gagal diperbarui: venue tidak ditemukan.')
    except ValidationError as e:
        messages.error(request, f'Event gagal diperbarui: {e.messages[0]}')
    except Exception as e:
        messages.error(request, f'Event gagal diperbarui: {str(e)}')

    return redirect('ticketing:event_manage')

# =============================================================================
# Ticket Category Views
# =============================================================================

def show_ticket_categories(request):
    """List all ticket categories. Accessible by everyone."""
    categories = Ticket_Category.objects.select_related('tevent', 'tevent__venue').all()

    # Search by category name
    search_query = request.GET.get('q', '')
    if search_query:
        categories = categories.filter(category_name__icontains=search_query)

    # Filter by event
    event_filter = request.GET.get('event', '')
    if event_filter:
        categories = categories.filter(tevent__id=event_filter)

    # Sort
    categories = categories.order_by('tevent__title', 'category_name')

    # Stats
    total_categories = categories.count()
    total_quota = categories.aggregate(total=models.Sum('quota'))['total'] or 0
    max_price = categories.aggregate(max_p=models.Max('price'))['max_p'] or 0

    # Get all events for the dropdown filter
    all_events = Event.objects.all().order_by('title')

    context = {
        'categories': categories,
        'search_query': search_query,
        'event_filter': event_filter,
        'all_events': all_events,
        'total_categories': total_categories,
        'total_quota': total_quota,
        'max_price': max_price,
        'user_role': getattr(request.user, 'role', None),
        'can_manage': _is_admin_or_organizer(request.user) if request.user.is_authenticated else False,
    }
    return render(request, 'ticketing/show_ticket_categories.html', context)


@login_required
def create_ticket_category(request):
    """Create a new ticket category. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method == 'POST':
        form = TicketCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ticket category created successfully!')
            return redirect('ticketing:show_ticket_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TicketCategoryForm()

    context = {
        'form': form,
        'form_title': 'Add New Ticket Category',
        'submit_label': 'Create Category',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/ticket_category_form.html', context)


@login_required
def edit_ticket_category(request, pk):
    """Edit an existing ticket category. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    category = get_object_or_404(Ticket_Category, pk=pk)

    if request.method == 'POST':
        form = TicketCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Ticket category "{category.category_name}" updated successfully!')
            return redirect('ticketing:show_ticket_categories')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TicketCategoryForm(instance=category)

    context = {
        'form': form,
        'form_title': f'Edit Category: {category.category_name}',
        'submit_label': 'Save Changes',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/ticket_category_form.html', context)


@login_required
def delete_ticket_category(request, pk):
    """Delete a ticket category. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    category = get_object_or_404(Ticket_Category, pk=pk)

    if request.method == 'POST':
        name = category.category_name
        category.delete()
        messages.success(request, f'Ticket category "{name}" deleted successfully!')
        return redirect('ticketing:show_ticket_categories')

    context = {
        'object': category,
        'object_type': 'Ticket Category',
        'cancel_url': 'ticketing:show_ticket_categories',
        'user_role': request.user.role,
    }
    return render(request, 'ticketing/delete_confirm.html', context)

def _generate_ticket_code():
    return f"TKT-{uuid.uuid4().hex[:10].upper()}"


def _dummy_customer_name(seed):
    names = ['Budi Santoso', 'Siti Rahayu', 'Dina Pratiwi', 'Raka Wijaya']
    try:
        index = uuid.UUID(str(seed)).int % len(names)
    except ValueError:
        index = sum(ord(char) for char in str(seed)) % len(names)
    return names[index]


def _dummy_order_id_for_event(event_id):
    return uuid.uuid5(uuid.NAMESPACE_URL, f'tiktaktuk-order-{event_id}')


def _build_dummy_orders(events):
    orders = []
    for index, event in enumerate(events, start=1):
        order_id = _dummy_order_id_for_event(event.id)
        is_reserved = index % 2 == 1
        orders.append({
            'id': order_id,
            'code': f'ord_{index:03d}',
            'customer': _dummy_customer_name(order_id),
            'event': event,
            'is_reserved': is_reserved,
        })
    return orders


@login_required
def seat_list(request):
    """List seats with availability status. Manageable by Admin and Organizer."""
    seats = (
        Seat.objects
        .select_related('venue')
        .prefetch_related('seat_ticket')
        .order_by('venue__name', 'section', 'row_number', 'seat_number')
    )
    used_seat_ids = set(HasRelationship.objects.values_list('seat_id', flat=True))
    total_seats = seats.count()
    occupied_count = len(used_seat_ids)
    seat_rows = [
        {
            'seat': seat,
            'is_used': seat.seat_id in used_seat_ids,
        }
        for seat in seats
    ]

    context = {
        'seat_rows': seat_rows,
        'total_seats': total_seats,
        'available_count': total_seats - occupied_count,
        'occupied_count': occupied_count,
        'venues': Venue.objects.all().order_by('name'),
        'can_manage': _is_admin_or_organizer(request.user),
        'user_role': request.user.role,
    }
    return render(request, "ticketing/seat_list.html", context)


@login_required
def create_seat(request):
    """Create a seat. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method != 'POST':
        return redirect('ticketing:seat_list')

    form = SeatForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, 'Kursi berhasil ditambahkan.')
    else:
        messages.error(request, 'Kursi gagal ditambahkan. Pastikan semua field valid dan tidak duplikat.')
    return redirect('ticketing:seat_list')


@login_required
def edit_seat(request, pk):
    """Update a seat. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    seat = get_object_or_404(Seat, pk=pk)
    if request.method != 'POST':
        return redirect('ticketing:seat_list')

    form = SeatForm(request.POST, instance=seat)
    if form.is_valid():
        form.save()
        messages.success(request, 'Kursi berhasil diperbarui.')
    else:
        messages.error(request, 'Kursi gagal diperbarui. Pastikan semua field valid dan tidak duplikat.')
    return redirect('ticketing:seat_list')


@login_required
def delete_seat(request, pk):
    """Delete an unassigned seat. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    seat = get_object_or_404(Seat, pk=pk)
    if request.method != 'POST':
        return redirect('ticketing:seat_list')

    if HasRelationship.objects.filter(seat=seat).exists():
        messages.error(
            request,
            'Kursi ini sudah di-assign ke tiket dan tidak dapat dihapus. '
            'Hapus atau ubah tiket terlebih dahulu.'
        )
        return redirect('ticketing:seat_list')

    seat.delete()
    messages.success(request, 'Kursi berhasil dihapus.')
    return redirect('ticketing:seat_list')


@login_required
def ticket_list(request):
    """List tickets. Admin can update/delete; Admin and Organizer can create."""
    from orders.models import Order

    tickets = (
        Ticket.objects
        .select_related('tcategory', 'tcategory__tevent', 'tcategory__tevent__venue')
        .prefetch_related('seat_ticket__seat')
        .order_by('ticket_code')
    )
    orders_by_id = {}

    if request.user.is_authenticated and request.user.role == 'CUSTOMER':
        customer_orders = Order.objects.filter(customer=request.user)
        order_ids = list(customer_orders.values_list('id', flat=True))
        tickets = tickets.filter(torder_id__in=order_ids)
        orders_by_id = {order.id: order for order in customer_orders}

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    if query:
        tickets = tickets.filter(
            Q(ticket_code__icontains=query)
            | Q(tcategory__tevent__title__icontains=query)
            | Q(tcategory__category_name__icontains=query)
        )
    if status:
        tickets = tickets.filter(status=status)

    ticket_rows = []
    for ticket in tickets:
        relation = ticket.seat_ticket.all()[0] if ticket.seat_ticket.all() else None
        order_code = f"ord_{str(ticket.torder_id).split('-')[0]}"
        order = orders_by_id.get(ticket.torder_id)
        ticket_rows.append({
            'ticket': ticket,
            'seat': relation.seat if relation else None,
            'customer_name': order.customer.username if order else _dummy_customer_name(ticket.torder_id),
            'order_code': order_code,
        })

    total_tickets = tickets.count()
    active_count = tickets.filter(status=Ticket.StatusChoices.ACTIVE).count()
    used_count = tickets.filter(status=Ticket.StatusChoices.USED).count()
    cancelled_count = tickets.filter(status=Ticket.StatusChoices.CANCELLED).count()
    all_events = Event.objects.select_related('venue').order_by('title')
    categories = (
        Ticket_Category.objects
        .select_related('tevent', 'tevent__venue')
        .annotate(used_count=models.Count('tickets'))
        .order_by('tevent__title', 'category_name')
    )
    category_rows = [
        {
            'category': category,
            'is_full': category.used_count >= category.quota,
            'remaining': max(category.quota - category.used_count, 0),
        }
        for category in categories
    ]

    context = {
        'ticket_rows': ticket_rows,
        'dummy_orders': _build_dummy_orders(all_events),
        'category_rows': category_rows,
        'available_seats': Seat.objects.select_related('venue').exclude(
            seat_id__in=HasRelationship.objects.values_list('seat_id', flat=True)
        ).order_by('venue__name', 'section', 'row_number', 'seat_number'),
        'status_choices': Ticket.StatusChoices.choices,
        'selected_status': status,
        'query': query,
        'total_tickets': total_tickets,
        'active_count': active_count,
        'used_count': used_count,
        'cancelled_count': cancelled_count,
        'can_create': _is_admin_or_organizer(request.user),
        'can_manage': _is_admin(request.user),
        'user_role': request.user.role,
    }
    return render(request, "ticketing/ticket_list.html", context)


@login_required
def create_ticket(request):
    """Create a ticket. Admin and Organizer only."""
    if not _is_admin_or_organizer(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    if request.method != 'POST':
        return redirect('ticketing:ticket_list')

    data = request.POST.copy()
    if not data.get('ticket_code'):
        data['ticket_code'] = _generate_ticket_code()
    if not data.get('torder_id'):
        data['torder_id'] = str(uuid.uuid4())

    form = TicketForm(data)
    if form.is_valid():
        ticket = form.save()
        seat = form.cleaned_data.get('seat')
        if seat:
            HasRelationship.objects.create(ticket=ticket, seat=seat)
        messages.success(request, 'Tiket berhasil dibuat.')
    else:
        messages.error(request, 'Tiket gagal dibuat. Pastikan order, kategori, dan kursi valid.')
    return redirect('ticketing:ticket_list')


@login_required
def edit_ticket(request, pk):
    """Update ticket status and seat. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    ticket = get_object_or_404(Ticket, pk=pk)
    current_relation = HasRelationship.objects.filter(ticket=ticket).select_related('seat').first()
    current_seat = current_relation.seat if current_relation else None

    if request.method != 'POST':
        return redirect('ticketing:ticket_list')

    data = request.POST.copy()
    if not data.get('ticket_code'):
        data['ticket_code'] = ticket.ticket_code
    if not data.get('torder_id'):
        data['torder_id'] = str(ticket.torder_id)

    form = TicketForm(data, instance=ticket, current_seat=current_seat)
    if form.is_valid():
        ticket = form.save()
        selected_seat = form.cleaned_data.get('seat')
        HasRelationship.objects.filter(ticket=ticket).delete()
        if selected_seat:
            HasRelationship.objects.create(ticket=ticket, seat=selected_seat)
        messages.success(request, 'Tiket berhasil diperbarui.')
    else:
        messages.error(request, 'Tiket gagal diperbarui. Pastikan data valid.')
    return redirect('ticketing:ticket_list')


@login_required
def delete_ticket(request, pk):
    """Delete a ticket and release its assigned seat. Admin only."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("You do not have permission to perform this action.")

    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        ticket.delete()
        messages.success(request, 'Tiket berhasil dihapus.')
    return redirect('ticketing:ticket_list')
