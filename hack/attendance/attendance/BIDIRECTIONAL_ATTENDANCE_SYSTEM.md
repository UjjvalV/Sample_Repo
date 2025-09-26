# Bidirectional Attendance System

## Overview

The bidirectional attendance system ensures that when a student marks their attendance, records are created on both the **student side** and the **faculty side**, providing comprehensive tracking for both perspectives.

## System Architecture

### Student Side (Existing)
- **Model**: `AttendanceRecord` in `student.models`
- **Purpose**: Tracks individual student attendance
- **Fields**: student, teacher, subject, group, attendance_date, status, qr_data, face_verified

### Faculty Side (New)
- **Model**: `FacultyAttendanceRecord` in `faculty.models`
- **Purpose**: Tracks attendance from teacher's perspective
- **Fields**: teacher, subject, group, attendance_date, total_students, present_students, absent_students, attendance_percentage

- **Model**: `FacultyAttendanceDetail` in `faculty.models`
- **Purpose**: Detailed student-by-student attendance for faculty view
- **Fields**: faculty_record, student, status, marked_time, face_verified, qr_data

## How It Works

### 1. Student Marks Attendance
When a student scans a QR code and completes face verification:

1. **Student Record Created**: `AttendanceRecord` is created with student's attendance
2. **Faculty Record Created/Updated**: `FacultyAttendanceRecord` is created or updated for the teacher/subject/group/date
3. **Faculty Detail Created**: `FacultyAttendanceDetail` is created for the specific student
4. **Counts Updated**: Faculty record counts are recalculated automatically

### 2. Data Flow
```
QR Scan → Face Verification → Student AttendanceRecord
                                ↓
                        FacultyAttendanceRecord (created/updated)
                                ↓
                        FacultyAttendanceDetail (created/updated)
                                ↓
                        Counts & Percentages (recalculated)
```

## Key Features

### Automatic Count Management
- **Total Students**: Automatically calculated from group
- **Present Students**: Count of students marked present
- **Absent Students**: Total - Present
- **Attendance Percentage**: (Present / Total) * 100

### Bidirectional Relationships
- Teachers can see all their attendance records
- Students can see their attendance history
- Faculty records link to individual student details
- Real-time updates when attendance is marked

### Data Consistency
- Both sides maintain the same QR data
- Face verification status is tracked on both sides
- Timestamps are synchronized
- Unique constraints prevent duplicate records

## Database Schema

### FacultyAttendanceRecord
```sql
CREATE TABLE faculty_facultyattendancerecord (
    id BIGINT PRIMARY KEY,
    teacher_id BIGINT REFERENCES student_teacher(id),
    subject_id BIGINT REFERENCES student_subject(id),
    group_id BIGINT REFERENCES student_group(id),
    attendance_date DATE,
    attendance_time TIME,
    total_students INTEGER DEFAULT 0,
    present_students INTEGER DEFAULT 0,
    absent_students INTEGER DEFAULT 0,
    attendance_percentage FLOAT DEFAULT 0.0,
    qr_data JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(teacher_id, subject_id, group_id, attendance_date)
);
```

### FacultyAttendanceDetail
```sql
CREATE TABLE faculty_facultyattendancedetail (
    id BIGINT PRIMARY KEY,
    faculty_record_id BIGINT REFERENCES faculty_facultyattendancerecord(id),
    student_id BIGINT REFERENCES student_student(id),
    status VARCHAR(20) DEFAULT 'present',
    marked_time TIMESTAMP,
    face_verified BOOLEAN DEFAULT FALSE,
    qr_data JSON,
    UNIQUE(faculty_record_id, student_id)
);
```

## Usage Examples

### For Teachers
```python
# Get today's attendance for a teacher
teacher = Teacher.objects.get(roll_no="T002")
today_records = FacultyAttendanceRecord.objects.filter(
    teacher=teacher,
    attendance_date=date.today()
)

# Get detailed attendance for a specific record
record = today_records.first()
details = FacultyAttendanceDetail.objects.filter(faculty_record=record)
present_students = details.filter(status='present')
absent_students = details.filter(status='absent')
```

### For Students
```python
# Student's attendance is still tracked in the original model
student = Student.objects.get(roll_number="765")
attendance_records = AttendanceRecord.objects.filter(student=student)
```

## Benefits

1. **Complete Visibility**: Teachers can see comprehensive attendance data
2. **Real-time Updates**: Counts update automatically as students mark attendance
3. **Data Integrity**: Both sides maintain consistent information
4. **Analytics Ready**: Faculty records provide aggregated data for analytics
5. **Backward Compatible**: Existing student-side functionality remains unchanged

## Migration

The system includes:
- New models in `faculty.models`
- Updated `mark_attendance()` function in `student.views`
- New faculty views for attendance management
- Database migration for new tables

## Testing

Run the test script to verify the system:
```bash
python test_bidirectional_attendance.py
```

This will test:
- Model creation and relationships
- Bidirectional data flow
- Count calculations
- Data consistency

## Future Enhancements

1. **Real-time Notifications**: Push notifications to teachers when attendance is marked
2. **Bulk Operations**: Mark multiple students present/absent at once
3. **Advanced Analytics**: More detailed reporting and trends
4. **Mobile App Integration**: Faculty mobile app for attendance management
5. **Export Features**: Export attendance data to Excel/CSV
