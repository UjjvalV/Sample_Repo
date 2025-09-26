#!/usr/bin/env python
"""
Script to fix teacher T002 issue
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance.settings')
django.setup()

from student.models import Teacher, User

def fix_teacher_t002():
    """Fix teacher T002 issue"""
    
    print("=== FIXING TEACHER T002 ISSUE ===")
    
    # Check if teacher T002 exists
    t002 = Teacher.objects.filter(roll_no="T002").first()
    if t002:
        print(f"✅ Teacher T002 found: {t002.name} (ID: {t002.id})")
        print(f"   Email: {t002.email}")
        print(f"   Subject ID: {t002.subject_id}")
        print(f"   User: {t002.user.username if t002.user else 'No user linked'}")
    else:
        print("❌ Teacher T002 not found, creating...")
        
        # Check if there's a user with username T002
        user_t002 = User.objects.filter(username="T002").first()
        if user_t002:
            print(f"Found user T002: {user_t002.email}")
            # Create teacher and link to user
            t002 = Teacher.objects.create(
                roll_no="T002",
                name="Teacher T002",
                email=user_t002.email,
                subject_id="MTH101",  # Default subject
                user=user_t002
            )
            print(f"✅ Created teacher T002 and linked to user: {t002.name} (ID: {t002.id})")
        else:
            print("No user T002 found, creating teacher without user link")
            t002 = Teacher.objects.create(
                roll_no="T002",
                name="Teacher T002",
                email="teacher.t002@example.com",
                subject_id="MTH101"
            )
            print(f"✅ Created teacher T002: {t002.name} (ID: {t002.id})")
    
    # Show all teachers
    print(f"\n=== ALL TEACHERS ===")
    teachers = Teacher.objects.all()
    for teacher in teachers:
        print(f"ID: {teacher.id} | Roll: {teacher.roll_no} | Name: {teacher.name} | User: {teacher.user.username if teacher.user else 'None'}")
    
    # Check for any teacher with ID 3
    teacher_id_3 = Teacher.objects.filter(id=3).first()
    if teacher_id_3:
        print(f"\n⚠️  Teacher with ID 3: {teacher_id_3.name} (Roll: {teacher_id_3.roll_no})")
        print("This might be the teacher being used instead of T002")
    
    print(f"\n=== SUMMARY ===")
    print(f"Teacher T002 ID: {t002.id}")
    print(f"Teacher T002 Roll: {t002.roll_no}")
    print("Now when you generate QR codes as T002, they should contain the correct teacher information.")

if __name__ == "__main__":
    fix_teacher_t002()
