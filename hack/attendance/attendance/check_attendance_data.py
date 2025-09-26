#!/usr/bin/env python
"""
Script to check what teacher ID and subject ID data is being stored in the database
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance.settings')
django.setup()

from student.models import AttendanceRecord, Teacher, Subject, Student, Group

def check_attendance_data():
    print("=== ATTENDANCE RECORD ANALYSIS ===\n")
    
    # Check total records
    total_records = AttendanceRecord.objects.count()
    print(f"Total Attendance Records: {total_records}")
    
    if total_records == 0:
        print("No attendance records found in database.")
        return
    
    # Check records with teacher information
    records_with_teacher = AttendanceRecord.objects.filter(teacher__isnull=False).count()
    print(f"Records with Teacher ID: {records_with_teacher}")
    
    # Check records with subject information
    records_with_subject = AttendanceRecord.objects.filter(subject__isnull=False).count()
    print(f"Records with Subject ID: {records_with_subject}")
    
    # Show sample records
    print("\n=== SAMPLE RECORDS ===")
    sample_records = AttendanceRecord.objects.select_related('student', 'teacher', 'subject', 'group').all()[:5]
    
    for i, record in enumerate(sample_records, 1):
        print(f"\nRecord {i}:")
        print(f"  Student: {record.student.name} ({record.student.roll_number})")
        print(f"  Teacher: {record.teacher.name if record.teacher else 'N/A'} (ID: {record.teacher.roll_no if record.teacher else 'N/A'})")
        print(f"  Subject: {record.subject.name if record.subject else 'N/A'} (ID: {record.subject.code if record.subject else 'N/A'})")
        print(f"  Group: {record.group.stream} - {record.group.name} (ID: {record.group.id})")
        print(f"  Date: {record.attendance_date}")
        print(f"  Time: {record.attendance_time}")
        print(f"  QR Data: {record.qr_data}")
        print(f"  Face Verified: {record.face_verified}")
    
    # Check QR data structure
    print("\n=== QR DATA ANALYSIS ===")
    records_with_qr = AttendanceRecord.objects.filter(qr_data__isnull=False).exclude(qr_data={})
    print(f"Records with QR Data: {records_with_qr.count()}")
    
    if records_with_qr.exists():
        sample_qr = records_with_qr.first().qr_data
        print(f"Sample QR Data Structure: {sample_qr}")
        
        # Check what fields are commonly present
        qr_fields = {}
        for record in records_with_qr:
            if record.qr_data:
                for key in record.qr_data.keys():
                    qr_fields[key] = qr_fields.get(key, 0) + 1
        
        print("\nQR Data Fields Frequency:")
        for field, count in qr_fields.items():
            print(f"  {field}: {count} records")

if __name__ == "__main__":
    check_attendance_data()
