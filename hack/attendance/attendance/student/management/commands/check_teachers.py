from django.core.management.base import BaseCommand
from student.models import Teacher, Subject, User

class Command(BaseCommand):
    help = 'Check teachers in the database and their information'

    def handle(self, *args, **options):
        self.stdout.write("=== TEACHER DATABASE CHECK ===")
        
        # Check all teachers
        teachers = Teacher.objects.all()
        self.stdout.write(f"Total teachers in database: {teachers.count()}")
        
        if teachers.count() == 0:
            self.stdout.write(self.style.WARNING("No teachers found in database!"))
            return
        
        for teacher in teachers:
            self.stdout.write(f"\nTeacher: {teacher.name}")
            self.stdout.write(f"  Roll No: {teacher.roll_no}")
            self.stdout.write(f"  Email: {teacher.email}")
            self.stdout.write(f"  Subject ID: {teacher.subject_id}")
            self.stdout.write(f"  User: {teacher.user.username if teacher.user else 'No user linked'}")
            self.stdout.write(f"  Groups: {[f'{g.stream}-{g.name}' for g in teacher.groups.all()]}")
        
        # Check for T002 specifically
        t002 = Teacher.objects.filter(roll_no="T002").first()
        if t002:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Teacher T002 found: {t002.name}"))
            self.stdout.write(f"   Subject ID: {t002.subject_id}")
            self.stdout.write(f"   User: {t002.user.username if t002.user else 'No user linked'}")
        else:
            self.stdout.write(self.style.ERROR("\n❌ Teacher T002 not found!"))
            self.stdout.write("Available roll numbers:")
            for teacher in teachers:
                self.stdout.write(f"  - {teacher.roll_no}")
        
        # Check subjects
        self.stdout.write(f"\n=== SUBJECTS ===")
        subjects = Subject.objects.all()
        self.stdout.write(f"Total subjects: {subjects.count()}")
        for subject in subjects:
            self.stdout.write(f"  {subject.code} - {subject.name}")
        
        # Check users with faculty role
        self.stdout.write(f"\n=== FACULTY USERS ===")
        faculty_users = User.objects.filter(role="faculty")
        self.stdout.write(f"Total faculty users: {faculty_users.count()}")
        for user in faculty_users:
            teacher_profile = getattr(user, 'teacher_profile', None)
            self.stdout.write(f"  {user.username} - {user.email}")
            if teacher_profile:
                self.stdout.write(f"    Teacher Profile: {teacher_profile.name} (Roll: {teacher_profile.roll_no})")
            else:
                self.stdout.write(f"    No teacher profile linked")
