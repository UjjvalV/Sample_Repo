from django.core.management.base import BaseCommand
from student.models import AttendanceRecord, Teacher, Subject, Student, Group

class Command(BaseCommand):
    help = 'Check attendance records and verify teacher ID and subject ID storage'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== ATTENDANCE RECORD ANALYSIS ==='))
        
        # Check total records
        total_records = AttendanceRecord.objects.count()
        self.stdout.write(f"Total Attendance Records: {total_records}")
        
        if total_records == 0:
            self.stdout.write(self.style.WARNING("No attendance records found in database."))
            return
        
        # Check records with teacher information
        records_with_teacher = AttendanceRecord.objects.filter(teacher__isnull=False).count()
        self.stdout.write(f"Records with Teacher ID: {records_with_teacher}")
        
        # Check records with subject information
        records_with_subject = AttendanceRecord.objects.filter(subject__isnull=False).count()
        self.stdout.write(f"Records with Subject ID: {records_with_subject}")
        
        # Show sample records
        self.stdout.write(self.style.SUCCESS('\n=== SAMPLE RECORDS ==='))
        sample_records = AttendanceRecord.objects.select_related('student', 'teacher', 'subject', 'group').all()[:5]
        
        for i, record in enumerate(sample_records, 1):
            self.stdout.write(f"\nRecord {i}:")
            self.stdout.write(f"  Student: {record.student.name} ({record.student.roll_number})")
            self.stdout.write(f"  Teacher: {record.teacher.name if record.teacher else 'N/A'} (ID: {record.teacher.roll_no if record.teacher else 'N/A'})")
            self.stdout.write(f"  Subject: {record.subject.name if record.subject else 'N/A'} (ID: {record.subject.code if record.subject else 'N/A'})")
            self.stdout.write(f"  Group: {record.group.stream} - {record.group.name} (ID: {record.group.id})")
            self.stdout.write(f"  Date: {record.attendance_date}")
            self.stdout.write(f"  Time: {record.attendance_time}")
            self.stdout.write(f"  QR Data: {record.qr_data}")
            self.stdout.write(f"  Face Verified: {record.face_verified}")
        
        # Check QR data structure
        self.stdout.write(self.style.SUCCESS('\n=== QR DATA ANALYSIS ==='))
        records_with_qr = AttendanceRecord.objects.filter(qr_data__isnull=False).exclude(qr_data={})
        self.stdout.write(f"Records with QR Data: {records_with_qr.count()}")
        
        if records_with_qr.exists():
            sample_qr = records_with_qr.first().qr_data
            self.stdout.write(f"Sample QR Data Structure: {sample_qr}")
            
            # Check what fields are commonly present
            qr_fields = {}
            for record in records_with_qr:
                if record.qr_data:
                    for key in record.qr_data.keys():
                        qr_fields[key] = qr_fields.get(key, 0) + 1
            
            self.stdout.write("\nQR Data Fields Frequency:")
            for field, count in qr_fields.items():
                self.stdout.write(f"  {field}: {count} records")
        
        # Verify teacher and subject data integrity
        self.stdout.write(self.style.SUCCESS('\n=== DATA INTEGRITY CHECK ==='))
        
        # Check for records with teacher_roll_no in QR but no teacher linked
        problematic_records = []
        for record in records_with_qr:
            if record.qr_data and record.qr_data.get('teacher_roll_no') and not record.teacher:
                problematic_records.append(record)
        
        if problematic_records:
            self.stdout.write(self.style.ERROR(f"Found {len(problematic_records)} records with teacher_roll_no in QR data but no teacher linked:"))
            for record in problematic_records[:3]:  # Show first 3
                self.stdout.write(f"  - Student: {record.student.roll_number}, QR Teacher: {record.qr_data.get('teacher_roll_no')}")
        else:
            self.stdout.write(self.style.SUCCESS("✓ All records with teacher_roll_no in QR data have proper teacher links"))
        
        # Check for records with subject_id in QR but no subject linked
        problematic_subjects = []
        for record in records_with_qr:
            if record.qr_data and record.qr_data.get('subject_id') and not record.subject:
                problematic_subjects.append(record)
        
        if problematic_subjects:
            self.stdout.write(self.style.ERROR(f"Found {len(problematic_subjects)} records with subject_id in QR data but no subject linked:"))
            for record in problematic_subjects[:3]:  # Show first 3
                self.stdout.write(f"  - Student: {record.student.roll_number}, QR Subject: {record.qr_data.get('subject_id')}")
        else:
            self.stdout.write(self.style.SUCCESS("✓ All records with subject_id in QR data have proper subject links"))
