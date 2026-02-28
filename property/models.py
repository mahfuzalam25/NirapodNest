from django.db import models
from accounts.models import Profile
from cloudinary.models import CloudinaryField
import uuid
from django.db.models import Q

class Property(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='properties')
    purpose = models.CharField(max_length=10, choices=[('Sale', 'Sale'), ('Rent', 'Rent')])
    property_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    
    city = models.CharField(max_length=50)
    area = models.CharField(max_length=100)
    
    size_sqft = models.IntegerField()
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    walkability_score = models.IntegerField(default=50)
    population_density_band = models.CharField(max_length=20, default='Medium')
    nearest_station = models.CharField(max_length=100, default='Bus Stop')
    dist_to_station_km = models.FloatField(default=0.0)
    nearest_hospital = models.CharField(max_length=100, default='General Hospital')
    dist_to_hospital_km = models.FloatField(default=0.0)
    
    amenities = models.JSONField(default=list) 
    description = models.TextField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.owner.user.email}"

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')

    def __str__(self):
        return f"Image for {self.property.title}"
    
from django.db.models import Q

class ChatConversation(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='conversations')
    buyer = models.ForeignKey(Profile, related_name='buyer_conversations', on_delete=models.CASCADE)
    owner = models.ForeignKey(Profile, related_name='owner_conversations', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True) 
    last_email_sent_to_buyer = models.DateTimeField(null=True, blank=True)
    last_email_sent_to_owner = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Chat: {self.buyer.user.first_name} & {self.owner.user.first_name} regarding {self.property.title}"

class ChatMessage(models.Model):
    conversation = models.ForeignKey(ChatConversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.user.first_name}: {self.text[:20]}"