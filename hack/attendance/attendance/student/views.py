from django.shortcuts import render
import jwt
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import random, string
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import User
from .models import SiteSetting
from django.utils.timezone import now
import qrcode
import io
import base64

from datetime import datetime, timedelta
from django.contrib.auth import authenticate
from django.http import JsonResponse, HttpResponseRedirect
import json
from .models import ActiveSession, Group, Subject, Student, Teacher, AttendanceRecord
from .face_utils_simple import compare_face_encodings, encode_face_from_canvas_data, validate_face_encoding
from .face_recognition_advanced import face_recognition_advanced
from datetime import date
import uuid
from django.conf import settings


# Public homepage
def homepage_view(request):
    """Render the marketing/home landing page using Django templates."""
    return render(request, "student/homepage.html")

# Signup view
def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)

                # 🔑 Explicitly control admin/staff access based on role
                if user.role == "student":
                    user.is_staff = False
                    user.is_superuser = False
                elif user.role == "faculty":
                    # Optional: Give faculty access to admin panel
                    user.is_staff = True  
                    user.is_superuser = False  # Faculties should not be superusers by default

                # Save user with retry logic for database lock issues
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        user.save()
                        break
                    except Exception as e:
                        if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                            import time
                            print(f"Database locked on attempt {attempt + 1}, retrying in 1 second...")
                            time.sleep(1)
                            continue
                        else:
                            raise e
                
                # Auto-link student profile if username matches a student's roll number
                if user.role == "student":
                    try:
                        student = Student.objects.get(roll_number=user.username)
                        student.user = user
                        
                        # Save student with retry logic
                        for attempt in range(max_retries):
                            try:
                                student.save()
                                break
                            except Exception as e:
                                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                                    import time
                                    print(f"Database locked on student save attempt {attempt + 1}, retrying...")
                                    time.sleep(1)
                                    continue
                                else:
                                    raise e
                        
                        messages.success(request, f"Account created and linked to student profile: {student.name}")
                    except Student.DoesNotExist:
                        messages.success(request, "Account created successfully! Please log in.")
                
                return redirect("login")
                
            except Exception as e:
                print(f"Error during signup: {e}")
                messages.error(request, f"Error creating account: {str(e)}. Please try again.")
                # Re-render the form with error message
                return render(request, "student/signup.html", {"form": form})
    else:
        form = SignUpForm()

    return render(request, "student/signup.html", {"form": form})

