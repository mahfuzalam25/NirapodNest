from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from .serializers import SignupSerializer
from .models import Profile, Address, FamilyMember, OwnerDetail, BannedEmail
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
import random
import re
import hashlib

from django.core.cache import cache
from django.contrib.auth.hashers import make_password


class RegisterUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = str(random.randint(1000, 9999))

            try:
                with transaction.atomic(): 
                    user = User.objects.filter(email=email).first()
                    
                    if user:
                        user.first_name = serializer.validated_data['first_name']
                        user.last_name = serializer.validated_data['last_name']
                        user.set_password(serializer.validated_data['password'])
                        user.save()
                        profile = user.profile
                    else:
                        user = User.objects.create_user(
                            username=email, 
                            email=email,
                            password=serializer.validated_data['password'],
                            first_name=serializer.validated_data['first_name'],
                            last_name=serializer.validated_data['last_name']
                        )
                        profile = user.profile
                    
                    profile.role = serializer.validated_data['role']
                    profile.phone_number = serializer.validated_data['phone_number']
                    profile.otp_code = otp
                    profile.save()

                    email_subject = "Verify your NirapodNest AI Account"
                    email_body = f"Hello {user.first_name},\n\nYour OTP is: {otp}\n\nWelcome to NirapodNest!"
                    
                    send_mail(
                        subject=email_subject,
                        message=email_body,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=False, 
                    )

                return Response({"message": "OTP sent to email.", "email": user.email}, status=status.HTTP_201_CREATED)

            except Exception as e:

                return Response({"error": f"Failed to send email. Please check your network/SMTP. Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        try:
            user = User.objects.get(email=email)
            if user.profile.otp_code == otp:
                user.profile.is_verified = True
                user.profile.otp_code = None 
                user.profile.save()

                refresh = RefreshToken.for_user(user)
                
                return Response({
                    "message": "OTP Verified!",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "role": user.profile.role 
                }, status=status.HTTP_200_OK)
                
            return Response({"error": "Invalid OTP Code."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)



class CompleteProfileView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request):
        user = request.user
        profile = user.profile
        data = request.data

        country = data.get('present_address', {}).get('country', 'Bangladesh')
        raw_identity = data.get('identity_number', '')
        
        if country.lower() == 'bangladesh':
            if not re.match(r'^([0-9]{10}|[0-9]{13}|[0-9]{17})$', raw_identity):
                return Response({"error": "Invalid Bangladeshi NID format."}, status=status.HTTP_400_BAD_REQUEST)

        identity_hash = hashlib.sha256(raw_identity.encode()).hexdigest()


        if Profile.objects.filter(identity_hash=identity_hash).exclude(user=user).exists():
            return Response({
                "error": "CRITICAL: This NID/Passport is already registered to an existing account. One person cannot have multiple accounts."
            }, status=status.HTTP_400_BAD_REQUEST)



        if profile.role == 'owner':
            house_no = data.get('present_address', {}).get('house_no')
            area = data.get('present_address', {}).get('area_name')
            
            address_match = Address.objects.filter(
                profile__role='owner', house_no=house_no, area_name=area
            ).exclude(profile=user.profile).first()
            
            if address_match:
                collision_profile = address_match.profile

                is_family = FamilyMember.objects.filter(
                    profile=collision_profile, 
                    first_name__iexact=user.first_name, 
                    last_name__iexact=user.last_name
                ).exists()
                
                if not is_family:

                    BannedEmail.objects.create(email=user.email, reason="Hijacking attempt on existing owner property.")
                    user.is_active = False
                    user.save()
                    return Response({"error": "Security Alert: Property address already claimed. Account suspended for review."}, status=status.HTTP_403_FORBIDDEN)


        try:
            with transaction.atomic():
                profile.set_identity(raw_identity)
                profile.professional_status = data.get('professional_status')
                profile.save()

                present_data = data.get('present_address', {})
                Address.objects.create(profile=profile, address_type='Present', **present_data)
                
                permanent_data = data.get('permanent_address', {})
                Address.objects.create(profile=profile, address_type='Permanent', **permanent_data)

                for member in data.get('family_members', []):
                    FamilyMember.objects.create(profile=profile, **member)

                if profile.role == 'owner':
                    owner_data = data.get('owner_details', {})
                    OwnerDetail.objects.create(
                        profile=profile,
                        building_name=owner_data.get('building_name'),
                        total_units=owner_data.get('total_units', 1),
                        avg_size_sqft=owner_data.get('avg_size_sqft'),
                        target_audience=owner_data.get('target_audience', [])
                    )
            
            return Response({"message": "Profile complete!"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Database error while saving profile: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uid): 
        try:
            profile = Profile.objects.get(uid=uid)
            target_user = profile.user 

            public_data = {
                "uid": str(profile.uid), 
                "name": f"{target_user.first_name} {target_user.last_name}",
                "role": profile.role,
                "is_verified": profile.is_verified,
            }
            
            if profile.role == 'owner':
                if hasattr(profile, 'owner_details'):
                    public_data["building_name"] = profile.owner_details.building_name
                    public_data["total_units"] = profile.owner_details.total_units
                else:
                    public_data["building_name"] = "Pending Setup"

            return Response(public_data, status=status.HTTP_200_OK)
            
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found or link is invalid."}, status=status.HTTP_404_NOT_FOUND)
        


class LoginUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(username=email, password=password)

        if user is not None:
            if not user.is_active:
                return Response({"error": "This account has been banned or deactivated."}, status=status.HTTP_403_FORBIDDEN)

            profile = user.profile
            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": profile.role,
                "is_verified": profile.is_verified,
                "name": f"{user.first_name} {user.last_name}"
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)
        


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile

        data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_number": profile.phone_number,
            "role": profile.role,
            "is_verified": profile.is_verified,
            "profile_image": profile.profile_image.url if profile.profile_image else None,
            "professional_status": profile.professional_status,
            "office_address": profile.office_address,
            "nid_status": "Verified" if profile.identity_hash else "Pending",
            "last_login": user.last_login.strftime("%B %d, %Y, %I:%M %p") if user.last_login else "First Login",
        }

        present_addr = profile.addresses.filter(address_type='Present').first()
        perm_addr = profile.addresses.filter(address_type='Permanent').first()
        
        if present_addr:
            data['present_address'] = f"House {present_addr.house_no}, {present_addr.area_name}<br>{present_addr.police_station}, {present_addr.district}"
            data['raw_present'] = {"area": present_addr.area_name, "district": present_addr.district}
        if perm_addr:
            data['permanent_address'] = f"House {perm_addr.house_no}, {perm_addr.area_name}<br>{perm_addr.police_station}, {perm_addr.district}"
            data['raw_permanent'] = {"area": perm_addr.area_name, "district": perm_addr.district}

        family_data = []
        for member in profile.family_members.all():
            family_data.append({
                "id": member.id,
                "name": f"{member.first_name} {member.last_name}",
                "relation": member.relation
            })
        data['family_members'] = family_data

        if profile.role == 'owner':
            if hasattr(profile, 'owner_details'):
                data['owner_details'] = {
                    "building_name": profile.owner_details.building_name,
                    "total_units": profile.owner_details.total_units,
                    "avg_size_sqft": profile.owner_details.avg_size_sqft,
                    "target_audience": ", ".join(profile.owner_details.target_audience)
                }
            

            properties_data = []
            for prop in profile.properties.all().order_by('-created_at'):
                first_image = prop.images.first()
                properties_data.append({
                    "uid": prop.uid,
                    "title": prop.title,
                    "location": f"{prop.area}, {prop.city}",
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "size_sqft": prop.size_sqft,
                    "price": prop.price,
                    "purpose": prop.purpose,
                    "image_url": first_image.image.url if first_image else 'https://placehold.co/400x250/334155/ffffff?text=No+Image'
                })
            data['my_properties'] = properties_data

        return Response(data, status=status.HTTP_200_OK)


class UploadAvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = request.user.profile
        profile.profile_image = request.FILES['image']
        profile.save()
        
        return Response({"image_url": profile.profile_image.url}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not user.check_password(current_password):
            return Response({"error": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user) 
        
        return Response({"message": "Password updated successfully!"}, status=status.HTTP_200_OK)
    


class EditProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        profile = user.profile
        data = request.data

        try:
            profile.professional_status = data.get('professional_status', profile.professional_status)
            profile.office_address = data.get('office_address', profile.office_address)
            profile.save()

            def update_address(addr_type, addr_data):
                if not addr_data: return
                
                address, created = Address.objects.get_or_create(profile=profile, address_type=addr_type)
                address.country = addr_data.get('country', address.country)
                address.district = addr_data.get('district', address.district)
                address.police_station = addr_data.get('police_station', address.police_station)
                address.area_name = addr_data.get('area_name', address.area_name)
                address.ward_no = addr_data.get('ward_no', address.ward_no)
                address.house_no = addr_data.get('house_no', address.house_no)
                address.floor_apt = addr_data.get('floor_apt', address.floor_apt)
                address.save()

            update_address('Present', data.get('present_address'))
            update_address('Permanent', data.get('permanent_address'))

            return Response({"message": "Profile updated successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        


class PublicProfileView(APIView):
    permission_classes = [AllowAny] 

    def get(self, request, uid):
        try:
            profile = Profile.objects.get(uid=uid)
            user = profile.user
            
            data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email, 
                "phone_number": profile.phone_number,
                "role": profile.role,
                "profile_image": profile.profile_image.url if profile.profile_image else None,
                "professional_status": profile.professional_status,
                "office_address": profile.office_address,
            }

            properties_data = []
            for prop in profile.properties.all().order_by('-created_at'):
                first_image = prop.images.first()
                properties_data.append({
                    "uid": prop.uid,
                    "title": prop.title,
                    "location": f"{prop.area}, {prop.city}",
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "size_sqft": prop.size_sqft,
                    "price": prop.price,
                    "purpose": prop.purpose,
                    "image_url": first_image.image.url if first_image else 'https://placehold.co/400x250/334155/ffffff?text=No+Image'
                })
            data['my_properties'] = properties_data

            return Response(data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        



class RequestPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "No account found with this email address."}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(1000, 9999))
        

        cache.set(f"reset_otp_{email}", otp, 300)

        try:
            send_mail(
                subject="NirapodNest AI - Password Reset Code",
                message=f"Hello {user.first_name},\n\nYour OTP for resetting your password is: {otp}\n\nThis code expires in 5 minutes.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({"message": "OTP sent successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Failed to send email. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp_provided = request.data.get('otp')
        stored_otp = cache.get(f"reset_otp_{email}")

        if stored_otp and stored_otp == otp_provided:

            cache.set(f"can_reset_{email}", True, 600)
            return Response({"message": "OTP Verified! Proceed to reset password."}, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid or expired OTP code."}, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('password')

        if not cache.get(f"can_reset_{email}"):
            return Response({"error": "Unauthorized. Please verify your OTP first."}, status=status.HTTP_403_FORBIDDEN)

        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()

            cache.delete(f"reset_otp_{email}")
            cache.delete(f"can_reset_{email}")

            return Response({"message": "Password reset successful!"}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "An error occurred. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)