from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("faculty", "Faculty"),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    # Optional face data captured at signup
    face_image = models.ImageField(upload_to='faces/', null=True, blank=True)
    face_encoding = models.TextField(null=True, blank=True)

    # Ensure new users are NOT staff/admin by default
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # ✅ Do NOT override superuser values
        if not self.is_superuser:
            if not self.pk:  # only for new users
                if self.role == "faculty":
                    self.is_staff = True
                    self.is_superuser = False
                elif self.role == "student":
                    self.is_staff = False
                    self.is_superuser = False
        else:
            # Ensure superuser can access admin panel
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"


class SiteSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)

    @staticmethod
    def get(key, default=None):
        try:
            return SiteSetting.objects.get(key=key).value
        except SiteSetting.DoesNotExist:
            return default

    @staticmethod
    def set(key, value):
        obj, _ = SiteSetting.objects.update_or_create(
            key=key, defaults={"value": value}
        )
        return obj

class ActiveSession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # One active session per user
    jwt_token = models.TextField()
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.session_id}"

class Group(models.Model):
    name = models.CharField(max_length=50)
    stream = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.stream} - {self.name}"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile", null=True, blank=True)
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.roll_number} - {self.name}"
    @property
    def subjects(self):
        """Get all subjects for this student via their group"""
        return self.group.subjects.all()


class Teacher(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="teacher_profile", 
        null=True, 
        blank=True
    )
    roll_no = models.CharField(max_length=20, unique=True)  # 👈 added field
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    subject_id = models.CharField(max_length=100, blank=True, null=True)
    groups = models.ManyToManyField("Group", related_name="teachers", blank=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100)   # e.g., "Maths", "DBMS"
    code = models.CharField(max_length=20, unique=True)  # e.g., "MTH101"
    groups = models.ManyToManyField(Group, related_name="subjects") 
    # subject can belong to multiple groups

class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    attendance_date = models.DateField(auto_now_add=True)
    attendance_time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('present', 'Present'), ('absent', 'Absent')], default='present')
    qr_data = models.JSONField(null=True, blank=True)  # Store QR code data
    face_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'attendance_date', 'subject']
    
    def __str__(self):
        return f"{self.student.name} - {self.attendance_date} - {self.status}"


