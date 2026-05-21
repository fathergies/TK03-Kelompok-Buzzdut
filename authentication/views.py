from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from datetime import datetime, timedelta
import uuid
import psycopg2


from basdat_tk03.db import fetch_one, execute_query, get_database_error_message
from basdat_tk03.auth import login_required

def register_select(request):
    if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'authentication/register_select.html')


def register_view(request, role):
    if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
        return redirect('core:dashboard')

    role_upper = role.upper()
    if role_upper not in ('CUSTOMER', 'ORGANIZER', 'ADMIN'):
        return redirect('authentication:register_select')

    role_labels = {
        'CUSTOMER': 'Pelanggan',
        'ORGANIZER': 'Penyelenggara',
        'ADMIN': 'Admin',
    }

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        raw_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number', '')

        if not all([username, email, raw_password, confirm_password, full_name]):
            messages.error(request, 'Semua field wajib diisi.')
        elif raw_password != confirm_password:
            messages.error(request, 'Password dan konfirmasi password tidak cocok.')
        else:
            try:
                validate_password(raw_password)
            except ValidationError as error:
                messages.error(request, ' '.join(error.messages))
                return render(request, 'authentication/register_form.html', {
                    'role': role_upper,
                    'role_label': role_labels.get(role_upper, role),
                })

            existing = fetch_one("SELECT email FROM USER_ACCOUNT WHERE email = %s;", [email])
            if existing:
                messages.error(request, 'Email sudah digunakan.')
            else:
                hashed_pw = make_password(raw_password)
                
                db_role_name = 'administrator' if role_upper == 'ADMIN' else role_upper
                
                # Retrieve role_id
                role_record = fetch_one("SELECT role_id FROM ROLE WHERE role_name ILIKE %s;", [db_role_name])
                if not role_record:
                    messages.error(request, 'Role tidak valid di sistem.')
                    return redirect('authentication:register_select')
                
                user_id = str(uuid.uuid4())
                try:
                    execute_query(
                        "INSERT INTO USER_ACCOUNT (user_id, username, email, password) VALUES (%s, %s, %s, %s);",
                        [user_id, username, email, hashed_pw]
                    )

                    execute_query(
                        "INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s);",
                        [role_record['role_id'], user_id]
                    )

                    if role_upper == 'CUSTOMER':
                        execute_query(
                            "INSERT INTO CUSTOMER (full_name, phone_number, user_id) VALUES (%s, %s, %s);",
                            [full_name, phone_number, user_id]
                        )
                    elif role_upper == 'ORGANIZER':
                        execute_query(
                            "INSERT INTO ORGANIZER (organizer_name, contact_email, user_id) VALUES (%s, %s, %s);",
                            [full_name, email, user_id]
                        )

                    messages.success(request, f'Akun berhasil dibuat! Silakan login.')
                    return redirect('authentication:login')
                except psycopg2.DatabaseError as error:
                    messages.error(request, get_database_error_message(error), extra_tags='trigger_error')
                except Exception as error:
                    messages.error(request, f'Registrasi gagal: {error}')

    context = {
        'role': role_upper,
        'role_label': role_labels.get(role_upper, role),
    }
    return render(request, 'authentication/register_form.html', context)


def login_view(request):
    if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Username dan password wajib diisi.')
        else:
            user_record = fetch_one("SELECT user_id, username, password FROM USER_ACCOUNT WHERE username = %s;", [username])
            
            if user_record and check_password(password, user_record['password']):
                # Valid login, create session
                session_id = str(uuid.uuid4())
                expires_at = datetime.now() + timedelta(days=7)
                
                execute_query(
                    "INSERT INTO USER_SESSION (session_id, user_id, expires_at) VALUES (%s, %s, %s);",
                    [session_id, user_record['user_id'], expires_at]
                )
                
                response = redirect('core:dashboard')
                response.set_cookie('session_id', session_id, expires=expires_at, httponly=True)
                messages.success(request, f"Selamat datang, {user_record['username']}!")
                return response
            else:
                messages.error(request, 'Username atau password salah.')

    return render(request, 'authentication/login.html')


def logout_view(request):
    session_id = request.COOKIES.get('session_id')
    response = redirect('authentication:login')
    
    if session_id:
        execute_query("UPDATE USER_SESSION SET is_active = FALSE WHERE session_id = %s;", [session_id])
        response.delete_cookie('session_id')
        
    messages.info(request, 'Anda telah logout.')
    return response


