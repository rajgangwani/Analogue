from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


def trial_expiry_default():
    """Default expiry date = 7 days from registration."""
    return timezone.now() + timedelta(days=7)


class Profile(models.Model):
    USER_TYPE_CHOICES = [
        ('academic', 'Academic'),
        ('industry', 'Industry'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    organization = models.CharField(max_length=120, blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    trial_expiry = models.DateTimeField(default=trial_expiry_default)
    is_premium = models.BooleanField(default=False, help_text="Grant premium access to this user.")

    # ------------------ LOGIC PROPERTIES ------------------
    @property
    def is_trial_active(self):
        """Check if trial is still valid or user is premium."""
        if self.is_premium:
            return True
        return timezone.now() < self.trial_expiry

    @property
    def days_left(self):
        """Return remaining trial days (auto-calculated daily)."""
        if self.is_premium:
            return "∞ (Premium User)"
        remaining = (self.trial_expiry - timezone.now()).days
        return max(0, remaining)

    def save(self, *args, **kwargs):
        """
        Automatically deactivate trial when expired
        (optional safety check).
        """
        if not self.is_premium and timezone.now() > self.trial_expiry:
            # trial expired
            self.is_premium = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.user_type})"


# ------------------ MODULE MODEL ------------------
class Module(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_free = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False, help_text="Check if this module requires premium access.")
    image = models.ImageField(upload_to='modules/', blank=True, null=True, help_text="Upload an image for this module.")
    image_url = models.URLField(blank=True, null=True, help_text="OR enter an external image URL for this module.")

    def get_image(self):
        """Return image path, URL, or fallback placeholder."""
        if self.image:
            return self.image.url
        elif self.image_url:
            return self.image_url
        else:
            return "https://via.placeholder.com/300x200?text=No+Image"

    def __str__(self):
        return self.name
