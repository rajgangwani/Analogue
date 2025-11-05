from django import forms
from django.contrib.auth.models import User
from .models import Profile
import re

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # ✅ Only letters and numbers allowed
        if not re.match(r'^[A-Za-z0-9]+$', username):
            raise forms.ValidationError("Username can only contain letters and numbers.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match!")
        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['user_type', 'organization']
