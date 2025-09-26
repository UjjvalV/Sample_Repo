from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden
from student.models import Group, Teacher
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseServerError, HttpResponseNotFound
from django.conf import settings
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import date, timedelta,datetime
from django.utils import timezone
from student.models import Group, Student, Teacher, Subject
from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail
import time

try:
    import qrcode
    from io import BytesIO
except Exception:
    qrcode = None
    BytesIO = None


def analytics_landing(request):
    # Show groups based on role: admins see all; teachers see only assigned groups
    from student.models import Group, Student
    if request.user.is_superuser:
        groups = Group.objects.all().order_by('stream', 'name')
    else:
        teacher = Teacher.objects.filter(user=request.user).first()
        if teacher:
            groups = teacher.groups.all().order_by('stream', 'name')
        else:
            groups = Group.objects.none()
    classes_count = groups.count()
    students_count = Student.objects.filter(group__in=groups).count() if classes_count else 0
    context = { 'groups': groups, 'classes_count': classes_count, 'students_count': students_count }
    return render(request, "faculty/analytics_landing.html", context)


def analytics_dashboard(request, class_id):
    """Render the analytics dashboard for a specific class"""
    try:
        from student.models import Group, Teacher
        
        print(f"Analytics dashboard called for class_id: {class_id}")
        print(f"User: {request.user}")
        print(f"Is authenticated: {request.user.is_authenticated}")
        
        # Get the group
        try:
            group = Group.objects.get(id=class_id)
            print(f"Group found: {group.stream} - {group.name}")
        except Group.DoesNotExist:
            print(f"Group with id {class_id} not found")
            return HttpResponseNotFound("❌ Class not found.")
        
        # Check if user is authorized to view this class (skip for now to test)
        # if not request.user.is_superuser:
        #     teacher = Teacher.objects.filter(user=request.user).first()
        #     if not teacher or not teacher.groups.filter(id=class_id).exists():
        #         return HttpResponseForbidden("❌ You are not authorized to view this class.")
        
        # Basic context - data will be loaded via AJAX
        context = {
            "class_id": class_id,
            "class_name": f"{group.stream} - {group.name}",
            "group": group,
            "total_students": group.student_set.count(),
            "present_today": 0,
            "absent_today": 0,
            "labels": [],
            "trend_data": [],
            "user": request.user,
        }
        
        print(f"Rendering analytics dashboard for class {class_id}: {group.stream} - {group.name}")
        return render(request, "faculty/analytics_basic.html", context)
        
    except Exception as e:
        print(f"Error in analytics_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return HttpResponseServerError(f"❌ Error loading analytics dashboard: {str(e)}")




@login_required
def faculty_dashboard(request):
    # If superuser, let them see everything
    if request.user.is_superuser:
        groups = Group.objects.all()
        return render(request, "faculty/faculty_dashboard.html", {"groups": groups, "is_admin": True})

    # Check if this user is linked to a teacher profile
    teacher = Teacher.objects.filter(user=request.user).first()
    if not teacher:
        # User exists but is not a teacher
        return HttpResponseForbidden("❌ You are logged in, but you are not registered as a teacher.")

    # Get groups assigned to this teacher
    groups = teacher.groups.all()
    if not groups.exists():
        # Teacher has no groups assigned yet
        return render(request, "faculty/no_groups_assigned.html", {"teacher": teacher})

    # Otherwise, show only their groups
    return render(request, "faculty/faculty_dashboard.html", {"groups": groups, "is_admin":True})

# def analytics_data(request, class_id):
#     """Fetch analytics JSON from database using bidirectional attendance records."""
#     try:
#         from student.models import Group, Student, AttendanceRecord
#         from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail
        
#         print(f"Analytics request for class_id: {class_id}")
        
#         try:
#             group = Group.objects.get(id=class_id)
#             print(f"Group found: {group.stream} - {group.name}")
#         except Group.DoesNotExist:
#             print(f"Group with id {class_id} not found")
#             return JsonResponse({
#                 "class_name": "Unknown Class",
#                 "total_students": 0,
#                 "present_today": 0,
#                 "absent_today": 0,
#                 "labels": [],
#                 "trend_data": [],
#                 "daily_absent": [],
#                 "absent_students_today": [],
#                 "total_absences_week": 0,
#                 "avg_absent_per_day": 0,
#                 "worst_day": {"date": "-", "absent_count": 0},
#                 "attendance_rate_today": 0,
#                 "attendance_rate_week": 0,
#                 "teacher_info": None,
#                 "subject_info": None,
#                 "bidirectional_data": True,
#                 "error": f"Class with ID {class_id} not found"
#             })

#         students = Student.objects.filter(group=group)
#         total_students = students.count()
#         # Get date from query param, default to today
#         date_str = request.GET.get('date')
#         if date_str:
#             try:
#                 target_day = date.fromisoformat(date_str)
#             except Exception:
#                 target_day = date.today()
#         else:
#             target_day = date.today()
        
#         print(f"Total students in group: {total_students}")
        
#         # Get current teacher info if logged in
#         teacher_info = None
#         current_teacher = None
#         if hasattr(request, "user") and request.user.is_authenticated:
#             try:
#                 current_teacher = Teacher.objects.filter(user=request.user).first()
#                 if current_teacher:
#                     teacher_info = {
#                         "name": current_teacher.name,
#                         "roll_no": current_teacher.roll_no,
#                         "subject_id": current_teacher.subject_id
#                     }
#                     print(f"Analytics for teacher: {current_teacher.name} (Roll: {current_teacher.roll_no})")
#                 else:
#                     print("No teacher found for current user")
#             except Exception as e:
#                 print(f"Error fetching teacher info: {e}")

#         # Get attendance records for this group
#         attendance_records = AttendanceRecord.objects.filter(group=group)
#         print(f"Total attendance records for group: {attendance_records.count()}")
        
#         # Filter by current teacher if available
#         if current_teacher:
#             attendance_records = attendance_records.filter(teacher=current_teacher)
#             print(f"Attendance records for teacher: {attendance_records.count()}")
        
#         # Attendance for selected day
#         selected_attendance = attendance_records.filter(attendance_date=target_day, status='present')
#         present_today = selected_attendance.count()
#         absent_today = total_students - present_today

#         print(f"Attendance for {target_day} - Present: {present_today}, Absent: {absent_today}")

#         # Get absent students for selected day
#         present_student_ids = selected_attendance.values_list('student_id', flat=True)
#         absent_students = students.exclude(id__in=present_student_ids)
#         absent_list = [f"{s.roll_number} - {s.name}" for s in absent_students]
        
#         # Get attendance data for last 7 days
#         labels = []
#         trend_data = []
#         daily_absent = []
#         today=target_date
        
#         for i in range(6, -1, -1):
#             target_date = today - timedelta(days=i)
#             labels.append(target_date.strftime("%d-%b"))
            
#             # Get attendance for this date
#             day_attendance = attendance_records.filter(attendance_date=target_date, status='present')
#             day_present = day_attendance.count()
#             day_absent_count = total_students - day_present
            
#             trend_data.append(day_present)
#             daily_absent.append(day_absent_count)
        
#         print(f"Generated 7-day data - Labels: {labels}, Trend data: {trend_data}")
        
#         # Calculate weekly statistics
#         total_absences_week = sum(daily_absent)
#         avg_absent_per_day = round(total_absences_week / 7, 1) if daily_absent else 0
        
#         # Find worst day
#         worst_day_index = daily_absent.index(max(daily_absent)) if daily_absent else 0
#         worst_day = {
#             "date": labels[worst_day_index] if labels else "-",
#             "absent_count": max(daily_absent) if daily_absent else 0
#         }
        
#         # Calculate attendance rates
#         attendance_rate_today = round((present_today / total_students) * 100, 1) if total_students else 0
        
#         # Weekly attendance rate (average of daily rates)
#         weekly_rates = []
#         for i, present in enumerate(trend_data):
#             if total_students > 0:
#                 daily_rate = (present / total_students) * 100
#                 weekly_rates.append(daily_rate)
#         attendance_rate_week = round(sum(weekly_rates) / len(weekly_rates), 1) if weekly_rates else 0
        
#         # Convert trend data to percentages for chart display
#         trend_data_percentages = []
#         for present in trend_data:
#             if total_students > 0:
#                 percentage = round((present / total_students) * 100, 1)
#                 trend_data_percentages.append(percentage)
#             else:
#                 trend_data_percentages.append(0)
        
#         # Get subject information
#         subject_info = None
#         if current_teacher and current_teacher.subject_id:
#             try:
#                 from student.models import Subject
#                 subject = Subject.objects.filter(code=current_teacher.subject_id).first()
#                 if subject:
#                     subject_info = {
#                         "name": subject.name,
#                         "code": subject.code
#                     }
#             except Exception as e:
#                 print(f"Error fetching subject info: {e}")

#         data = {
#             "class_name": f"{group.stream} - {group.name}",
#             "total_students": total_students,
#             "present_today": present_today,
#             "absent_today": absent_today,
#             "labels": labels,
#             "trend_data": trend_data_percentages,  # Use percentage data for charts
#             "trend_data_raw": trend_data,  # Keep raw data for reference
#             "daily_absent": daily_absent,
#             "absent_students_today": absent_list,
#             "total_absences_week": total_absences_week,
#             "avg_absent_per_day": avg_absent_per_day,
#             "worst_day": worst_day,
#             "attendance_rate_today": attendance_rate_today,
#             "attendance_rate_week": attendance_rate_week,
#             "teacher_info": teacher_info,
#             "subject_info": subject_info,
#             "bidirectional_data": True,
#             "debug_info": {
#                 "group_id": class_id,
#                 "group_name": f"{group.stream} - {group.name}",
#                 "total_students": total_students,
#                 "attendance_records_count": attendance_records.count(),
#                 "teacher_name": current_teacher.name if current_teacher else "No teacher",
#             }
#         }
        
#         print(f"Returning analytics data: {data}")
#         return JsonResponse(data)
        
#     except Exception as e:
#         print(f"Error fetching analytics data: {e}")
#         import traceback
#         traceback.print_exc()
#         return JsonResponse({
#             "class_name": "Error",
#             "total_students": 0,
#             "present_today": 0,
#             "absent_today": 0,
#             "labels": [],
#             "trend_data": [],
#             "daily_absent": [],
#             "absent_students_today": [],
#             "total_absences_week": 0,
#             "avg_absent_per_day": 0,
#             "worst_day": {"date": "-", "absent_count": 0},
#             "attendance_rate_today": 0,
#             "attendance_rate_week": 0,
#             "teacher_info": None,
#             "subject_info": None,
#             "bidirectional_data": False,
#             "error": str(e)
#         })

from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import FacultyAttendanceRecord, FacultyAttendanceDetail
from student.models import Teacher, Subject, Group, Student


def analytics_data(request, class_id=None):
    """
    Fetch analytics JSON from faculty attendance models.
    Supports:
    1. Group/Class-based analytics (if class_id provided)
    2. Teacher-based analytics (if teacher_id GET param provided)
    """
    try:
        # --- Date handling ---
        date_str = request.GET.get("date")
        if date_str:
            try:
                target_day = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                target_day = timezone.now().date()
        else:
            target_day = timezone.now().date()

        # --- Check if teacher-based analytics ---
        teacher_id = request.GET.get("teacher_id")
        if teacher_id:
            try:
                current_teacher = Teacher.objects.get(id=teacher_id)
            except Teacher.DoesNotExist:
                return JsonResponse({"error": "Teacher not found"}, status=404)

            subject = Subject.objects.filter(code=current_teacher.subject_id).first()
            if not subject:
                return JsonResponse({"error": f"No subject found for code {current_teacher.subject_id}"}, status=404)

            # Query records for this teacher + subject + date
            records = FacultyAttendanceRecord.objects.filter(
                teacher=current_teacher,
                subject=subject,
                attendance_date=target_day
            )

            total_students = sum(r.present_students + r.absent_students for r in records) if records.exists() else 0
            present_today = sum(r.present_students for r in records) if records.exists() else 0
            absent_today = sum(r.absent_students for r in records) if records.exists() else 0
            absent_list = []  # Not available in summary
            class_name = f"{subject.name} ({subject.code})"

            # Trend data (last 7 days)
            labels, trend_data, daily_absent = [], [], []
            for i in range(6, -1, -1):
                day = target_day - timedelta(days=i)
                day_records = FacultyAttendanceRecord.objects.filter(
                    teacher=current_teacher,
                    subject=subject,
                    attendance_date=day
                )
                day_present = sum(r.present_students for r in day_records) if day_records.exists() else 0
                labels.append(day.strftime("%d-%b"))
                trend_data.append(round((day_present / total_students) * 100, 1) if total_students else 0)
                daily_absent.append(total_students - day_present)

        else:
            # --- Group/Class-based analytics ---
            if not class_id:
                return JsonResponse({"error": "class_id is required if teacher_id not provided"}, status=400)
            try:
                group = Group.objects.get(id=class_id)
            except Group.DoesNotExist:
                return JsonResponse({"error": f"Class with ID {class_id} not found"}, status=404)

            students = Student.objects.filter(group=group)
            total_students = students.count()

            # Step 1: FacultyAttendanceDetail (per student)
            # Consider all subjects on the selected day for this group
            details = FacultyAttendanceDetail.objects.filter(
                faculty_record__group=group,
                faculty_record__attendance_date=target_day
            )

            # Build per-student map
            student_status = {s.id: "absent" for s in students}
            if details.exists():
                present_today = details.filter(status="present").count()
                absent_today = details.filter(status="absent").count()
                absent_list = [
                    f"{d.student.roll_number} - {d.student.name}"
                    for d in details.filter(status="absent")
                ]
                for d in details:
                    student_status[d.student_id] = d.status
            else:
                # Step 2: FacultyAttendanceRecord summary
                # Sum across all subjects' summary records for the day
                day_records = FacultyAttendanceRecord.objects.filter(
                    group=group, attendance_date=target_day
                )
                if day_records.exists():
                    present_today = sum(r.present_students for r in day_records)
                    # Cap to total students (some students may attend multiple subjects)
                    if present_today > total_students:
                        present_today = total_students
                    absent_today = total_students - present_today
                else:
                    present_today = 0
                    absent_today = total_students
                absent_list = []

            class_name = f"{group.stream} - {group.name}"

            # Trend data (last 7 days)
            labels, trend_data, daily_absent = [], [], []
            for i in range(6, -1, -1):
                day = target_day - timedelta(days=i)
                day_records = FacultyAttendanceRecord.objects.filter(group=group, attendance_date=day)
                day_present = sum(r.present_students for r in day_records) if day_records.exists() else 0
                if day_present > total_students:
                    day_present = total_students
                labels.append(day.strftime("%d-%b"))
                trend_data.append(round((day_present / total_students) * 100, 1) if total_students else 0)
                daily_absent.append(total_students - day_present)

        # --- Weekly stats ---
        total_absences_week = sum(daily_absent)
        avg_absent_per_day = round(total_absences_week / 7, 1) if total_students else 0
        worst_day_index = daily_absent.index(max(daily_absent)) if daily_absent else 0
        worst_day = {
            "date": labels[worst_day_index] if labels else "-",
            "absent_count": max(daily_absent) if daily_absent else 0,
        }
        attendance_rate_today = round((present_today / total_students) * 100, 1) if total_students else 0
        attendance_rate_week = round(sum(trend_data) / len(trend_data), 1) if trend_data else 0

        # Teacher info (if logged in)
        teacher_info, subject_info = None, None
        if hasattr(request, "user") and request.user.is_authenticated:
            current_user_teacher = Teacher.objects.filter(user=request.user).first()
            if current_user_teacher:
                teacher_info = {
                    "name": current_user_teacher.name,
                    "email": current_user_teacher.email,
                }
                subj = Subject.objects.filter(code=current_user_teacher.subject_id).first()
                if subj:
                    subject_info = {"name": subj.name, "code": subj.code}

        data = {
            "class_name": class_name,
            "total_students": total_students,
            "present_today": present_today,
            "absent_today": absent_today,
            "labels": labels,
            "trend_data": trend_data,
            "daily_absent": daily_absent,
            "absent_students_today": absent_list,
            "students": [
                {
                    "id": s.id,
                    "name": s.name,
                    "roll_number": s.roll_number,
                    "status": student_status.get(s.id, "absent"),
                }
                for s in students
            ] if class_id else [],
            "total_absences_week": total_absences_week,
            "avg_absent_per_day": avg_absent_per_day,
            "worst_day": worst_day,
            "attendance_rate_today": attendance_rate_today,
            "attendance_rate_week": attendance_rate_week,
            "teacher_info": teacher_info,
            "subject_info": subject_info,
        }

        return JsonResponse(data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

def qr_page(request):
    # Get all groups for the dropdown
    from student.models import Group, Teacher, Subject
    groups = Group.objects.all().order_by('stream', 'name')
    # Prefill subject code from the logged-in teacher if available
    subject_code = ""
    try:
        current_teacher = Teacher.objects.filter(user=request.user).only("subject_id").first()
        if current_teacher and current_teacher.subject_id:
            subject_code = str(current_teacher.subject_id)
    except Exception:
        pass
    
    # Provide list of subject codes to populate dropdown
    subjects = list(Subject.objects.all().order_by('code').values_list('code', flat=True))
    context = {
        'groups': groups,
        'subject_code': subject_code,
        'subjects': subjects,
    }
    return render(request, "faculty/qr.html", context)

@login_required
def faculty_attendance_records(request):
    """View to show detailed attendance records for faculty"""
    from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail
    from student.models import Group, Subject
    
    # Get current teacher
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return HttpResponseForbidden("❌ You are not registered as a teacher.")
    
    # Get teacher's groups
    teacher_groups = current_teacher.groups.all()
    if not teacher_groups.exists():
        return render(request, "faculty/no_groups_assigned.html", {"teacher": current_teacher})
    
    # Get attendance records for this teacher
    faculty_records = FacultyAttendanceRecord.objects.filter(
        teacher=current_teacher
    ).select_related('subject', 'group').order_by('-attendance_date', '-attendance_time')
    
    # Get recent records (last 30 days)
    from datetime import timedelta
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_records = faculty_records.filter(attendance_date__gte=thirty_days_ago)
    
    # Get today's record if exists
    today_record = faculty_records.filter(attendance_date=date.today()).first()
    
    # Get attendance details for today if record exists
    today_details = []
    if today_record:
        today_details = FacultyAttendanceDetail.objects.filter(
            faculty_record=today_record
        ).select_related('student').order_by('student__roll_number')
    
    context = {
        'teacher': current_teacher,
        'teacher_groups': teacher_groups,
        'recent_records': recent_records,
        'today_record': today_record,
        'today_details': today_details,
        'total_records': faculty_records.count(),
        'recent_count': recent_records.count(),
    }
    
    return render(request, "faculty/attendance_records.html", context)

@login_required
def faculty_attendance_detail(request, record_id):
    """View to show detailed attendance for a specific record"""
    from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail
    
    # Get current teacher
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return HttpResponseForbidden("❌ You are not registered as a teacher.")
    
    try:
        # Get the attendance record
        faculty_record = FacultyAttendanceRecord.objects.select_related(
            'teacher', 'subject', 'group'
        ).get(id=record_id, teacher=current_teacher)
        
        # Get all attendance details for this record
        attendance_details = FacultyAttendanceDetail.objects.filter(
            faculty_record=faculty_record
        ).select_related('student').order_by('student__roll_number')
        
        # Separate present and absent students
        present_students = attendance_details.filter(status='present')
        absent_students = attendance_details.filter(status='absent')
        
        context = {
            'faculty_record': faculty_record,
            'attendance_details': attendance_details,
            'present_students': present_students,
            'absent_students': absent_students,
            'total_students': attendance_details.count(),
            'present_count': present_students.count(),
            'absent_count': absent_students.count(),
        }
        
        return render(request, "faculty/attendance_detail.html", context)
        
    except FacultyAttendanceRecord.DoesNotExist:
        return HttpResponseForbidden("❌ Attendance record not found or you don't have permission to view it.")

@login_required
def teacher_notifications(request):
    """View to show teacher notifications"""
    from faculty.models import TeacherNotification
    
    # Get current teacher
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return HttpResponseForbidden("❌ You are not registered as a teacher.")
    
    # Get notifications for this teacher
    notifications = TeacherNotification.objects.filter(
        teacher=current_teacher
    ).select_related('student', 'attendance_record').order_by('-created_at')
    
    # Get unread count
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'teacher': current_teacher,
        'notifications': notifications,
        'unread_count': unread_count,
        'total_notifications': notifications.count(),
    }
    
    return render(request, "faculty/notifications.html", context)

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    from faculty.models import TeacherNotification
    
    # Get current teacher
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return JsonResponse({'status': 'error', 'message': 'Not authorized'})
    
    try:
        notification = TeacherNotification.objects.get(
            id=notification_id,
            teacher=current_teacher
        )
        notification.mark_as_read()
        return JsonResponse({'status': 'success', 'message': 'Notification marked as read'})
    except TeacherNotification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'})

@login_required
def get_notification_count(request):
    """Get unread notification count for AJAX requests"""
    from faculty.models import TeacherNotification
    
    # Get current teacher
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return JsonResponse({'unread_count': 0})
    
    unread_count = TeacherNotification.objects.filter(
        teacher=current_teacher,
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': unread_count})


def qr_api(request):
    if qrcode is None:
        return HttpResponseServerError("Python package 'qrcode' is not installed.")

    mode = request.GET.get("mode", "class")
    class_id = request.GET.get("class_id", "0")
    
    print(f"QR API called with: mode={mode}, class_id={class_id}")

    # Always use the logged-in teacher's info for QR code, but allow subject override
    teacher_obj = None
    teacher_roll_no = None
    subject_id = None
    if hasattr(request, "user") and request.user.is_authenticated:
        teacher_obj = Teacher.objects.filter(user=request.user).first()
        if teacher_obj:
            teacher_roll_no = str(teacher_obj.roll_no)
            # Allow subject_id to be overridden by GET param (for multi-subject teachers)
            subject_id = request.GET.get("subject_id") or str(teacher_obj.subject_id)
            print(f"Using teacher info: {teacher_obj.name} (Roll: {teacher_obj.roll_no}, Subject: {subject_id})")
        else:
            print(f"No teacher found for user: {request.user.username}")
    else:
        print("User not authenticated or no user attribute")

    start_time = int(time.time())  # Exact generation time as UNIX timestamp
    
    # Ensure we have a valid subject_id - REQUIRE it, no implicit defaults
    if not subject_id:
        return JsonResponse({"error": "subject_id is required"}, status=400)

    # Normalize subject code to avoid duplicates due to case/spacing
    if isinstance(subject_id, str):
        subject_id = subject_id.strip().upper()

    # Validate that the subject exists to avoid accidental creation downstream
    try:
        from student.models import Subject  # local import to avoid circulars at module load
        if not Subject.objects.filter(code=subject_id).exists():
            return JsonResponse({"error": f"Unknown subject code: {subject_id}"}, status=400)
    except Exception:
        # If validation fails unexpectedly, continue without blocking QR but avoid defaults
        pass
    
    # Build payload with generation time and required fields
    parts = [
        f"mode={mode}",
        f"class_id={class_id}",
        f"start_time={start_time}",
        f"teacher_roll_no={teacher_roll_no}",  # Always include teacher roll number
        f"subject_id={subject_id}",  # Always include subject_id
    ]
    payload = ";".join(parts)
    
    print(f"QR Payload generated: {payload}")

    # Try PNG first (requires Pillow). If unavailable, fall back to SVG.
    try:
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        import base64
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return JsonResponse({
            "qr": b64, 
            "data": "QR_CODE_GENERATED",  # Don't expose actual QR data
            "mime": "image/png", 
            "class_id": class_id,
            "teacher_id": "HIDDEN",  # Don't expose teacher ID
            "start_time": start_time
        })
    except Exception:
        # Pillow likely missing; generate SVG instead
        try:
            import qrcode.image.svg as svg
            factory = svg.SvgImage
            img = qrcode.make(payload, image_factory=factory, box_size=8, border=4)
            svg_bytes = img.to_string().encode("utf-8") if hasattr(img, "to_string") else img.getvalue()
            import base64
            b64 = base64.b64encode(svg_bytes).decode("utf-8")
            return JsonResponse({
                "qr": b64, 
                "data": "QR_CODE_GENERATED",  # Don't expose actual QR data
                "mime": "image/svg+xml", 
                "class_id": class_id,
                "teacher_id": "HIDDEN",  # Don't expose teacher ID
                "start_time": start_time
            })
        except Exception:
            return HttpResponseServerError("Failed to generate QR (PNG and SVG backends unavailable).")
        
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from datetime import date
from student.models import Group, Student, AttendanceRecord
from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail
from .models import Teacher   # adjust import path if needed


@login_required
def mark_attendance(request, class_id):
    """Fetch students of a class by teacher and mark attendance (present/absent)."""
    # Get teacher linked to logged-in user
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return HttpResponseForbidden("❌ You are not registered as a teacher.")
    
    # Get class/group
    try:
        group = Group.objects.get(id=class_id)
    except Group.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Class not found"})
    
    # Ensure this teacher is authorized for the class
    if not request.user.is_superuser and not current_teacher.groups.filter(id=class_id).exists():
        return HttpResponseForbidden("❌ You are not allowed to mark attendance for this class.")

    students = Student.objects.filter(group=group).order_by("roll_number")
    
    if request.method == "POST":
        # Expect attendance data as { student_id: "present"/"absent" }
        data = request.POST
        today = date.today()

        # Create a faculty attendance record (header)
        faculty_record, created = FacultyAttendanceRecord.objects.get_or_create(
            teacher=current_teacher,
            group=group,
            attendance_date=today,
            defaults={"subject": Subject.objects.filter(code=current_teacher.subject_id).first()}
        )

        for student in students:
            status = data.get(str(student.id), "absent")  # default absent
            # Save AttendanceRecord (for student’s perspective)
            AttendanceRecord.objects.update_or_create(
                student=student,
                group=group,
                teacher=current_teacher,
                attendance_date=today,
                defaults={"status": status}
            )
            # Save FacultyAttendanceDetail (for faculty’s perspective)
            FacultyAttendanceDetail.objects.update_or_create(
                faculty_record=faculty_record,
                student=student,
                defaults={"status": status}
            )

        return JsonResponse({"status": "success", "message": "✅ Attendance marked successfully"})
    
    # GET → Show students list with today’s attendance status
    today = date.today()
    attendance_data = AttendanceRecord.objects.filter(
        group=group, teacher=current_teacher, attendance_date=today
    )
    attendance_map = {rec.student_id: rec.status for rec in attendance_data}

    context = {
        "teacher": current_teacher,
        "group": group,
        "students": students,
        "attendance_map": attendance_map,
    }
    return render(request, "faculty/mark_attendance.html", context)


@login_required
def class_analytics(request, class_id):
    """Show analytics for a class based on attendance records."""
    current_teacher = Teacher.objects.filter(user=request.user).first()
    if not current_teacher:
        return HttpResponseForbidden("❌ You are not registered as a teacher.")
    
    try:
        group = Group.objects.get(id=class_id)
    except Group.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Class not found"})
    
    students = Student.objects.filter(group=group)
    total_students = students.count()

    today = date.today()
    present_today = AttendanceRecord.objects.filter(
        group=group, teacher=current_teacher, attendance_date=today, status="present"
    ).count()
    absent_today = total_students - present_today

    # Attendance stats for past week
    from datetime import timedelta
    labels, present_trend = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime("%d-%b"))
        count = AttendanceRecord.objects.filter(
            group=group, teacher=current_teacher, attendance_date=day, status="present"
        ).count()
        present_trend.append(count)

    context = {
        "teacher": current_teacher,
        "class_name": f"{group.stream} - {group.name}",
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today,
        "labels": labels,
        "trend_data": present_trend,
    }
    return render(request, "faculty/class_analytics.html", context)

