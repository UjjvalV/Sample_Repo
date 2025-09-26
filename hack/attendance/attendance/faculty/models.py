from django.db import models
from student.models import Teacher, Subject, Group, Student

# Create your models here.
# Faculty-specific models can be added here

class FacultyAttendanceRecord(models.Model):
    """Faculty-side attendance tracking model"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='faculty_attendance_records')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='faculty_attendance_records')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='faculty_attendance_records')
    attendance_date = models.DateField(auto_now_add=True)
    attendance_time = models.TimeField(auto_now_add=True)
    total_students = models.IntegerField(default=0)
    present_students = models.IntegerField(default=0)
    absent_students = models.IntegerField(default=0)
    attendance_percentage = models.FloatField(default=0.0)
    qr_data = models.JSONField(null=True, blank=True)  # Store QR code data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['teacher', 'subject', 'group', 'attendance_date']
        ordering = ['-attendance_date', '-attendance_time']
    
    def __str__(self):
        return f"{self.teacher.name} - {self.subject.name} - {self.group.name} - {self.attendance_date}"
    
    def save(self, *args, **kwargs):
        # Calculate attendance percentage
        if self.total_students > 0:
            self.attendance_percentage = round((self.present_students / self.total_students) * 100, 2)
        else:
            self.attendance_percentage = 0.0
        super().save(*args, **kwargs)

class FacultyAttendanceDetail(models.Model):
    """Detailed attendance records for faculty view"""
    faculty_record = models.ForeignKey(FacultyAttendanceRecord, on_delete=models.CASCADE, related_name='attendance_details')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='faculty_attendance_details')
    status = models.CharField(max_length=20, choices=[('present', 'Present'), ('absent', 'Absent')], default='present')
    marked_time = models.DateTimeField(auto_now_add=True)
    face_verified = models.BooleanField(default=False)
    qr_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        unique_together = ['faculty_record', 'student']
        ordering = ['-marked_time']
    
    def __str__(self):
        return f"{self.student.name} - {self.status} - {self.faculty_record.attendance_date}"

class TeacherNotification(models.Model):
    """Notifications for teachers when students mark attendance"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='notifications')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='teacher_notifications')
    attendance_record = models.ForeignKey('student.AttendanceRecord', on_delete=models.CASCADE, related_name='teacher_notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('attendance_marked', 'Attendance Marked'),
        ('attendance_updated', 'Attendance Updated'),
        ('system_alert', 'System Alert'),
    ], default='attendance_marked')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.name} - {self.student.name} - {self.notification_type}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save()