import os
import requests
from jose import jwt
from django.shortcuts import render, redirect
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Category, EmailTemplate
from .serializers import CategorySerializer, EmailTemplateSerializer


# Get Auth0 details from environment variables
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")


def login(request):
    """
    Renders the login page with a link to authenticate with Auth0.
    """
    return render(request, 'users/login.html')


def auth0_login(request):
    """
    Redirects the user to Auth0's login page.
    """
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK_URL,
        "response_type": "code",
        "scope": "openid profile email",
    }
    url = f"https://{AUTH0_DOMAIN}/authorize?{requests.compat.urlencode(params)}"
    return redirect(url)


def callback(request):
    """
    Handles the callback from Auth0, retrieves the JWT, and renders the user profile.
    """
    code = request.GET.get("code")
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URL,
    }

    # Exchange the authorization code for an ID token
    token_info = requests.post(token_url, json=token_payload).json()
    id_token = token_info.get("id_token")

    if id_token:
        # Retrieve Auth0's JWKS (JSON Web Key Set)
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks = requests.get(jwks_url).json()
        unverified_header = jwt.get_unverified_header(id_token)

        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }

        if rsa_key:
            try:
                # Decode the ID token to verify and extract user information
                claims = jwt.decode(
                    id_token,
                    rsa_key,
                    algorithms=["RS256"],
                    audience=CLIENT_ID,
                    issuer=f"https://{AUTH0_DOMAIN}/"
                )
                return render(request, 'users/profile.html', {
                    'user_name': claims.get('name'),
                    'user_email': claims.get('email')
                })
            except jwt.ExpiredSignatureError:
                return HttpResponse("Token expired.", status=401)
            except jwt.JWTClaimsError:
                return HttpResponse("Incorrect claims, please check the audience and issuer.", status=401)
            except Exception:
                return HttpResponse("Unable to parse authentication token.", status=400)
        else:
            return HttpResponse("Unable to find appropriate key.", status=400)
    else:
        return HttpResponse("Authentication failed", status=401)


def logout(request):
    """
    Logs the user out and redirects them to the homepage.
    """
    return_to = "http://127.0.0.1:8000/"
    logout_url = f"https://{AUTH0_DOMAIN}/v2/logout?client_id={CLIENT_ID}&returnTo={return_to}"
    return redirect(logout_url)


@csrf_exempt
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([AllowAny])
def template_operations(request, template_id=None):
    """
    Unified view for all template operations
    """
    if request.method == 'GET':
        if template_id:
            try:
                template = EmailTemplate.objects.get(id=template_id)
                serializer = EmailTemplateSerializer(template)
                return Response(serializer.data)
            except EmailTemplate.DoesNotExist:
                return Response(
                    {'error': 'Template not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            templates = EmailTemplate.objects.all().order_by('-created_at')
            serializer = EmailTemplateSerializer(templates, many=True)
            return Response(serializer.data)

    elif request.method == 'POST':
        print("Received data:", request.data)
        serializer = EmailTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        try:
            template = EmailTemplate.objects.get(id=template_id)
            serializer = EmailTemplateSerializer(template, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except EmailTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    elif request.method == 'DELETE':
        try:
            template = EmailTemplate.objects.get(id=template_id)
            template.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except EmailTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        




class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class EmailTemplateViewSet(viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer

    def get_queryset(self):
        queryset = EmailTemplate.objects.all()
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def set_category(self, request, pk=None):
        template = self.get_object()
        category_id = request.data.get('category_id')
        
        if category_id:
            category = get_object_or_404(Category, id=category_id)
            template.category = category
        else:
            template.category = None
            
        template.save()
        return Response(self.get_serializer(template).data)