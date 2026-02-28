from django.contrib import admin
from .models import Profile, Address, FamilyMember, OwnerDetail, BannedEmail

# Register your models here.
admin.site.register(Profile)
admin.site.register(Address)
admin.site.register(FamilyMember)
admin.site.register(OwnerDetail)
admin.site.register(BannedEmail)