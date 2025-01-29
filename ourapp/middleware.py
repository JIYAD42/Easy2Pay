from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Define exempt URLs, including the admin URL
        exempt_urls = [reverse('login'), reverse('signup')]
        
        # Allow access to the admin page
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if the user is authenticated
        if not request.user.is_authenticated and request.path not in exempt_urls:
            messages.error(request, "Login required")
            return redirect('login')  # Redirect to login if not authenticated

        return self.get_response(request)