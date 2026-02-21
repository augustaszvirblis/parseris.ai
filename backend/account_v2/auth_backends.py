"""
Authentication backend that allows duplicate usernames.

Login form submits username + password. We first try matching user_id (so
user_id in URL or OAuth still works), then match by non-unique username
and password.
"""

from django.conf import settings
from django.contrib.auth.backends import ModelBackend

from account_v2.models import User


class UsernamePasswordBackend(ModelBackend):
    """
    Authenticate by username (display name) and password.
    Multiple users can share the same username; we return the first
    user whose password matches.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        username = username.strip()
        if not username:
            return None
        # Prefer match by user_id (e.g. OAuth, legacy, or login by id)
        try:
            user = User.objects.get(user_id=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        # Match by display username (non-unique); return first matching password
        for user in User.objects.filter(username=username):
            if user.check_password(password):
                return user
        return None
