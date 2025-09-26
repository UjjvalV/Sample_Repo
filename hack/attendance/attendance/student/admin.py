from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
import pandas as pd
from .models import User, SiteSetting, Student, Group, Teacher, Subject


# --- USER MODEL ADMIN ---
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_superuser")
    list_filter = ("role", "is_staff", "is_superuser")


# --- SITE SETTINGS ADMIN ---
@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value")

class StudentInline(admin.TabularInline):   # or StackedInline
    model = Student
    extra = 1 

# --- GROUP ADMIN ---
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "stream")
    search_fields = ("name", "stream")
    inlines = [StudentInline]   # lets admin add students while editing a group 


# --- TEACHER ADMIN ---
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject_id")
    search_fields = ("name", "email", "subject_id")
    filter_horizontal = ('groups',)  # nice multi-select widget





# --- STUDENT ADMIN WITH CUSTOM UPLOAD ---
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    change_list_template = "admin/students_changelist.html"  # ✅ Custom template
    list_display = ("name", "roll_number", "email", "phone", "group")
    search_fields = ("name", "roll_number", "email")
    list_filter = ("group",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("upload-students/", self.admin_site.admin_view(self.upload_students), name="upload_students"),
        ]
        return custom_urls + urls

    def upload_students(self, request):
        if request.method == "POST" and request.FILES.get("file"):
            file = request.FILES["file"]
            df = pd.read_excel(file) if file.name.endswith(".xlsx") else pd.read_csv(file)

            # Normalize column names (lowercase, no spaces)
            df.columns = df.columns.str.strip().str.lower()

            for _, row in df.iterrows():
                # Try to read group and stream safely
                group_name = row.get("group") or row.get("group name")
                stream = row.get("stream") or row.get("stream name")
                roll_no = row.get("roll_no") or row.get("roll number")
                name = row.get("name")
                email = row.get("email", "")
                phone = row.get("phone", "")

                if not group_name or not roll_no or not name:
                    continue  # skip incomplete rows

                group, _ = Group.objects.get_or_create(name=group_name, stream=stream or "")
                Student.objects.get_or_create(
                    roll_number=roll_no,
                    defaults={
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "group": group,
                    }
                )

            self.message_user(request, f"✅ {len(df)} students uploaded successfully!")
            return redirect("..")

        # Only render the upload page if it was not a POST request
        return render(request, "admin/upload_students.html")
@admin.register(Subject)

class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")
    filter_horizontal = ("groups",)  # assign subjects to multiple groups
