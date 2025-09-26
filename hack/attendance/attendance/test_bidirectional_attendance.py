#!/usr/bin/env python
"""
Test script for bidirectional attendance system
This script tests the new faculty attendance models and bidirectional marking
"""

import os
import sys
import django
from datetime import date, time

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance.settings')
django.setup()

from student.models import User, Student, Teacher, Subject, Group, AttendanceRecord
from faculty.models import FacultyAttendanceRecord, FacultyAttendanceDetail

def test_bidirectional_attendance():
    """Test the bidirectional attendance system"""
    print("🧪 Testing Bidirectional Attendance System")
    print("=" * 50)
    
    # Test 1: Check if faculty models exist
    print("\n1. Testing Faculty Models...")
    try:
        faculty_records_count = FacultyAttendanceRecord.objects.count()
        faculty_details_count = FacultyAttendanceDetail.objects.count()
        print(f"✅ FacultyAttendanceRecord count: {faculty_records_count}")
        print(f"✅ FacultyAttendanceDetail count: {faculty_details_count}")
    except Exception as e:
        print(f"❌ Error accessing faculty models: {e}")
        return False
    
    # Test 2: Check existing data
    print("\n2. Checking Existing Data...")
    try:
        students_count = Student.objects.count()
        teachers_count = Teacher.objects.count()
        subjects_count = Subject.objects.count()
        groups_count = Group.objects.count()
        attendance_records_count = AttendanceRecord.objects.count()
        
        print(f"📊 Students: {students_count}")
        print(f"📊 Teachers: {teachers_count}")
        print(f"📊 Subjects: {subjects_count}")
        print(f"📊 Groups: {groups_count}")
        print(f"📊 Attendance Records: {attendance_records_count}")
        
        if students_count == 0 or teachers_count == 0:
            print("⚠️  No students or teachers found. Please add some test data first.")
            return False
            
    except Exception as e:
        print(f"❌ Error checking existing data: {e}")
        return False
    
    # Test 3: Test faculty record creation
    print("\n3. Testing Faculty Record Creation...")
    try:
        # Get first teacher, subject, and group
        teacher = Teacher.objects.first()
        subject = Subject.objects.first()
        group = Group.objects.first()
        
        if not all([teacher, subject, group]):
            print("❌ Missing required data (teacher, subject, or group)")
            return False
        
        # Create a test faculty record
        faculty_record, created = FacultyAttendanceRecord.objects.get_or_create(
            teacher=teacher,
            subject=subject,
            group=group,
            attendance_date=date.today(),
            defaults={
                'total_students': group.student_set.count(),
                'present_students': 0,
                'absent_students': group.student_set.count(),
                'qr_data': {'test': True, 'mode': 'test'}
            }
        )
        
        if created:
            print(f"✅ Created new faculty record: {faculty_record.id}")
        else:
            print(f"✅ Using existing faculty record: {faculty_record.id}")
        
        print(f"📊 Faculty Record - Present: {faculty_record.present_students}, Absent: {faculty_record.absent_students}, Total: {faculty_record.total_students}")
        
    except Exception as e:
        print(f"❌ Error creating faculty record: {e}")
        return False
    
    # Test 4: Test faculty detail creation
    print("\n4. Testing Faculty Detail Creation...")
    try:
        # Get first student
        student = Student.objects.first()
        if not student:
            print("❌ No students found")
            return False
        
        # Create a test faculty detail
        faculty_detail, created = FacultyAttendanceDetail.objects.get_or_create(
            faculty_record=faculty_record,
            student=student,
            defaults={
                'status': 'present',
                'face_verified': True,
                'qr_data': {'test': True, 'student_id': student.id}
            }
        )
        
        if created:
            print(f"✅ Created new faculty detail for student: {student.name}")
        else:
            print(f"✅ Using existing faculty detail for student: {student.name}")
        
        print(f"📊 Faculty Detail - Student: {faculty_detail.student.name}, Status: {faculty_detail.status}")
        
    except Exception as e:
        print(f"❌ Error creating faculty detail: {e}")
        return False
    
    # Test 5: Test attendance percentage calculation
    print("\n5. Testing Attendance Percentage Calculation...")
    try:
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
        
        print(f"✅ Updated faculty record counts")
        print(f"📊 Present: {present_count}, Absent: {absent_count}, Total: {total_students}")
        print(f"📊 Attendance Percentage: {faculty_record.attendance_percentage}%")
        
    except Exception as e:
        print(f"❌ Error updating attendance percentage: {e}")
        return False
    
    # Test 6: Test bidirectional relationship
    print("\n6. Testing Bidirectional Relationship...")
    try:
        # Check if we can access faculty records from teacher
        teacher_faculty_records = teacher.faculty_attendance_records.count()
        print(f"✅ Teacher {teacher.name} has {teacher_faculty_records} faculty attendance records")
        
        # Check if we can access faculty details from student
        student_faculty_details = student.faculty_attendance_details.count()
        print(f"✅ Student {student.name} has {student_faculty_details} faculty attendance details")
        
        # Check if we can access attendance details from faculty record
        record_details_count = faculty_record.attendance_details.count()
        print(f"✅ Faculty record has {record_details_count} attendance details")
        
    except Exception as e:
        print(f"❌ Error testing bidirectional relationship: {e}")
        return False
    
    print("\n🎉 All tests passed! Bidirectional attendance system is working correctly.")
    return True

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    try:
        # Delete test faculty records
        test_records = FacultyAttendanceRecord.objects.filter(qr_data__test=True)
        test_count = test_records.count()
        test_records.delete()
        print(f"✅ Deleted {test_count} test faculty records")
        
        # Delete test faculty details
        test_details = FacultyAttendanceDetail.objects.filter(qr_data__test=True)
        test_detail_count = test_details.count()
        test_details.delete()
        print(f"✅ Deleted {test_detail_count} test faculty details")
        
    except Exception as e:
        print(f"❌ Error cleaning up test data: {e}")

if __name__ == "__main__":
    try:
        success = test_bidirectional_attendance()
        if success:
            print("\n✅ Bidirectional attendance system test completed successfully!")
        else:
            print("\n❌ Bidirectional attendance system test failed!")
        
        # Ask user if they want to clean up test data
        cleanup_choice = input("\nDo you want to clean up test data? (y/n): ").lower().strip()
        if cleanup_choice in ['y', 'yes']:
            cleanup_test_data()
            
    except Exception as e:
        print(f"\n❌ Test script failed with error: {e}")
        import traceback
        traceback.print_exc()
