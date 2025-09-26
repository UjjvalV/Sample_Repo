from django import forms
from django.core.files.base import ContentFile
import base64
import uuid
import json
from .models import User, SiteSetting, Group, Student, Teacher
from .face_utils_simple import encode_face_from_base64

class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    faculty_code = forms.CharField(required=False)
    face_image_data = forms.CharField(required=False, widget=forms.HiddenInput)
    face_encoding = forms.CharField(required=False, widget=forms.HiddenInput)
    # Role-specific fields
    faculty_roll_no = forms.CharField(required=False, label="Faculty Roll No")
    student_roll_no = forms.CharField(required=False, label="Student Roll No")
    student_group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, label="Class/Group")

    class Meta:
        model = User
        fields = ["username", "email", "role", "password"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        role = cleaned_data.get("role")
        faculty_code = cleaned_data.get("faculty_code")
        face_image_data = cleaned_data.get("face_image_data")
        faculty_roll_no = cleaned_data.get("faculty_roll_no")
        student_roll_no = cleaned_data.get("student_roll_no")
        student_group = cleaned_data.get("student_group")
        face_encoding = cleaned_data.get("face_encoding")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        if role == "faculty":
            expected = (SiteSetting.get("faculty_access_code") or "").strip()
            provided = (faculty_code or "").strip()
            if not expected:
                raise forms.ValidationError("Faculty access code is not configured. Contact admin.")
            # Accept case-insensitive match and ignore surrounding spaces
            if provided.lower() != expected.lower():
                raise forms.ValidationError("Invalid faculty access code.")
            if not faculty_roll_no:
                raise forms.ValidationError("Faculty roll number is required for faculty signup.")

        if role == "student":
            if not student_group:
                raise forms.ValidationError("Class/Group is required for student signup.")
            if not student_roll_no:
                raise forms.ValidationError("Student roll number is required for student signup.")

        # Require face encoding for signup
        if not face_encoding:
            raise forms.ValidationError("Face encoding is required. Please capture your face to continue.")

        return cleaned_data
    def save(self, commit=True):
        user = super().save(commit=False)
        # Hash the password
        user.set_password(self.cleaned_data["password"])

        # Process face image and store face encoding
        face_data_uri = self.cleaned_data.get("face_image_data")
        face_encoding_str = self.cleaned_data.get("face_encoding")
        
        if face_data_uri and face_data_uri.startswith("data:image"):
            header, data = face_data_uri.split(",", 1)
            image_bytes = base64.b64decode(data)
            filename = f"{uuid.uuid4()}.png"
            # Save to ImageField without immediate database write
            user.face_image.save(filename, ContentFile(image_bytes), save=False)
        
        # Store face encoding directly from frontend
        if face_encoding_str:
            try:
                # Validate that it's a proper JSON array
                face_encoding_data = json.loads(face_encoding_str)
                if isinstance(face_encoding_data, list) and len(face_encoding_data) > 0:
                    user.face_encoding = face_encoding_str
                else:
                    raise forms.ValidationError("Invalid face encoding format.")
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid face encoding data.")
        else:
            # Fallback: generate face encoding from image if no encoding provided
            if face_data_uri and face_data_uri.startswith("data:image"):
                face_encoding = encode_face_from_base64(face_data_uri)
                if face_encoding:
                    user.face_encoding = json.dumps(face_encoding)
                else:
                    raise forms.ValidationError("No face detected in the captured image.")
            else:
                raise forms.ValidationError("Face encoding is required.")
        if commit:
            user.save()

            # Create role-specific profiles/records
            role = self.cleaned_data.get("role")
            if role == "faculty":
                Teacher.objects.get_or_create(
                    user=user,
                    defaults={
                        "roll_no": self.cleaned_data.get("faculty_roll_no"),
                        "name": user.username,
                        "email": user.email or f"{user.username}@example.com",
                        "department": "",
                    },
                )
            elif role == "student":
                group = self.cleaned_data.get("student_group")
                student, created = Student.objects.get_or_create(
                    roll_number=self.cleaned_data.get("student_roll_no"),
                    defaults={
                        "name": user.username,
                        "email": user.email,
                        "group": group,
                        "user": user,
                    },
                )
                if not created:
                    student.user = user
                    student.save()
        return user
