from django.contrib.auth import login
from account_v2.models import User

class AutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only attempt auto-login if the user is not already authenticated
        if hasattr(request, 'user') and not request.user.is_authenticated:
            # Get the first superuser (admin)
            user = User.objects.filter(is_superuser=True).first()
            if user:
                # Specify the backend to avoid authentication backend errors
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
        return self.get_response(request)
