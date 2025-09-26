from django.urls import path
from . import views

urlpatterns = [
    path("teacher", views.analytics_landing, name="analytics_landing"),
    path("<int:class_id>/", views.analytics_dashboard, name="analytics_dashboard"),
    path("api/<int:class_id>/", views.analytics_data, name="analytics_data"),
    path("qr/", views.qr_page, name="qr_page"),
    path("api/qr/", views.qr_api, name="qr_api"),
    path("faculty-dashboard/", views.faculty_dashboard, name="faculty_dashboard"),
    path("mark/<int:class_id>/", views.mark_attendance, name="faculty_mark_attendance"),
    path("attendance-records/", views.faculty_attendance_records, name="faculty_attendance_records"),
    path("attendance-detail/<int:record_id>/", views.faculty_attendance_detail, name="faculty_attendance_detail"),
    path("notifications/", views.teacher_notifications, name="teacher_notifications"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("api/notification-count/", views.get_notification_count, name="get_notification_count"),
]

