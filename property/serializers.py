from rest_framework import serializers
from .models import Property, PropertyImage

class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ['image_url']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None

class PropertySerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    owner_name = serializers.SerializerMethodField()
    owner_image = serializers.SerializerMethodField()
    is_my_property = serializers.SerializerMethodField()
    owner_uid = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = '__all__'

    def get_owner_name(self, obj):
        return f"{obj.owner.user.first_name} {obj.owner.user.last_name}"

    def get_owner_image(self, obj):
        if obj.owner.profile_image:
            return obj.owner.profile_image.url
        return None
    
    def get_is_my_property(self, obj):

        request = self.context.get('request')

        if request and request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                return obj.owner == request.user.profile

        return False
    
    def get_owner_uid(self, obj):
        return obj.owner.uid