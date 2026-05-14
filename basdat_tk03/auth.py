import functools
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from basdat_tk03.db import fetch_one

class SimpleUser:
    """Mock user object to replace Django's CustomUser ORM model."""
    def __init__(self, user_id, username, email, role):
        self.pk = user_id
        self.user_id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.is_authenticated = True

    @property
    def is_anonymous(self):
        return False

def get_user_from_request(request):
    """Retrieve user from custom USER_SESSION table via cookie."""
    session_id = request.COOKIES.get('session_id')
    if not session_id:
        return None
        
    query = """
        SELECT u.user_id, u.username, u.email, r.role_name
        FROM USER_SESSION s
        JOIN USER_ACCOUNT u ON s.user_id = u.user_id
        JOIN ACCOUNT_ROLE ar ON u.user_id = ar.user_id
        JOIN ROLE r ON ar.role_id = r.role_id
        WHERE s.session_id = %s AND s.is_active = TRUE AND s.expires_at > CURRENT_TIMESTAMP
    """
    row = fetch_one(query, [session_id])
    if row:
        role_name = row['role_name'].upper()
        if role_name == 'ADMINISTRATOR':
            role_name = 'ADMIN'
        return SimpleUser(str(row['user_id']), row['username'], row['email'], role_name)
    return None

class RawSQLAuthMiddleware(MiddlewareMixin):
    """
    Middleware to replace django.contrib.auth.middleware.AuthenticationMiddleware.
    It reads the session_id cookie and sets request.user using raw SQL.
    """
    def process_request(self, request):
        user = get_user_from_request(request)
        if user:
            request.user = user

def login_required(view_func):
    """Custom decorator replacing django.contrib.auth.decorators.login_required"""
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request, 'user') and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Anda harus login terlebih dahulu.")
            return redirect('authentication:login')
    return wrapper
