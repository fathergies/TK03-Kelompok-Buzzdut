from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime, timedelta
import uuid


from basdat_tk03.db import fetch_one, execute_query

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
        username = request.POST.get('username')
        email = request.POST.get('email')
        raw_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number', '')

        if not all([username, email, raw_password, confirm_password, full_name]):
            messages.error(request, 'Semua field wajib diisi.')
        elif raw_password != confirm_password:
            messages.error(request, 'Password dan konfirmasi password tidak cocok.')
        else:
            # Cek duplikat username / email
            existing = fetch_one("SELECT username FROM USER_ACCOUNT WHERE username = %s OR email = %s;", [username, email])
            if existing:
                messages.error(request, 'Username atau email sudah digunakan.')
            else:
                hashed_pw = make_password(raw_password)
                
                db_role_name = 'administrator' if role_upper == 'ADMIN' else role_upper
                
                # Retrieve role_id
                role_record = fetch_one("SELECT role_id FROM ROLE WHERE role_name ILIKE %s;", [db_role_name])
                if not role_record:
                    messages.error(request, 'Role tidak valid di sistem.')
                    return redirect('authentication:register_select')
                
                # INSERT USER_ACCOUNT
                user_id = str(uuid.uuid4())
                execute_query(
                    "INSERT INTO USER_ACCOUNT (user_id, username, email, password) VALUES (%s, %s, %s, %s);",
                    [user_id, username, email, hashed_pw]
                )
                
                # INSERT ACCOUNT_ROLE
                execute_query(
                    "INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s);",
                    [role_record['role_id'], user_id]
                )

                # INSERT CUSTOMER / ORGANIZER
                if role_upper == 'CUSTOMER':
                    execute_query(
                        "INSERT INTO CUSTOMER (full_name, phone_number, user_id) VALUES (%s, %s, %s);",
                        [full_name, phone_number, user_id]
                    )
                elif role_upper == 'ORGANIZER':
                    execute_query(
                        "INSERT INTO ORGANIZER (organizer_name, contact_email, user_id) VALUES (%s, %s, %s);",
                        [full_name, email, user_id] # Using full_name as organizer_name
                    )

                messages.success(request, f'Akun berhasil dibuat! Silakan login.')
                return redirect('authentication:login')

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
