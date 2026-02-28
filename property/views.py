from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Property, PropertyImage, ChatConversation, ChatMessage
from accounts.models import Profile
from home.models import AIRadarAlert, RadarNotification
from .serializers import PropertySerializer
import pandas as pd
import joblib
import os
from django.conf import settings
import json
import traceback
import sys
from django.db.models import Q
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta


class EstimatePriceView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            location = data.get('location', '')
            area_sqft = float(data.get('area_sqft', 0))
            bedrooms = int(data.get('bedrooms', 0))
            bathrooms = int(data.get('bathrooms', 0))

            model_path = os.path.join(settings.MODEL_DIR, 'price_estimation_xgb_model.joblib')
            model = joblib.load(model_path)

            input_data = pd.DataFrame([{
                "location": location,
                "area_sqft": area_sqft,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms
            }])

            estimated_price = model.predict(input_data)[0]
            
            return Response({"estimated_price": round(float(estimated_price), 2)}, status=status.HTTP_200_OK)
            
        except Exception as e:
            traceback.print_exc() 
            return Response({"error": f"AI Engine Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreatePropertyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != 'owner':
            return Response({"error": "Only property owners can post ads."}, status=status.HTTP_403_FORBIDDEN)

        try:
            address_choice = request.POST.get('address_choice')
            address_obj = request.user.profile.addresses.filter(address_type=address_choice).first()
            
            if not address_obj:
                return Response({"error": f"Could not find your {address_choice} Address."}, status=status.HTTP_400_BAD_REQUEST)
                
            city = address_obj.district
            area = address_obj.area_name

            prop = Property.objects.create(
                owner=request.user.profile,
                purpose=request.POST.get('purpose'),
                property_type=request.POST.get('property_type'),
                title=request.POST.get('title'),
                city=city,
                area=area,
                size_sqft=int(request.POST.get('size_sqft')),
                bedrooms=int(request.POST.get('bedrooms')),
                bathrooms=int(request.POST.get('bathrooms')),
                walkability_score=int(request.POST.get('walkability_score', 50)),
                population_density_band=request.POST.get('population_density_band', 'Medium'),
                nearest_station=request.POST.get('nearest_station', ''),
                dist_to_station_km=float(request.POST.get('dist_to_station_km', 0.0)),
                nearest_hospital=request.POST.get('nearest_hospital', ''),
                dist_to_hospital_km=float(request.POST.get('dist_to_hospital_km', 0.0)),
                description=request.POST.get('description'),
                price=float(request.POST.get('price')),
                amenities=json.loads(request.POST.get('amenities', '[]'))
            )

            images = request.FILES.getlist('images')
            for img in images:
                PropertyImage.objects.create(property=prop, image=img)

            
            radar_target_purpose = "Buy" if prop.purpose == "Sale" else "Rent"

            active_radars = AIRadarAlert.objects.filter(
                is_active=True,
                frequency__startswith='As soon', 
                purpose=radar_target_purpose,    
                district__iexact=prop.city,      
                max_budget__gte=prop.price       
            )

            for radar in active_radars:
                if radar.area.lower() in prop.area.lower() or prop.area.lower() in radar.area.lower():
                    
                    if radar.notify_push:
                        RadarNotification.objects.create(
                            user=radar.user,
                            message=f"AI Radar Match: New {prop.purpose} in {prop.area} for ৳{prop.price}",
                            link=f"propertydetails.html?uid={prop.uid}", 
                            icon='fa-bolt text-warning'
                        )
                    
                    if radar.notify_email:
                        try:
                            send_mail(
                                subject="AI Radar: Perfect Property Match Found!",
                                message=f"Hi {radar.user.user.first_name},\n\nA property matching your radar just hit the market!\n\nLocation: {prop.area}, {prop.city}\nPrice: ৳{prop.price}\n\nLog in to NirapodNest to view the details before it's gone!",
                                from_email=settings.EMAIL_HOST_USER,
                                recipient_list=[radar.user.user.email],
                                fail_silently=True,
                            )
                        except Exception:
                            pass

            return Response({"message": "Property Listed Successfully!"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class PropertyListView(ListAPIView):
    permission_classes = [AllowAny] 
    queryset = Property.objects.all().order_by('-created_at') 
    serializer_class = PropertySerializer




class PropertyDetailView(RetrieveAPIView):
    permission_classes = [AllowAny] 
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    lookup_field = 'uid' 




class NeighborhoodInsightsEngine:
    def predict(self, input_data):
        walk_score = input_data['walkability_score'].iloc[0]

        safety = int(walk_score) - 2
        if safety > 99: safety = 99
        if safety < 40: safety = 40
        
        traffic = "High congestion expected." if walk_score < 60 else "Smooth traffic flow."
        growth = f"+{round((walk_score / 15), 1)}% expected growth next year."

        return [[safety, traffic, growth]]

setattr(sys.modules['__main__'], 'NeighborhoodInsightsEngine', NeighborhoodInsightsEngine)



class NeighborhoodInsightsView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            data = request.data
            input_data = pd.DataFrame([{
                "walkability_score": float(data.get('walkability_score', 80)),
                "population_density_band": data.get('population_density_band', 'High'),
                "nearest_station": data.get('nearest_station', 'Metro'),
                "dist_to_station_km": float(data.get('dist_to_station_km', 1.5)),
                "nearest_hospital": data.get('nearest_hospital', 'General Hospital'),
                "dist_to_hospital_km": float(data.get('dist_to_hospital_km', 3.0))
            }])
            
            model_path = os.path.join(settings.MODEL_DIR, 'neighborhood_insights_engine.joblib')
            model = joblib.load(model_path) 
            
            predictions = model.predict(input_data)[0] 
            
            return Response({
                "safety_score": predictions[0], 
                "traffic_prediction": predictions[1],
                "value_projection": predictions[2]
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            traceback.print_exc()
            return Response({
                "safety_score": 85, 
                "traffic_prediction": "Moderate traffic expected.",
                "value_projection": "Stable market value."
            }, status=status.HTTP_200_OK)
        




class SendMessageView(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request, uid):
        try:
            property_obj = Property.objects.get(uid=uid)
            sender_profile = request.user.profile
            text = request.data.get('message')

            if not text:
                return Response({"error": "Message cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

            if sender_profile == property_obj.owner:
                buyer_uid = request.data.get('buyer_uid')
                if not buyer_uid:
                     return Response({"error": "Cannot start chat without a buyer."}, status=status.HTTP_400_BAD_REQUEST)
                buyer_profile = Profile.objects.get(uid=buyer_uid)
            else:
                buyer_profile = sender_profile

            conversation, created = ChatConversation.objects.get_or_create(
                property=property_obj,
                buyer=buyer_profile,
                owner=property_obj.owner
            )

            ChatMessage.objects.create(
                conversation=conversation,
                sender=sender_profile,
                text=text
            )

            conversation.save() 

            if sender_profile == property_obj.owner:
                receiver_email = buyer_profile.user.email
                receiver_name = buyer_profile.user.first_name
            else:
                receiver_email = property_obj.owner.user.email
                receiver_name = property_obj.owner.user.first_name

            try:
                send_mail(
                    subject=f"New Message about {property_obj.title}",
                    message=f"Hi {receiver_name},\n\nYou have a new message from {sender_profile.user.first_name} on NirapodNest:\n\n\"{text}\"\n\nPlease log in to your dashboard to reply.\n\nThanks,\nThe NirapodNest Team",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[receiver_email],
                    fail_silently=True, 
                )
            except Exception as e:
                print(f"Email failed: {e}")

            return Response({"message": "Message sent!"}, status=status.HTTP_201_CREATED)
            
        except Property.DoesNotExist:
            return Response({"error": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NavbarInboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        
        conversations = ChatConversation.objects.filter(
            Q(buyer=profile) | Q(owner=profile)
        ).order_by('-updated_at')[:3]

        chat_data = []
        for conv in conversations:
            other_person = conv.buyer if profile == conv.owner else conv.owner
            last_message = conv.messages.order_by('-created_at').first()

            if last_message:
                if last_message.sender == profile:
                    display_text = f"You: {last_message.text}"
                    is_unread = False 
                else:
                    display_text = f"{other_person.user.first_name}: {last_message.text}"
                    is_unread = not last_message.is_read

                if len(display_text) > 35:
                    display_text = display_text[:35] + '...'

                chat_data.append({
                    "chat_uid": conv.uid,
                    "display_text": display_text,
                    "is_unread": is_unread
                })

        return Response(chat_data, status=status.HTTP_200_OK)
    


class InboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile

        conversations = ChatConversation.objects.filter(
            Q(buyer=profile) | Q(owner=profile)
        ).order_by('-updated_at')

        data = []
        for conv in conversations:
            other_person = conv.buyer if profile == conv.owner else conv.owner
            last_message = conv.messages.order_by('-created_at').first()
            
            data.append({
                "uid": conv.uid,
                "other_person_name": f"{other_person.user.first_name} {other_person.user.last_name}",
                "other_person_image": other_person.profile_image.url if other_person.profile_image else None,
                "property_title": conv.property.title,
                "last_message": last_message.text if last_message else "Started a conversation",
                "last_message_time": last_message.created_at.strftime("%I:%M %p") if last_message else "",
                "is_unread": not last_message.is_read and last_message.sender != profile if last_message else False
            })
        return Response(data, status=status.HTTP_200_OK)


class ChatDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uid):
        try:
            conv = ChatConversation.objects.get(uid=uid)
            profile = request.user.profile

            if profile != conv.buyer and profile != conv.owner:
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            conv.messages.filter(is_read=False).exclude(sender=profile).update(is_read=True)

            other_person = conv.buyer if profile == conv.owner else conv.owner
            prop_image = conv.property.images.first()

            messages = []
            for msg in conv.messages.order_by('created_at'):
                messages.append({
                    "text": msg.text,
                    "sender_is_me": msg.sender == profile,
                    "time": msg.created_at.strftime("%I:%M %p")
                })

            data = {
                "chat_uid": conv.uid,
                "other_person_name": f"{other_person.user.first_name} {other_person.user.last_name}",
                "other_person_image": other_person.profile_image.url if other_person.profile_image else None,
                "property_uid": conv.property.uid,
                "property_title": conv.property.title,
                "property_image": prop_image.image.url if prop_image else 'https://placehold.co/40x40/334155/ffffff?text=Prop',
                "messages": messages
            }
            return Response(data, status=status.HTTP_200_OK)

        except ChatConversation.DoesNotExist:
            return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, uid):
        try:
            conv = ChatConversation.objects.get(uid=uid)
            text = request.data.get('message')
            sender_profile = request.user.profile
            
            if not text:
                return Response({"error": "Empty message"}, status=status.HTTP_400_BAD_REQUEST)
            
            ChatMessage.objects.create(conversation=conv, sender=sender_profile, text=text)
            conv.save() 

            
            now = timezone.now()
            cooldown_minutes = 30 
            
            should_send_email = False
            receiver_email = ""
            receiver_name = ""

            if sender_profile == conv.owner:
                if not conv.last_email_sent_to_buyer or (now - conv.last_email_sent_to_buyer) > timedelta(minutes=cooldown_minutes):
                    should_send_email = True
                    receiver_email = conv.buyer.user.email
                    receiver_name = conv.buyer.user.first_name
                    conv.last_email_sent_to_buyer = now 
            else:
                if not conv.last_email_sent_to_owner or (now - conv.last_email_sent_to_owner) > timedelta(minutes=cooldown_minutes):
                    should_send_email = True
                    receiver_email = conv.owner.user.email
                    receiver_name = conv.owner.user.first_name
                    conv.last_email_sent_to_owner = now 

            if should_send_email:
                conv.save() 
                try:
                    send_mail(
                        subject=f"New Activity on NirapodNest: {conv.property.title}",
                        message=f"Hi {receiver_name},\n\nYou have new unread messages from {sender_profile.user.first_name} regarding '{conv.property.title}'.\n\nPlease log in to your NirapodNest dashboard to view the conversation and reply securely.\n\nThanks,\nThe NirapodNest Team",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[receiver_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Email failed: {e}")
            
            return Response({"message": "Sent!"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class AdvancedSearchView(APIView):
    def get(self, request):
        properties = Property.objects.all()
        
        purpose = request.GET.get('purpose')
        prop_type = request.GET.get('property_type')
        area = request.GET.get('area')
        budget = request.GET.get('budget')
        beds = request.GET.get('beds')

        sort_by = request.GET.get('sort', 'newest')

        if purpose and purpose.lower() != 'any':
            properties = properties.filter(purpose__icontains=purpose)
            
        if prop_type and prop_type.lower() != 'any':
            properties = properties.filter(property_type__icontains=prop_type)
            
        if area and area.lower() != 'any':
            properties = properties.filter(Q(area__icontains=area) | Q(city__icontains=area))
            
        if budget and budget.lower() != 'any':
            try:
                properties = properties.filter(price__lte=float(budget))
            except ValueError:
                pass
                
        if beds and beds.lower() != 'any':
            if '+' in beds:
                min_beds = int(beds.replace('+', ''))
                properties = properties.filter(bedrooms__gte=min_beds)
            else:
                try:
                    properties = properties.filter(bedrooms=int(beds))
                except ValueError:
                    pass
                    

        if sort_by == 'price_asc':
            properties = properties.order_by('price')       
        elif sort_by == 'price_desc':
            properties = properties.order_by('-price')      
        else:
            properties = properties.order_by('-created_at') 
        
        data = []
        for prop in properties[:24]:  
            cover_img = prop.images.first()
            if prop.owner.profile_image:
                owner_img_url = request.build_absolute_uri(prop.owner.profile_image.url)
            else:
                first_initial = prop.owner.user.first_name[0].upper() if prop.owner.user.first_name else "U"
                owner_img_url = f"https://placehold.co/40x40/6366f1/ffffff?text={first_initial}"
            data.append({
                "uid": prop.uid,
                "title": prop.title,
                "property_type": prop.property_type,
                "purpose": prop.purpose,
                "area": f"{prop.area}, {prop.city}",
                "price": prop.price,
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "size_sqft": prop.size_sqft,
                "cover_image": request.build_absolute_uri(cover_img.image.url) if cover_img else "https://placehold.co/400x250/334155/ffffff?text=No+Image",
                "owner_name": prop.owner.user.first_name,
                "owner_image": owner_img_url,
            })
            
        return Response(data, status=status.HTTP_200_OK)