@login_required
def profile_view(request):
    if request.user.role not in ('CUSTOMER', 'ORGANIZER'):
        messages.error(request, 'Halaman profil hanya tersedia untuk pelanggan dan penyelenggara.')
        return redirect('core:dashboard')

    show_edit_modal = False

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            show_edit_modal = True
            if request.user.role == 'CUSTOMER':
                full_name = request.POST.get('full_name', '').strip()
                phone_number = request.POST.get('phone_number', '').strip()

                if not full_name or not phone_number:
                    messages.error(request, 'Nama lengkap dan nomor telepon wajib diisi.')
                else:
                    try:
                        execute_query(
                            "UPDATE CUSTOMER SET full_name = %s, phone_number = %s WHERE user_id = %s;",
                            [full_name, phone_number, request.user.pk]
                        )
                        messages.success(request, 'Profil berhasil diperbarui.')
                        return redirect('authentication:profile')
                    except psycopg2.DatabaseError as error:
                        messages.error(request, get_database_error_message(error), extra_tags='trigger_error')

            elif request.user.role == 'ORGANIZER':
                organizer_name = request.POST.get('organizer_name', '').strip()
                contact_email = request.POST.get('contact_email', '').strip()

                if not organizer_name or not contact_email:
                    messages.error(request, 'Nama organizer dan email kontak wajib diisi.')
                else:
                    try:
                        EmailValidator()(contact_email)
                        execute_query(
                            "UPDATE ORGANIZER SET organizer_name = %s, contact_email = %s WHERE user_id = %s;",
                            [organizer_name, contact_email, request.user.pk]
                        )
                        messages.success(request, 'Profil berhasil diperbarui.')
                        return redirect('authentication:profile')
                    except ValidationError:
                        messages.error(request, 'Format email kontak tidak valid.')
                    except psycopg2.DatabaseError as error:
                        messages.error(request, get_database_error_message(error), extra_tags='trigger_error')

        elif action == 'update_password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            user_record = fetch_one(
                "SELECT password FROM USER_ACCOUNT WHERE user_id = %s;",
                [request.user.pk]
            )

            if not old_password or not new_password or not confirm_password:
                messages.error(request, 'Semua field password wajib diisi.')
            elif not user_record or not check_password(old_password, user_record['password']):
                messages.error(request, 'Password lama tidak sesuai.')
            elif new_password != confirm_password:
                messages.error(request, 'Password baru dan konfirmasi password tidak cocok.')
            else:
                try:
                    validate_password(new_password)
                    execute_query(
                        "UPDATE USER_ACCOUNT SET password = %s WHERE user_id = %s;",
                        [make_password(new_password), request.user.pk]
                    )
                    messages.success(request, 'Password berhasil diperbarui.')
                    return redirect('authentication:profile')
                except ValidationError as error:
                    messages.error(request, ' '.join(error.messages))
                except psycopg2.DatabaseError as error:
                    messages.error(request, get_database_error_message(error), extra_tags='trigger_error')

    profile = get_profile_data(request.user)
    if not profile:
        messages.error(request, 'Data profil tidak ditemukan.')
        return redirect('core:dashboard')

    return render(request, 'authentication/profile.html', {
        'profile': profile,
        'show_edit_modal': show_edit_modal,
    })


def get_profile_data(user):
    if user.role == 'CUSTOMER':
        row = fetch_one(
            """
            SELECT ua.username, c.full_name, c.phone_number
            FROM USER_ACCOUNT ua
            JOIN CUSTOMER c ON ua.user_id = c.user_id
            WHERE ua.user_id = %s;
            """,
            [user.pk]
        )
        if row:
            row['role_label'] = 'Pelanggan'
            row['role_badge_class'] = 'bg-blue-100 text-blue-700'
            row['avatar_initial'] = (row['full_name'] or row['username'] or 'P')[:1].upper()
        return row

    if user.role == 'ORGANIZER':
        row = fetch_one(
            """
            SELECT ua.username, o.organizer_name, o.contact_email
            FROM USER_ACCOUNT ua
            JOIN ORGANIZER o ON ua.user_id = o.user_id
            WHERE ua.user_id = %s;
            """,
            [user.pk]
        )
        if row:
            row['role_label'] = 'Penyelenggara'
            row['role_badge_class'] = 'bg-purple-100 text-purple-700'
            row['avatar_initial'] = (row['organizer_name'] or row['username'] or 'P')[:1].upper()
        return row

    return None
