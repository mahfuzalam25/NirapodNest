from django.db import models
from accounts.models import Profile
import uuid

class AIRadarAlert(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='radars')
    
    purpose = models.CharField(max_length=50) 
    property_type = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    area = models.CharField(max_length=100)
    
    max_budget = models.IntegerField()
    min_beds = models.CharField(max_length=20) 
    

    notify_push = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=True)
    frequency = models.CharField(max_length=100) 
    preferred_time = models.TimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Radar for {self.user.user.email} - {self.area}"

class RadarNotification(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='radar_notifications')
    message = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default='fa-wand-magic-sparkles')
    link = models.CharField(max_length=255, default='#')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.user.first_name}: {self.message}"
    

class HeroBanner(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title if self.title else "Hero Banner"

class AdBanner(models.Model):
    POSITION_CHOICES = [
        ('home_full', 'Home Page Full Width'),
        ('home_sidebar', 'Home Page Sidebar'),
    ]
    title = models.CharField(max_length=100, help_text="Internal name for the ad")
    image = models.ImageField(upload_to='ads/')
    link = models.URLField(blank=True, null=True)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.position})"
    

class ContactMessage(models.Model):
    DEPARTMENT_CHOICES = [
        ('general', 'General Inquiry'),
        ('technical', 'Technical Support'),
        ('billing', 'Billing & Payments'),
        ('report', 'Report a Listing/User'),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    message = models.TextField()
    

    admin_reply = models.TextField(blank=True, null=True, help_text="Type your reply here. Saving will automatically email the user!")
    is_replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        status = "✅ Replied" if self.is_replied else "⏳ Pending"
        return f"{status} | {self.subject} - {self.name}"