from django.db import models
from django.contrib.auth.models import User
import hashlib
import uuid
from cloudinary.models import CloudinaryField

class BannedEmail(models.Model):
    email = models.EmailField(unique=True)
    reason = models.CharField(max_length=255)
    banned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BANNED: {self.email}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    profile_image = CloudinaryField('image', null=True, blank=True)
    role = models.CharField(max_length=20, choices=[('user', 'Regular User'), ('owner', 'Property Owner')], default='user')
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False) 
    otp_code = models.CharField(max_length=4, null=True, blank=True) 
    

    identity_number = models.CharField(max_length=255, null=True, blank=True) 
    identity_hash = models.CharField(max_length=64, null=True, blank=True) 
    
    professional_status = models.CharField(max_length=50, null=True, blank=True)
    office_address = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} ({self.role.capitalize()})"

    def set_identity(self, raw_id):
        self.identity_hash = hashlib.sha256(raw_id.encode()).hexdigest()
        self.identity_number = f"ENCRYPTED_{raw_id[::-1]}" 
        self.save()

class Address(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Permanent', 'Permanent')])
    country = models.CharField(max_length=50, default="Bangladesh")
    district = models.CharField(max_length=50)
    police_station = models.CharField(max_length=50)
    area_name = models.CharField(max_length=100)
    ward_no = models.CharField(max_length=20)
    house_no = models.CharField(max_length=50)
    floor_apt = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.address_type} Address - {self.profile.user.email}"

class FamilyMember(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='family_members')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relation = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.first_name} ({self.relation}) - {self.profile.user.email}"

class OwnerDetail(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='owner_details')
    building_name = models.CharField(max_length=100, null=True, blank=True)
    total_units = models.IntegerField(default=1)
    avg_size_sqft = models.IntegerField(null=True, blank=True)
    target_audience = models.JSONField(default=list)

    def __str__(self):
        return f"Owner Details: {self.profile.user.email}"