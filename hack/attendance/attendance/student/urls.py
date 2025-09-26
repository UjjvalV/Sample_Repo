from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.homepage_view, name="home"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
      path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
   
    path("logout/", views.logout_view, name="logout"),
     path("generate-faculty-code/", views.generate_faculty_code, name="generate_faculty_code"),
    path("scan/", views.qr_scanner_view, name="qr_scanner"),
    path("qr-expired/", views.qr_expired_view, name="qr_expired"),
    path("qr-success/", views.qr_success_view, name="qr_success"),
    path("face-recognition/", views.face_recognition_view, name="face_recognition"),
    path("liveness-status/", views.get_liveness_status, name="liveness_status"),
    path("reset-liveness/", views.reset_liveness, name="reset_liveness"),
    path("courses/", views.student_courses, name="student_courses"),
    path("attendance-analytics/", views.student_attendance_analytics, name="student_attendance_analytics"),
    path("test-face-encoding/", views.test_face_encoding_view, name="test_face_encoding"),
    path("debug-attendance/", views.debug_attendance, name="debug_attendance"),
]
