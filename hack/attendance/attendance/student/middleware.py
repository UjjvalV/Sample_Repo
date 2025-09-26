import jwt
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from datetime import datetime
import json

User = get_user_model()

class JWTSessionMiddleware(MiddlewareMixin):
    """
    Middleware to handle JWT authentication for API requests
    """
    
    def process_request(self, request):
        # Skip JWT processing for certain paths
        skip_paths = [
            '/admin/',
            '/login/',
            '/signup/',
            '/static/',
            '/media/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
            
        # Check for JWT token in Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get('user_id')
                if user_id:
                    user = User.objects.get(id=user_id)
                    request.user = user
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
                pass
        
        # Check for JWT token in cookies
        elif 'jwt_token' in request.COOKIES:
            token = request.COOKIES['jwt_token']
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get('user_id')
                if user_id:
                    user = User.objects.get(id=user_id)
                    request.user = user
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
                pass
                
        return None
