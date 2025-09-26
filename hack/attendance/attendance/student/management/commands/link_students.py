from django.core.management.base import BaseCommand
from student.models import User, Student

class Command(BaseCommand):
    help = 'Link existing users to student profiles based on username matching roll_number'

    def handle(self, *args, **options):
        linked_count = 0
        not_found_count = 0
        
        # Get all student users who don't have a student profile linked
        student_users = User.objects.filter(role='student', student_profile__isnull=True)
        
        for user in student_users:
            try:
                student = Student.objects.get(roll_number=user.username)
                student.user = user
                student.save()
                linked_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Linked user {user.username} to student {student.name}')
                )
            except Student.DoesNotExist:
                not_found_count += 1
                self.stdout.write(
                    self.style.WARNING(f'No student found with roll_number: {user.username}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSummary: {linked_count} users linked, {not_found_count} not found')
        )
