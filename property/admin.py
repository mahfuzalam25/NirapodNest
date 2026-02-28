from django.contrib import admin
from .models import Property, PropertyImage, ChatMessage, ChatConversation

# Register your models here.

admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(ChatConversation)
admin.site.register(ChatMessage)