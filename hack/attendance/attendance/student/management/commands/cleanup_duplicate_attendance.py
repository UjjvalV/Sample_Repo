"""
Management command to clean up duplicate attendance records.
This command removes duplicate attendance records for the same student on the same day.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from student.models import AttendanceRecord
from datetime import date

class Command(BaseCommand):
    help = 'Clean up duplicate attendance records for the same student on the same day'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Clean up duplicates for a specific date (YYYY-MM-DD format)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_date = options.get('date')
        
        if target_date:
            try:
                target_date = date.fromisoformat(target_date)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD format.')
                )
                return
        
        # Find duplicate attendance records
        if target_date:
            duplicates = AttendanceRecord.objects.filter(
                attendance_date=target_date
            ).values('student', 'attendance_date').annotate(
                count=Count('id')
            ).filter(count__gt=1)
        else:
            duplicates = AttendanceRecord.objects.values(
                'student', 'attendance_date'
            ).annotate(
                count=Count('id')
            ).filter(count__gt=1)
        
        if not duplicates.exists():
            self.stdout.write(
                self.style.SUCCESS('No duplicate attendance records found.')
            )
            return
        
        self.stdout.write(f'Found {duplicates.count()} sets of duplicate records:')
        
        total_deleted = 0
        for duplicate in duplicates:
            student_id = duplicate['student']
            attendance_date = duplicate['attendance_date']
            count = duplicate['count']
            
            # Get all records for this student on this date
            records = AttendanceRecord.objects.filter(
                student_id=student_id,
                attendance_date=attendance_date
            ).order_by('created_at')
            
            # Keep the first record, delete the rest
            records_to_delete = records[1:]
            
            self.stdout.write(
                f'Student ID {student_id} on {attendance_date}: '
                f'{count} records found, will delete {len(records_to_delete)} duplicates'
            )
            
            if not dry_run:
                for record in records_to_delete:
                    self.stdout.write(
                        f'  Deleting record ID {record.id} (created at {record.created_at})'
                    )
                    record.delete()
                    total_deleted += 1
            else:
                for record in records_to_delete:
                    self.stdout.write(
                        f'  Would delete record ID {record.id} (created at {record.created_at})'
                    )
                    total_deleted += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {total_deleted} duplicate records.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {total_deleted} duplicate records.')
            )