# Login view
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user:
            # Generate new JWT
            payload = {
                "user_id": user.id,
                "exp": datetime.utcnow() + timedelta(minutes=30)  # JWT expires in 30 min
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

            # Generate a new session_id
            new_session_id = uuid.uuid4()
            

            # Invalidate old session if exists
            ActiveSession.objects.update_or_create(
                user=user,
                defaults={
                    "jwt_token": token,
                    "session_id": new_session_id
                }
            )

            # Log Django session in parallel (for @login_required decorated views)
            login(request, user)

            # If client expects JSON (e.g., API/AJAX), return tokens as JSON
            if 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({
                    "message": "Login successful",
                    "jwt_token": token,
                    "session_id": str(new_session_id)
                })

            # Otherwise, set HttpOnly cookies and redirect to dashboard
            response = HttpResponseRedirect("/dashboard/")
            # Cookies expire with JWT expiry (~30 min)
            max_age = 30 * 60
            secure_flag = False  # set True if using HTTPS
            response.set_cookie("jwt_token", token, max_age=max_age, httponly=True, samesite='Lax', secure=secure_flag)
            response.set_cookie("session_id", str(new_session_id), max_age=max_age, httponly=True, samesite='Lax', secure=secure_flag)
            return response
        else:
            messages.error(request, "Invalid credentials")
            return redirect("login")
    # GET: render login page
    return render(request, "student/login.html")

# Role-based dashboard redirect
@staff_member_required
def generate_faculty_code(request):
    if request.method == "POST":
        # Generate random 8-character alphanumeric code
        new_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # Save in SiteSetting
        SiteSetting.set("faculty_access_code", new_code)
        
        messages.success(request, f"New faculty access code generated: {new_code}")
        return redirect("generate_faculty_code")
    
    # GET request → show current code
    current_code = SiteSetting.get("faculty_access_code")
    return render(request, "student/generate_faculty_code.html", {"current_code": current_code})
@login_required
def dashboard_redirect(request):
    user = request.user
    if user.role == "student":
        return redirect("student_dashboard")
    elif user.role == "faculty":
        return redirect("analytics_landing")
    elif user.is_staff:
        return redirect("/admin/")
    else:
        messages.error(request, "Role not recognized")
        return redirect("login")

# Student dashboard
@login_required
def student_dashboard(request):
    """Enhanced student dashboard with bidirectional attendance data"""
    user = request.user
    today = date.today()
    
    # Get student profile
    try:
        student = user.student_profile
    except Student.DoesNotExist:
        return render(request, "student/student_dashboard.html", {
            "error": "Student profile not found",
            "attendance_rate": 0,
            "total_classes": 0,
            "present_days": 0,
            "absent_days": 0,
            "recent_records": [],
            "is_present_today": False,
        })

    # Get actual attendance records from the database
    attendance_records = AttendanceRecord.objects.filter(
        student=student
    ).select_related('teacher', 'subject', 'group').order_by('-attendance_date', '-attendance_time')
    
    # Calculate overall statistics
    total_records = attendance_records.count()
    present_records = attendance_records.filter(status='present')
    absent_records = attendance_records.filter(status='absent')
    
    present_count = present_records.count()
    absent_count = absent_records.count()
    
    # Calculate overall attendance rate
    if total_records > 0:
        attendance_rate = round((present_count / total_records) * 100, 1)
    else:
        attendance_rate = 0
    
    # Get today's attendance status
    today_record = attendance_records.filter(attendance_date=today).first()
    is_present_today = today_record and today_record.status == 'present'
    
    # Get recent records (last 5 days)
    from datetime import timedelta
    five_days_ago = today - timedelta(days=5)
    recent_attendance = attendance_records.filter(attendance_date__gte=five_days_ago)
    
    # Format recent records for dashboard
    recent_records = []
    for record in recent_attendance:
        recent_records.append({
            "date": record.attendance_date.strftime("%Y-%m-%d"),
            "label": "Today" if record.attendance_date == today else record.attendance_date.strftime("%a, %b %d"),
            "class": f"{record.group.stream} - {record.group.name}" if record.group else "N/A",
            "subject": record.subject.name if record.subject else "N/A",
            "teacher": record.teacher.name if record.teacher else "N/A",
            "status": record.status.title(),
            "time": record.attendance_time.strftime("%I:%M %p") if record.attendance_time else "-",
            "face_verified": record.face_verified,
        })
    
    # Get weekly statistics (last 7 days)
    seven_days_ago = today - timedelta(days=7)
    weekly_records = attendance_records.filter(attendance_date__gte=seven_days_ago)
    weekly_present = weekly_records.filter(status='present').count()
    weekly_total = weekly_records.count()
    weekly_attendance_rate = round((weekly_present / weekly_total) * 100, 1) if weekly_total > 0 else 0
    
    # Get monthly statistics (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    monthly_records = attendance_records.filter(attendance_date__gte=thirty_days_ago)
    monthly_present = monthly_records.filter(status='present').count()
    monthly_total = monthly_records.count()
    monthly_attendance_rate = round((monthly_present / monthly_total) * 100, 1) if monthly_total > 0 else 0
    
    # Get attendance streak
    current_streak = 0
    for i in range(30):  # Check last 30 days
        check_date = today - timedelta(days=i)
        day_record = attendance_records.filter(attendance_date=check_date).first()
        
        if day_record and day_record.status == 'present':
            current_streak += 1
        else:
            if i == 0:  # Today is absent
                current_streak = 0
            break
    
    # Get subject-wise quick stats (ensure ALL assigned subjects are present)
    # Seed with assigned subjects so even 0/0 subjects show up on dashboard
    subject_stats = {}
    for subj in student.subjects:
        subject_stats[subj.code] = {
            "display_name": subj.name,
            "present": 0,
            "total": 0,
            "weekly_present": 0,
            "weekly_total": 0,
            "monthly_present": 0,
            "monthly_total": 0,
        }

    # Fill stats from existing attendance records
    for record in attendance_records:
        subj_code = record.subject.code if record.subject else "UNKNOWN"
        subj_name = record.subject.name if record.subject else "Unknown"
        if subj_code not in subject_stats:
            subject_stats[subj_code] = {
                "display_name": subj_name,
                "present": 0,
                "total": 0,
                "weekly_present": 0,
                "weekly_total": 0,
                "monthly_present": 0,
                "monthly_total": 0,
            }
        stats = subject_stats[subj_code]
        stats["total"] += 1
        if record.status == 'present':
            stats["present"] += 1
        if record.attendance_date >= seven_days_ago:
            stats["weekly_total"] += 1
            if record.status == 'present':
                stats["weekly_present"] += 1
        if record.attendance_date >= thirty_days_ago:
            stats["monthly_total"] += 1
            if record.status == 'present':
                stats["monthly_present"] += 1

    # Calculate subject-wise rates
    for subj_code, stats in subject_stats.items():
        stats["overall_rate"] = round((stats["present"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0
        stats["weekly_rate"] = round((stats["weekly_present"] / stats["weekly_total"]) * 100, 1) if stats["weekly_total"] > 0 else 0
        stats["monthly_rate"] = round((stats["monthly_present"] / stats["monthly_total"]) * 100, 1) if stats["monthly_total"] > 0 else 0
    
    # Get student's courses/subjects
    student_profile = student
    student_subjects = student.subjects
    student_group = student.group
    
    # Get last attendance info
    last_attendance = attendance_records.first() if attendance_records.exists() else None
    
    # Get upcoming classes (if any)
    upcoming_classes = []
    # You can add logic here to show upcoming classes based on schedule
    
    context = {
        # Overall statistics
        "attendance_rate": attendance_rate,
        "total_classes": total_records,
        "present_days": present_count,
        "absent_days": absent_count,
        
        # Time-based statistics
        "weekly_attendance": weekly_attendance_rate,
        "monthly_attendance": monthly_attendance_rate,
        "weekly_present": weekly_present,
        "weekly_total": weekly_total,
        "monthly_present": monthly_present,
        "monthly_total": monthly_total,
        
        # Today's status
        "is_present_today": is_present_today,
        "today_status": today_record.status if today_record else "absent",
        "today_time": today_record.attendance_time.strftime("%I:%M %p") if today_record and today_record.attendance_time else None,
        
        # Recent activity
        "recent_records": recent_records,
        "current_streak": current_streak,
        
        # Subject information
        "subject_stats": subject_stats,
        "student_profile": student_profile,
        "student_subjects": student_subjects,
        "student_group": student_group,
        
        # Additional info
        "last_attendance": last_attendance,
        "upcoming_classes": upcoming_classes,
        "total_subjects": len(student_subjects),
    }
    return render(request, "student/student_dashboard.html", context)

# Faculty dashboard
@login_required
def qr_scanner_view(request):
    # Get student information
    student_profile = None
    student_group = None
    student_subjects = []
    
    try:
        student_profile = request.user.student_profile
        student_group = student_profile.group
        student_subjects = student_profile.subjects
    except Student.DoesNotExist:
        pass
    
    context = {
        'student_profile': student_profile,
        'student_group': student_group,
        'student_subjects': student_subjects,
    }
    return render(request, "student/qr_scanner_fixed.html", context)

@login_required
def qr_expired_view(request):
    # Get student information
    student_profile = None
    student_group = None
    qr_data = None
    error_message = None
    
    try:
        student_profile = request.user.student_profile
        student_group = student_profile.group
    except Student.DoesNotExist:
        pass
    
    if request.method == 'POST':
        # Handle storing expired QR data
        import json
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            if not data.get('qr_data'):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: missing qr_data field'})
            
            qr_data_dict = data.get('qr_data', {})
            if not qr_data_dict.get('start_time'):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: missing start_time field'})
            
            # Validate start_time is a valid integer
            try:
                int(qr_data_dict.get('start_time'))
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: start_time must be a valid timestamp'})
            
            request.session['expired_qr_data'] = data
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing QR data: {str(e)}'})
    
    # Get QR data from session if available
    qr_data = request.session.get('expired_qr_data', None)
    qr_data_dict = None
    
    # Validate QR data if available
    if qr_data:
        try:
            qr_data_dict = qr_data.get('qr_data', {})
            start_time = int(qr_data_dict.get('start_time', 0))
            
            # Convert start_time to datetime for template display
            from datetime import datetime
            qr_data_dict['generated_time'] = datetime.fromtimestamp(start_time)
            
            # Add scanning time - use current server time for accuracy
            qr_data_dict['expired_time'] = datetime.now()
            
            # Validate time difference is reasonable
            import time
            current_time = int(time.time())
            time_diff = current_time - start_time
            
            if time_diff < 0:
                error_message = "Invalid QR data: scan time is before generation time"
            elif time_diff > 86400:  # More than 24 hours
                error_message = "QR data appears to be very old"
        except (ValueError, TypeError) as e:
            error_message = f"Invalid timestamp data: {str(e)}"
        except Exception as e:
            error_message = f"Error processing QR data: {str(e)}"
    
    context = {
        'student_profile': student_profile,
        'student_group': student_group,
        'qr_data': qr_data_dict,  # Pass the actual QR data dict, not the wrapper
        'error_message': error_message,
    }
    return render(request, "student/qr_expired.html", context)

@login_required
def face_recognition_view(request):
    """Face recognition page for attendance verification"""
    # Get student information
    student_profile = None
    student_group = None
    qr_data = None
    scan_info = None
    error_message = None
    
    try:
        student_profile = request.user.student_profile
        student_group = student_profile.group
    except Student.DoesNotExist:
        pass
    
    if request.method == 'POST':
        # Handle face recognition verification
        import json
        try:
            data = json.loads(request.body)
            
            # Check if this is a face verification request
            if data.get('action') == 'verify_face':
                return handle_face_verification(request, data)
            
            # Handle storing face recognition data
            if not data.get('qr_data'):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: missing qr_data field'})
            
            qr_data_dict = data.get('qr_data', {})
            if not qr_data_dict.get('start_time'):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: missing start_time field'})
            
            # Validate start_time is a valid integer
            try:
                int(qr_data_dict.get('start_time'))
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: start_time must be a valid timestamp'})
            
            request.session['face_recognition_data'] = data
            print(f"Stored QR data in session: {data}")
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing QR data: {str(e)}'})
    
    # Get QR data from session if available
    qr_data = request.session.get('face_recognition_data', None)
    qr_data_dict = None
    
    print(f"Face recognition view - Session data: {qr_data}")
    print(f"Face recognition view - Request method: {request.method}")
    
    # Calculate scan information if QR data is available
    if qr_data:
        try:
            import time
            current_time = int(time.time())
            qr_data_dict = qr_data.get('qr_data', {})
            start_time = int(qr_data_dict.get('start_time', 0))
            time_diff = current_time - start_time
            
            # Validate time difference is reasonable (not negative or too large)
            if time_diff < 0:
                error_message = "Invalid QR data: scan time is before generation time"
            elif time_diff > 3600:  # More than 1 hour
                error_message = "QR data appears to be very old"
            else:
                # Convert start_time to datetime for template display
                from datetime import datetime
                qr_data_dict['generated_time'] = datetime.fromtimestamp(start_time)
                
                # Add scanning time - use current server time for accuracy
                qr_data_dict['scan_time'] = datetime.now()
                
                scan_info = {
                    'subject_id': qr_data_dict.get('subject_id', 'N/A'),
                    'student_id': request.user.student_profile.id if hasattr(request.user, 'student_profile') else request.user.id,
                    'scan_timestamp': current_time,
                    'time_difference': time_diff,
                    'start_time': start_time,
                    'generated_time': datetime.fromtimestamp(start_time),
                    'scan_time': datetime.now(),
                    'class_id': qr_data_dict.get('class_id', 'N/A'),
                    'teacher_roll_no': qr_data_dict.get('teacher_roll_no', 'N/A'),
                }
        except (ValueError, TypeError) as e:
            error_message = f"Invalid timestamp data: {str(e)}"
        except Exception as e:
            error_message = f"Error processing scan info: {str(e)}"
    
    context = {
        'student_profile': student_profile,
        'student_group': student_group,
        'qr_data': qr_data_dict,  # Pass the actual QR data dict, not the wrapper
        'scan_info': scan_info,
        'error_message': error_message,
    }
    return render(request, "student/face_recognition.html", context)

def handle_face_verification(request, data):
    """Handle face verification with liveness detection and mark attendance"""
    try:
        # Get face encoding data from request
        face_encoding_data = data.get('face_encoding')
        if not face_encoding_data:
            return JsonResponse({'status': 'error', 'message': 'No face encoding provided'})
        
        # Parse face encoding data
        try:
            face_data = json.loads(face_encoding_data)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid face encoding data format'})
        
        # Check if this is a verification token (face already verified on frontend)
        if face_data.get('face_verified') and face_data.get('verification_type') == 'face_recognition':
            # Face was already verified on frontend, just mark attendance
            print("Face already verified on frontend, proceeding with attendance marking")
            attendance_record = mark_attendance(request, data)
            if attendance_record:
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Face verified and attendance marked successfully',
                    'attendance_id': attendance_record.id
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to mark attendance'})
        
        # If it's not a verification token, proceed with advanced face verification
        # Extract canvas data URL
        canvas_data_url = face_data.get('canvas_data_url')
        if not canvas_data_url:
            return JsonResponse({'status': 'error', 'message': 'No canvas data URL in face encoding'})
        
        # Get student's stored face encoding
        student = request.user.student_profile
        stored_encoding = request.user.face_encoding
        
        if not stored_encoding:
            return JsonResponse({'status': 'error', 'message': 'No face encoding found for this student'})
        
        # Use advanced face recognition with liveness detection
        user_id = str(request.user.id)
        verification_result = face_recognition_advanced.verify_face_with_liveness(
            user_id, 
            stored_encoding, 
            canvas_data_url
        )
        
        if verification_result['success']:
            # Face verification and liveness detection successful - mark attendance
            attendance_result = mark_attendance(request, data)
            if attendance_result:
                # Check if attendance was already marked
                if isinstance(attendance_result, dict) and attendance_result.get('error'):
                    return JsonResponse({
                        'status': 'already_marked',
                        'message': attendance_result['message'],
                        'existing_record': {
                            'id': attendance_result['existing_record'].id if hasattr(attendance_result['existing_record'], 'id') else 'N/A',
                            'time': attendance_result['existing_record'].attendance_time.strftime("%I:%M %p") if hasattr(attendance_result['existing_record'], 'attendance_time') else 'N/A',
                            'date': attendance_result['existing_record'].attendance_date.strftime("%Y-%m-%d") if hasattr(attendance_result['existing_record'], 'attendance_date') else 'N/A'
                        }
                    })
                else:
                    # New attendance marked successfully
                    attendance_id = attendance_result.id if hasattr(attendance_result, 'id') else 'N/A'
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Face verified with liveness detection and attendance marked successfully',
                        'attendance_id': attendance_id,
                        'liveness_status': {
                            'success': bool(verification_result.get('success', False)),
                            'message': str(verification_result.get('message', '')),
                            'liveness_verified': bool(verification_result.get('liveness_verified', False)),
                            'face_match': bool(verification_result.get('face_match', False)),
                            'blink_count': int(verification_result.get('blink_count', 0)),
                            'head_moved': bool(verification_result.get('head_moved', False))
                        }
                    })
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to mark attendance'})
        else:
            # Face verification failed - provide specific and encouraging messages
            face_match = verification_result.get('face_match', False)
            liveness_verified = verification_result.get('liveness_verified', False)
            blink_count = verification_result.get('blink_count', 0)
            head_moved = verification_result.get('head_moved', False)
            
            # Determine the specific failure type and provide appropriate message
            if not face_match:
                # Face not detected or doesn't match
                error_message = "Face not detected or doesn't match your profile. Please try scanning again with better lighting and make sure your face is clearly visible in the camera."
                prompt_message = "👆 Please scan your face again! Make sure your face is clearly visible and well-lit."
            elif not liveness_verified:
                # Face matches but liveness failed
                if blink_count == 0 and not head_moved:
                    error_message = "Face matches but liveness verification failed. Please blink naturally and move your head slightly during scanning."
                    prompt_message = "👆 Please scan again! This time, blink naturally and move your head slightly while looking at the camera."
                elif blink_count == 0:
                    error_message = "Face matches but please blink naturally during scanning for liveness verification."
                    prompt_message = "👆 Please scan again! This time, blink naturally while looking at the camera."
                elif not head_moved:
                    error_message = "Face matches but please move your head slightly during scanning for liveness verification."
                    prompt_message = "👆 Please scan again! This time, move your head slightly (left-right or up-down) while looking at the camera."
                else:
                    error_message = "Face matches but liveness verification failed. Please try scanning again with natural movements."
                    prompt_message = "👆 Please scan again! Make natural movements like blinking and slight head movements."
            else:
                # Other verification issues
                error_message = f"Face verification failed: {verification_result.get('message', 'Unknown error')}"
                prompt_message = "👆 Please try scanning your face again!"
            
            # Get current liveness status for debugging
            liveness_status = face_recognition_advanced.get_liveness_status(user_id)
            
            return JsonResponse({
                'status': 'error', 
                'message': error_message,
                'prompt_message': prompt_message,
                'retry_required': True,
                'liveness_status': {
                    'success': bool(verification_result.get('success', False)),
                    'message': str(verification_result.get('message', '')),
                    'liveness_verified': bool(liveness_verified),
                    'face_match': bool(face_match),
                    'blink_count': int(blink_count),
                    'head_moved': bool(head_moved)
                },
                'details': {
                    'success': bool(verification_result.get('success', False)),
                    'message': str(verification_result.get('message', '')),
                    'liveness_verified': bool(liveness_verified),
                    'face_match': bool(face_match),
                    'blink_count': int(blink_count),
                    'head_moved': bool(head_moved),
                    'failure_type': 'face_not_detected' if not face_match else 'liveness_failed'
                }
            })
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error during face verification: {str(e)}'})

def compare_face_encodings(stored_encoding, provided_encoding):
    """Compare face encodings using face_recognition library"""
    try:
        # Validate both encodings
        if not validate_face_encoding(stored_encoding):
            print("Invalid stored face encoding")
            return False
        
        if not validate_face_encoding(provided_encoding):
            print("Invalid provided face encoding")
            return False
        
        # Use face_recognition library for comparison
        from .face_utils import compare_face_encodings as face_compare
        match = face_compare(stored_encoding, provided_encoding, tolerance=0.6)
        
        print(f"Face comparison result: {match}")
        return match
        
    except Exception as e:
        print(f"Error comparing face encodings: {e}")
        return False

def get_liveness_status(request):
    """Get current liveness detection status for the user"""
    try:
        user_id = str(request.user.id)
        liveness_status = face_recognition_advanced.get_liveness_status(user_id)
        
        return JsonResponse({
            'status': 'success',
            'liveness_status': liveness_status
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error getting liveness status: {str(e)}'
        })

def reset_liveness(request):
    """Reset liveness detection state for the user"""
    try:
        user_id = str(request.user.id)
        face_recognition_advanced.reset_user_liveness(user_id)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Liveness state reset successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error resetting liveness state: {str(e)}'
        })

