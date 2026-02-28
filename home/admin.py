from django.contrib import admin
from .models import AIRadarAlert, RadarNotification, HeroBanner, AdBanner, ContactMessage
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

admin.site.register(AIRadarAlert)
admin.site.register(RadarNotification)
admin.site.register(HeroBanner)
admin.site.register(AdBanner)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'department', 'is_replied', 'created_at')
    list_filter = ('is_replied', 'department')
    search_fields = ('name', 'email', 'subject')

    readonly_fields = ('name', 'email', 'subject', 'department', 'message', 'created_at', 'replied_at')

    fieldsets = (
        ('User Message Details', {
            'fields': ('name', 'email', 'department', 'subject', 'message', 'created_at')
        }),
        ('NirapodNest Admin Response', {
            'fields': ('admin_reply', 'is_replied', 'replied_at'),
            'description': "Type your reply in the box below. When you click Save, an email will be sent automatically to the user."
        }),
    )

    def save_model(self, request, obj, form, change):

        if change and obj.admin_reply and not obj.is_replied:
            try:

                send_mail(
                    subject=f"Re: {obj.subject} (NirapodNest Support)",
                    message=f"Hello {obj.name},\n\n{obj.admin_reply}\n\nBest regards,\nNirapodNest Team",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.email],
                )
                obj.is_replied = True
                obj.replied_at = timezone.now()
            except Exception as e:
                pass 
        
        super().save_model(request, obj, form, change)