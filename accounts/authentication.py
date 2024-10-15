from rest_framework.authentication import TokenAuthentication


class CustomTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        # Skip authentication for the registration endpoints
        if request.path in ["/api/register/", "/api/register-owner/"]:
            return None
        return super().authenticate(request)