def mark_attendance(request, data):
    """Mark student attendance and create bidirectional records (student + faculty sides)"""
    try:
        from datetime import date, time
        from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail
        
        # Get student profile
        try:
            student = request.user.student_profile
            print(f"Student found: {student.name} (Roll: {student.roll_number})")
        except Exception as e:
            print(f"Error getting student profile: {e}")
            return {'error': True, 'message': 'Student profile not found'}
        
        qr_data = data.get('qr_data', {})
        today = date.today()
        print(f"QR Data received: {qr_data}")
        print(f"QR Data type: {type(qr_data)}")
        print(f"QR Data keys: {list(qr_data.keys()) if isinstance(qr_data, dict) else 'Not a dict'}")
        
        # Get teacher from QR data
        teacher_roll_no = qr_data.get('teacher_roll_no')
        print(f"Looking for teacher with roll_no: {teacher_roll_no}")
        teacher = None
        if teacher_roll_no:
            teacher = Teacher.objects.filter(roll_no=teacher_roll_no).first()
            if teacher:
                print(f"Teacher found: {teacher.name} (Roll: {teacher.roll_no}, ID: {teacher.id})")
            else:
                print(f"Teacher not found with roll_no: {teacher_roll_no}")
                # Check if there are any teachers in the database
                all_teachers = Teacher.objects.all()
                print(f"Available teachers in database:")
                for t in all_teachers:
                    print(f"  - ID: {t.id}, Roll: {t.roll_no}, Name: {t.name}")
                
                # Try to create a default teacher if not found
                teacher = Teacher.objects.create(
                    roll_no=teacher_roll_no,
                    name=f"Teacher {teacher_roll_no}",
                    email=f"teacher{teacher_roll_no}@example.com"
                )
                print(f"Created default teacher: {teacher.name} (Roll: {teacher.roll_no}, ID: {teacher.id})")
        else:
            print("No teacher_roll_no found in QR data")
        
        # Get subject from QR data
        subject_code = qr_data.get('subject_id')
        print(f"Looking for subject with code: {subject_code}")
        subject = None
        if subject_code:
            subject = Subject.objects.filter(code=subject_code).first()
            if subject:
                print(f"Subject found: {subject.name} (Code: {subject.code})")
            else:
                print(f"Subject not found with code: {subject_code}")
                return {
                    'error': True,
                    'message': f'Unknown subject code in QR: {subject_code}. Please regenerate the QR with a valid subject.'
                }
        else:
            print("No subject_id found in QR data")
            return {
                'error': True,
                'message': 'QR missing subject_id. Please regenerate the QR with a subject.'
            }
        
        # Get group from QR, but enforce student's own group to avoid cross-group marking
        group_id = qr_data.get('class_id')
        group_from_qr = None
        if group_id:
            try:
                group_from_qr = Group.objects.filter(id=int(group_id)).first()
                if group_from_qr:
                    print(f"Group from QR: {group_from_qr.stream} - {group_from_qr.name} (ID: {group_from_qr.id})")
                else:
                    print(f"Group not found with ID: {group_id}")
            except (ValueError, TypeError):
                print(f"Invalid group ID: {group_id}")

        # Always use the student's assigned group for saving the record
        group = student.group
        if group_from_qr and group_from_qr.id != group.id:
            print(
                f"QR group ({group_from_qr.id}) does not match student's group ({group.id}). "
                "Proceeding with student's group to prevent cross-group attendance."
            )
        
        # Check if attendance already marked for today
        existing_attendance = AttendanceRecord.objects.filter(
            student=student,
            attendance_date=today,
            status='present'
        )
        # Only block duplicates for the same subject on the same day
        if subject:
            existing_attendance = existing_attendance.filter(subject=subject)
        
        if existing_attendance.exists():
            # Attendance already marked for today
            existing_record = existing_attendance.first()
            print(f"Attendance already marked at: {existing_record.attendance_time}")
            return {
                'error': True,
                'message': f'Attendance already marked for today at {existing_record.attendance_time.strftime("%I:%M %p")}',
                'existing_record': existing_record
            }
        
        # Create student-side attendance record with retry logic
        print("Creating student attendance record...")
        max_retries = 3
        attendance_record = None
        
        for attempt in range(max_retries):
            try:
                attendance_record = AttendanceRecord.objects.create(
                    student=student,
                    teacher=teacher,
                    subject=subject,
                    group=group,
                    status='present',
                    qr_data=qr_data,
                    face_verified=True
                )
                print(f"Student attendance record created successfully with ID: {attendance_record.id}")
                break
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    import time
                    print(f"Database locked on attendance creation attempt {attempt + 1}, retrying...")
                    time.sleep(1)
                    continue
                else:
                    raise e
        
        if not attendance_record:
            return {'error': True, 'message': 'Failed to create attendance record after multiple attempts'}
        
        # Create faculty-side attendance records
        if teacher and subject and group:
            print("Creating faculty-side attendance records...")
            try:
                # Get or create faculty attendance record for this teacher/subject/group/date
                faculty_record, created = FacultyAttendanceRecord.objects.get_or_create(
                    teacher=teacher,
                    subject=subject,
                    group=group,
                    attendance_date=today,
                    defaults={
                        'qr_data': qr_data,
                        'total_students': group.student_set.count(),
                        'present_students': 0,
                        'absent_students': group.student_set.count()
                    }
                )
                
                if created:
                    print(f"Created new faculty attendance record: {faculty_record.id}")
                else:
                    print(f"Using existing faculty attendance record: {faculty_record.id}")
                
                # Create or update faculty attendance detail for this student
                faculty_detail, detail_created = FacultyAttendanceDetail.objects.get_or_create(
                    faculty_record=faculty_record,
                    student=student,
                    defaults={
                        'status': 'present',
                        'face_verified': True,
                        'qr_data': qr_data
                    }
                )
                
                if detail_created:
                    print(f"Created faculty attendance detail for student: {student.name}")
                else:
                    # Update existing detail if it was absent before
                    if faculty_detail.status == 'absent':
                        faculty_detail.status = 'present'
                        faculty_detail.face_verified = True
                        faculty_detail.qr_data = qr_data
                        faculty_detail.save()
                        print(f"Updated faculty attendance detail for student: {student.name}")
                
                # Update faculty record counts
                present_count = FacultyAttendanceDetail.objects.filter(
                    faculty_record=faculty_record,
                    status='present'
                ).count()
                
                total_students = group.student_set.count()
                absent_count = total_students - present_count
                
                faculty_record.present_students = present_count
                faculty_record.absent_students = absent_count
                faculty_record.total_students = total_students
                faculty_record.save()
                
                print(f"Updated faculty record counts - Present: {present_count}, Absent: {absent_count}, Total: {total_students}")
                
            except Exception as e:
                print(f"Error creating faculty attendance records: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail the entire process if faculty records fail
        
        # Send data to teacher (you can implement notification system here)
        if teacher:
            send_attendance_notification_to_teacher(teacher, student, attendance_record)
        
        return attendance_record
        
    except Exception as e:
        print(f"Error marking attendance: {e}")
        import traceback
        traceback.print_exc()
        return {'error': True, 'message': f'Error marking attendance: {str(e)}'}

def send_attendance_notification_to_teacher(teacher, student, attendance_record):
    """Send attendance data to teacher with real-time notification"""
    try:
        from faculty.models import TeacherNotification
        
        # Create a notification record for the teacher
        notification = TeacherNotification.objects.create(
            teacher=teacher,
            student=student,
            attendance_record=attendance_record,
            message=f"{student.name} ({student.roll_number}) marked attendance for {attendance_record.subject.name if attendance_record.subject else 'Unknown Subject'}",
            notification_type='attendance_marked',
            is_read=False
        )
        
        print(f"✅ Notification created for teacher {teacher.name}: {notification.message}")
        
        # You can add additional notification methods here:
        # - Email notification
        # - SMS notification  
        # - Push notification
        # - WebSocket real-time notification
        
        return notification
        
    except Exception as e:
        print(f"❌ Error creating notification: {e}")
        # Fallback to simple print
        print(f"Attendance marked for {student.name} in {attendance_record.group} - Teacher: {teacher.name}")
        return None

@login_required
def test_face_encoding_view(request):
    """Test view to verify face encoding functionality"""
    user = request.user
    
    context = {
        'user': user,
        'has_face_encoding': bool(user.face_encoding),
        'face_encoding_length': len(json.loads(user.face_encoding)) if user.face_encoding else 0,
    }
    
    if request.method == 'POST':
        # Test face comparison
        try:
            test_encoding_data = request.POST.get('test_encoding')
            if test_encoding_data and user.face_encoding:
                test_encoding = json.loads(test_encoding_data)
                stored_encoding = json.loads(user.face_encoding)
                
                # Use the face comparison function
                from .face_utils_simple import compare_face_encodings
                match = compare_face_encodings(stored_encoding, test_encoding)
                
                context['test_result'] = {
                    'match': match,
                    'test_encoding_length': len(test_encoding),
                    'stored_encoding_length': len(stored_encoding)
                }
                
                messages.success(request, f"Face comparison test completed. Match: {match}")
            else:
                messages.error(request, "Missing test encoding or user face encoding")
        except Exception as e:
            messages.error(request, f"Error in face comparison test: {str(e)}")
    
    return render(request, "student/test_face_encoding.html", context)

@login_required
def qr_success_view(request):
    # Get student information
    student_profile = None
    student_group = None
    qr_data = None
    scan_info = None
    error_message = None
    
    try:
        student_profile = request.user.student_profile
        student_group = student_profile.group
    except Student.DoesNotExist:
        pass
    
    if request.method == 'POST':
        # Handle storing successful QR scan data
        import json
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            if not data.get('qr_data'):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: missing qr_data field'})
            
            qr_data_dict = data.get('qr_data', {})
            if not qr_data_dict.get('start_time'):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: missing start_time field'})
            
            # Validate start_time is a valid integer
            try:
                int(qr_data_dict.get('start_time'))
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid QR data: start_time must be a valid timestamp'})
            
            request.session['success_qr_data'] = data
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error processing QR data: {str(e)}'})
    
    # Get QR data from session if available
    qr_data = request.session.get('success_qr_data', None)
    qr_data_dict = None
    
    # Calculate scan information if QR data is available
    if qr_data:
        try:
            import time
            current_time = int(time.time())
            qr_data_dict = qr_data.get('qr_data', {})
            start_time = int(qr_data_dict.get('start_time', 0))
            time_diff = current_time - start_time
            
            # Validate time difference is reasonable (not negative or too large)
            if time_diff < 0:
                error_message = "Invalid QR data: scan time is before generation time"
            elif time_diff > 3600:  # More than 1 hour
                error_message = "QR data appears to be very old"
            else:
                # Convert start_time to datetime for template display
                from datetime import datetime
                qr_data_dict['generated_time'] = datetime.fromtimestamp(start_time)
                
                # Add scanning time - use current server time for accuracy
                qr_data_dict['scan_time'] = datetime.now()
                
                scan_info = {
                    'subject_id': qr_data_dict.get('subject_id', 'N/A'),
                    'student_id': request.user.student_profile.id if hasattr(request.user, 'student_profile') else request.user.id,
                    'scan_timestamp': current_time,
                    'time_difference': time_diff,
                    'start_time': start_time,
                    'generated_time': datetime.fromtimestamp(start_time),
                    'scan_time': datetime.now(),
                    'class_id': qr_data_dict.get('class_id', 'N/A'),
                    'teacher_roll_no': qr_data_dict.get('teacher_roll_no', 'N/A'),
                }
        except (ValueError, TypeError) as e:
            error_message = f"Invalid timestamp data: {str(e)}"
        except Exception as e:
            error_message = f"Error processing scan info: {str(e)}"
    
    context = {
        'student_profile': student_profile,
        'student_group': student_group,
        'qr_data': qr_data_dict,  # Pass the actual QR data dict, not the wrapper
        'scan_info': scan_info,
        'error_message': error_message,
    }
    return render(request, "student/qr_success.html", context)

@login_required
def debug_attendance(request):
    """Debug view to check attendance records and database state"""
    from student.models import AttendanceRecord, Teacher, Subject, Student, Group
    
    context = {
        'total_records': AttendanceRecord.objects.count(),
        'today_records': AttendanceRecord.objects.filter(attendance_date=date.today()).count(),
        'recent_records': AttendanceRecord.objects.select_related('student', 'teacher', 'subject', 'group').order_by('-created_at')[:10],
        'students_count': Student.objects.count(),
        'teachers_count': Teacher.objects.count(),
        'subjects_count': Subject.objects.count(),
        'groups_count': Group.objects.count(),
    }
    
    return render(request, "student/debug_attendance.html", context)

@login_required
def student_courses(request):
    """View to show courses/subjects assigned to the student's group only"""
    user = request.user
    
    # Get the student profile for this user
    student_profile = None
    student_subjects = []
    student_group = None
    
    try:
        student_profile = user.student_profile
        student_group = student_profile.group
        student_subjects = student_profile.subjects
    except Student.DoesNotExist:
        pass
    
    context = {
        'student_profile': student_profile,
        'student_subjects': student_subjects,
        'student_group': student_group,
        'total_subjects': len(student_subjects),
    }
    return render(request, "student/courses.html", context)

@login_required
def student_attendance_analytics(request):
    """Render comprehensive student attendance analytics with weekly, monthly, and all-time data."""
    user = request.user
    today = date.today()
    
    # Get student profile
    try:
        student = user.student_profile
    except Student.DoesNotExist:
        return render(request, "student/attendance_analytics.html", {
            "error": "Student profile not found",
            "overall_attendance": 0,
            "total_present": 0,
            "total_absent": 0,
            "total_late": 0,
            "records": [],
        })

    # Get actual attendance records from the database
    attendance_records = AttendanceRecord.objects.filter(
        student=student
    ).select_related('teacher', 'subject', 'group').order_by('-attendance_date', '-attendance_time')
    
    # Calculate overall statistics
    total_records = attendance_records.count()
    present_records = attendance_records.filter(status='present')
    absent_records = attendance_records.filter(status='absent')
    
    present_count = present_records.count()
    absent_count = absent_records.count()
    late_count = 0  # You can add late status logic if needed
    
    # Calculate overall attendance rate
    if total_records > 0:
        attendance_rate = round((present_count / total_records) * 100, 1)
    else:
        attendance_rate = 0
    
    # Get date ranges
    from datetime import timedelta
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ago = today - timedelta(days=7)
    ninety_days_ago = today - timedelta(days=90)
    
    # Calculate weekly statistics (last 7 days)
    weekly_records = attendance_records.filter(attendance_date__gte=seven_days_ago)
    weekly_present = weekly_records.filter(status='present').count()
    weekly_total = weekly_records.count()
    weekly_attendance_rate = round((weekly_present / weekly_total) * 100, 1) if weekly_total > 0 else 0
    
    # Calculate monthly statistics (last 30 days)
    monthly_records = attendance_records.filter(attendance_date__gte=thirty_days_ago)
    monthly_present = monthly_records.filter(status='present').count()
    monthly_total = monthly_records.count()
    monthly_attendance_rate = round((monthly_present / monthly_total) * 100, 1) if monthly_total > 0 else 0
    
    # Calculate quarterly statistics (last 90 days)
    quarterly_records = attendance_records.filter(attendance_date__gte=ninety_days_ago)
    quarterly_present = quarterly_records.filter(status='present').count()
    quarterly_total = quarterly_records.count()
    quarterly_attendance_rate = round((quarterly_present / quarterly_total) * 100, 1) if quarterly_total > 0 else 0
    
    # Get recent records (last 30 days) for detailed table
    recent_records = attendance_records.filter(attendance_date__gte=thirty_days_ago)
    
    # Format records for template
    records = []
    for record in recent_records:
        records.append({
            "date": record.attendance_date.strftime("%Y-%m-%d"),
            "class": f"{record.group.stream} - {record.group.name}" if record.group else "N/A",
            "subject": record.subject.name if record.subject else "N/A",
            "teacher": record.teacher.name if record.teacher else "N/A",
            "status": record.status.title(),
            "time": record.attendance_time.strftime("%I:%M %p") if record.attendance_time else "-",
            "face_verified": "✅" if record.face_verified else "❌",
            "notes": f"QR: {record.qr_data.get('mode', 'N/A')}" if record.qr_data else "-",
        })
    
    # Get today's status
    today_record = attendance_records.filter(attendance_date=today).first()
    is_present_today = today_record and today_record.status == 'present'
    
    # Get weekly attendance trend (last 7 days)
    weekly_trend = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        day_record = attendance_records.filter(attendance_date=target_date).first()
        weekly_trend.append({
            "date": target_date.strftime("%m/%d"),
            "day_name": target_date.strftime("%a"),
            "status": day_record.status if day_record else "absent",
            "present": 1 if day_record and day_record.status == 'present' else 0
        })
    
    # Get monthly attendance trend (last 30 days)
    monthly_trend = []
    for i in range(29, -1, -1):
        target_date = today - timedelta(days=i)
        day_record = attendance_records.filter(attendance_date=target_date).first()
        monthly_trend.append({
            "date": target_date.strftime("%m/%d"),
            "status": day_record.status if day_record else "absent",
            "present": 1 if day_record and day_record.status == 'present' else 0
        })
    
    # Calculate monthly trend statistics
    monthly_trend_present = sum(day['present'] for day in monthly_trend)
    monthly_trend_rate = round((monthly_trend_present / 30) * 100, 1) if monthly_trend else 0
    
    # Get subject-wise attendance (ensure all assigned subjects appear)
    # Use subject.code as stable key to avoid mismatches in names
    subject_stats = {}
    # Pre-seed from assigned subjects
    for subj in student.subjects:
        subject_stats[subj.code] = {
            "display_name": subj.name,
            "present": 0, "absent": 0, "total": 0,
            "weekly_present": 0, "weekly_total": 0,
            "monthly_present": 0, "monthly_total": 0
        }
    # Fill using attendance records (by subject code)
    for record in attendance_records:
        subj_code = record.subject.code if record.subject else "UNKNOWN"
        subj_name = record.subject.name if record.subject else "Unknown"
        if subj_code not in subject_stats:
            subject_stats[subj_code] = {
                "display_name": subj_name,
                "present": 0, "absent": 0, "total": 0,
                "weekly_present": 0, "weekly_total": 0,
                "monthly_present": 0, "monthly_total": 0
            }
        stats = subject_stats[subj_code]
        stats["total"] += 1
        if record.status == 'present':
            stats["present"] += 1
        else:
            stats["absent"] += 1
        if record.attendance_date >= seven_days_ago:
            stats["weekly_total"] += 1
            if record.status == 'present':
                stats["weekly_present"] += 1
        if record.attendance_date >= thirty_days_ago:
            stats["monthly_total"] += 1
            if record.status == 'present':
                stats["monthly_present"] += 1
    
    # Calculate subject-wise attendance rates
    for subject_name, stats in subject_stats.items():
        if stats["total"] > 0:
            stats["overall_rate"] = round((stats["present"] / stats["total"]) * 100, 1)
        else:
            stats["overall_rate"] = 0
            
        if stats["weekly_total"] > 0:
            stats["weekly_rate"] = round((stats["weekly_present"] / stats["weekly_total"]) * 100, 1)
        else:
            stats["weekly_rate"] = 0
            
        if stats["monthly_total"] > 0:
            stats["monthly_rate"] = round((stats["monthly_present"] / stats["monthly_total"]) * 100, 1)
        else:
            stats["monthly_rate"] = 0
    
    # Get teacher-wise attendance
    teacher_stats = {}
    for record in attendance_records:
        teacher_name = record.teacher.name if record.teacher else "Unknown"
        if teacher_name not in teacher_stats:
            teacher_stats[teacher_name] = {"present": 0, "absent": 0, "total": 0}
        
        teacher_stats[teacher_name]["total"] += 1
        if record.status == 'present':
            teacher_stats[teacher_name]["present"] += 1
        else:
            teacher_stats[teacher_name]["absent"] += 1
    
    # Calculate teacher-wise attendance rates
    for teacher_name, stats in teacher_stats.items():
        if stats["total"] > 0:
            stats["rate"] = round((stats["present"] / stats["total"]) * 100, 1)
        else:
            stats["rate"] = 0
    
    # Get attendance patterns (day of week analysis)
    day_patterns = {}
    for record in attendance_records:
        day_name = record.attendance_date.strftime("%A")
        if day_name not in day_patterns:
            day_patterns[day_name] = {"present": 0, "total": 0}
        
        day_patterns[day_name]["total"] += 1
        if record.status == 'present':
            day_patterns[day_name]["present"] += 1
    
    # Calculate day-wise attendance rates
    for day_name, stats in day_patterns.items():
        if stats["total"] > 0:
            stats["rate"] = round((stats["present"] / stats["total"]) * 100, 1)
        else:
            stats["rate"] = 0
    
    # Get attendance streaks
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    # Calculate current streak (from today backwards)
    for i in range(30):  # Check last 30 days
        check_date = today - timedelta(days=i)
        day_record = attendance_records.filter(attendance_date=check_date).first()
        
        if day_record and day_record.status == 'present':
            if i == 0:  # Today
                current_streak = 1
                temp_streak = 1
            else:
                current_streak += 1
                temp_streak += 1
        else:
            if i == 0:  # Today is absent
                current_streak = 0
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 0
    
    longest_streak = max(longest_streak, temp_streak)
    
    # Get attendance by month (for yearly view)
    monthly_breakdown = {}
    for record in attendance_records:
        month_key = record.attendance_date.strftime("%Y-%m")
        month_name = record.attendance_date.strftime("%B %Y")
        
        if month_key not in monthly_breakdown:
            monthly_breakdown[month_key] = {
                "name": month_name,
                "present": 0,
                "total": 0
            }
        
        monthly_breakdown[month_key]["total"] += 1
        if record.status == 'present':
            monthly_breakdown[month_key]["present"] += 1
    
    # Calculate monthly breakdown rates
    for month_key, stats in monthly_breakdown.items():
        if stats["total"] > 0:
            stats["rate"] = round((stats["present"] / stats["total"]) * 100, 1)
        else:
            stats["rate"] = 0

    context = {
        # Overall statistics
        "overall_attendance": attendance_rate,
        "total_present": present_count,
        "total_absent": absent_count,
        "total_late": late_count,
        "total_records": total_records,
        
        # Time-based statistics
        "weekly_attendance": weekly_attendance_rate,
        "monthly_attendance": monthly_attendance_rate,
        "quarterly_attendance": quarterly_attendance_rate,
        
        # Weekly and monthly data
        "weekly_present": weekly_present,
        "weekly_total": weekly_total,
        "monthly_present": monthly_present,
        "monthly_total": monthly_total,
        "quarterly_present": quarterly_present,
        "quarterly_total": quarterly_total,
        
        # Trends and patterns
        "weekly_trend": weekly_trend,
        "monthly_trend": monthly_trend,
        "monthly_trend_rate": monthly_trend_rate,
        
        # Subject and teacher statistics
        "subject_stats": subject_stats,
        "teacher_stats": teacher_stats,
        
        # Patterns and streaks
        "day_patterns": day_patterns,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        
        # Monthly breakdown
        "monthly_breakdown": monthly_breakdown,
        
        # Today's status
        "is_present_today": is_present_today,
        "today_status": today_record.status if today_record else "absent",
        
        # Student info
        "student_profile": student,
        "last_attendance": attendance_records.first() if attendance_records.exists() else None,
        "records": records,
    }
    return render(request, "student/attendance_analytics.html", context)



# Logout
@login_required
def logout_view(request):
    logout(request)
    return redirect("login")
