"""
URL configuration for attendance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from student import views as student_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', student_views.homepage_view, name='homepage'),  # Set homepage as root URL
    path('dashboard/', student_views.dashboard_redirect, name='dashboard'),  # Dashboard redirect at root level
    path('scan/', student_views.qr_scanner_view, name='qr_scanner'),  # QR Scanner at root level
    path('face-recognition/', student_views.face_recognition_view, name='face_recognition_root'),  # Face recognition at root level
    path('liveness-status/', student_views.get_liveness_status, name='liveness_status_root'),  # Liveness status
    path('reset-liveness/', student_views.reset_liveness, name='reset_liveness_root'),  # Reset liveness
    path('qr-expired/', student_views.qr_expired_view, name='qr_expired_root'),  # QR expired page
    path('qr-success/', student_views.qr_success_view, name='qr_success_root'),  # QR success page
    path('signup/', student_views.signup_view, name='root_signup'),
    path('login/', student_views.login_view, name='login'),  # Login at root level
    path('logout/', student_views.logout_view, name='logout'),  # Logout at root level
    path('student-dashboard/', student_views.student_dashboard, name='student_dashboard_root'),  # Student dashboard at root level
    path('attendance-analytics/', student_views.student_attendance_analytics, name='attendance_analytics_root'),  # Analytics at root level
    path("student/", include("student.urls")),  # Add student prefix for other student URLs
    path("faculty/", include("faculty.urls")),
    path("analytics/", include("faculty.urls")),  # Alias for analytics
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
