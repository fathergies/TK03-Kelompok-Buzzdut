import uuid

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from basdat_tk03.auth import login_required
from basdat_tk03.db import execute_query, fetch_all, fetch_one


def _promotion_payload(request):
    return {
        'code': request.POST.get('code', '').strip().upper(),
        'discount_type': request.POST.get('discount_type', '').strip(),
        'discount_value': request.POST.get('discount_value', '').strip(),
        'start_date': request.POST.get('start_date', '').strip(),
        'end_date': request.POST.get('end_date', '').strip(),
        'usage_limit': request.POST.get('usage_limit', '').strip(),
    }


def _validate_promotion_payload(payload, promotion_id=None):
    required_fields = {
        'code': 'Kode Promo wajib diisi.',
        'discount_type': 'Tipe Diskon wajib dipilih.',
        'discount_value': 'Nilai Diskon wajib diisi.',
        'start_date': 'Tanggal Mulai wajib diisi.',
        'end_date': 'Tanggal Berakhir wajib diisi.',
        'usage_limit': 'Batas Penggunaan wajib diisi.',
    }

    for field, error_message in required_fields.items():
        if not payload[field]:
            return error_message

    if payload['discount_type'] not in ['PERCENTAGE', 'NOMINAL']:
        return 'Tipe Diskon harus Persentase atau Nominal.'

    try:
        discount_value = float(payload['discount_value'])
    except ValueError:
        return 'Nilai Diskon harus berupa angka.'

    if discount_value <= 0:
        return 'Nilai Diskon harus lebih dari 0.'

    try:
        usage_limit = int(payload['usage_limit'])
    except ValueError:
        return 'Batas Penggunaan harus berupa bilangan bulat.'

    if usage_limit <= 0:
        return 'Batas Penggunaan harus lebih dari 0.'

    if payload['end_date'] < payload['start_date']:
        return 'Tanggal Berakhir harus sama dengan atau setelah Tanggal Mulai.'

    existing = fetch_one(
        "SELECT promotion_id FROM PROMOTION WHERE promo_code ILIKE %s",
        [payload['code']],
    )
    if existing and str(existing['promotion_id']) != str(promotion_id):
        return 'Kode Promo sudah digunakan.'

    return None


def promotion_list(request):
    search_query = request.GET.get('search', '')
    type_filter = request.GET.get('type', '')

    base_query = """
        SELECT p.*, COUNT(op.order_promotion_id) as used_count
        FROM PROMOTION p
        LEFT JOIN ORDER_PROMOTION op ON p.promotion_id = op.promotion_id
        WHERE 1=1
    """
    params = []

    if search_query:
        base_query += " AND p.promo_code ILIKE %s"
        params.append(f"%{search_query}%")
    if type_filter:
        base_query += " AND p.discount_type = %s"
        params.append(type_filter)

    base_query += " GROUP BY p.promotion_id ORDER BY p.start_date DESC, p.promo_code ASC"
    promos_raw = fetch_all(base_query, params)

    today = timezone.localdate()
    total_usage = 0
    total_persentase = 0

    for promo in promos_raw:
        promo['is_active_for_list'] = (
            str(promo['start_date']) <= str(today) <= str(promo['end_date'])
            and promo['used_count'] < promo['usage_limit']
        )
        promo['code'] = promo['promo_code']
        promo['pk'] = promo['promotion_id']

        total_usage += promo['used_count']
        if promo['discount_type'] == 'PERCENTAGE':
            total_persentase += 1

    class DummyForm:
        pass

    user_role = getattr(request.user, 'role', 'GUEST') if hasattr(request, 'user') and request.user else 'GUEST'

    return render(request, 'promotions/promotion_list.html', {
        'promos': promos_raw,
        'stats': {
            'total_promo': len(promos_raw),
            'total_usage': total_usage,
            'total_persentase': total_persentase,
        },
        'form': DummyForm(),
        'user_role': user_role,
        'search': search_query,
        'promo_type': type_filter,
        'can_manage': user_role == 'ADMIN',
    })


@login_required
def create_promotion(request):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat membuat promosi.')
        return redirect('promotions:promotion_list')

    if request.method == 'POST':
        payload = _promotion_payload(request)
        validation_error = _validate_promotion_payload(payload)
        if validation_error:
            messages.error(request, validation_error)
            return redirect('promotions:promotion_list')

        try:
            execute_query(
                "INSERT INTO PROMOTION (promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    str(uuid.uuid4()),
                    payload['code'],
                    payload['discount_type'],
                    payload['discount_value'],
                    payload['start_date'],
                    payload['end_date'],
                    payload['usage_limit'],
                ],
            )
            messages.success(request, 'Promosi berhasil dibuat.')
        except Exception as error:
            messages.error(request, f'Promosi gagal dibuat: {error}')

    return redirect('promotions:promotion_list')


@login_required
def update_promotion(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat mengubah promosi.')
        return redirect('promotions:promotion_list')

    if request.method == 'POST':
        payload = _promotion_payload(request)
        validation_error = _validate_promotion_payload(payload, promotion_id=pk)
        if validation_error:
            messages.error(request, validation_error)
            return redirect('promotions:promotion_list')

        try:
            execute_query(
                "UPDATE PROMOTION SET promo_code=%s, discount_type=%s, discount_value=%s, start_date=%s, end_date=%s, usage_limit=%s WHERE promotion_id=%s",
                [
                    payload['code'],
                    payload['discount_type'],
                    payload['discount_value'],
                    payload['start_date'],
                    payload['end_date'],
                    payload['usage_limit'],
                    pk,
                ],
            )
            messages.success(request, 'Promosi berhasil diperbarui.')
        except Exception as error:
            messages.error(request, f'Promosi gagal diperbarui: {error}')

    return redirect('promotions:promotion_list')


@login_required
def delete_promotion(request, pk):
    if request.user.role != 'ADMIN':
        messages.error(request, 'Hanya admin yang dapat menghapus promosi.')
        return redirect('promotions:promotion_list')

    if request.method == 'POST':
        try:
            execute_query("DELETE FROM PROMOTION WHERE promotion_id=%s", [pk])
            messages.success(request, 'Promosi berhasil dihapus.')
        except Exception as error:
            messages.error(request, f'Promosi gagal dihapus: {error}')

    return redirect('promotions:promotion_list')


promotion_create = create_promotion
promotion_update = update_promotion
promotion_delete = delete_promotion
