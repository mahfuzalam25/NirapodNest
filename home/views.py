from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import AIRadarAlert, RadarNotification
from django.core.mail import send_mail
from django.conf import settings
import os
import joblib
import pandas as pd
import re
from django.core.management import call_command
from django.http import JsonResponse

from .models import HeroBanner, AdBanner, ContactMessage


from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


class AIMarketRadarEngine:
    def __init__(self):
        try:
            model_dir = settings.MODEL_DIR
            self.preprocessor = joblib.load(os.path.join(settings.MODEL_DIR, 'radar_preprocessor.joblib'))
            self.knn_model = joblib.load(os.path.join(settings.MODEL_DIR, 'radar_knn_model.joblib'))
            self.catalog = joblib.load(os.path.join(settings.MODEL_DIR, 'radar_property_catalog.joblib'))
        except Exception as e:
            print(f"Warning: AI Radar Models not loaded. {e}")
            self.knn_model = None

    def find_matches(self, criteria):

        if not self.knn_model:
            return [{"title": f"Test Match in {criteria['location']}", "uid": "12345"}]
        
        return []


class RadarAlertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        radars = AIRadarAlert.objects.filter(user=request.user.profile).order_by('-created_at')
        data = []
        for r in radars:
            data.append({
                "uid": r.uid,
                "purpose": r.purpose,
                "property_type": r.property_type,
                "district": r.district,
                "area": r.area,
                "max_budget": r.max_budget,
                "min_beds": r.min_beds,
                "notify_push": r.notify_push,
                "notify_email": r.notify_email,
                "frequency": r.frequency,
                "is_active": r.is_active
            })
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        profile = request.user.profile
        data = request.data
        pref_time = data.get('preferred_time') if data.get('frequency') == 'Daily Summary' else None

        radar = AIRadarAlert.objects.create(
            user=profile,
            purpose=data.get('purpose'),
            property_type=data.get('property_type'),
            district=data.get('district'),
            area=data.get('area'),
            max_budget=int(data.get('budget')),
            min_beds=data.get('beds'),
            notify_push=data.get('push'),
            notify_email=data.get('email'),
            frequency=data.get('frequency'),
            preferred_time=pref_time
        )


        if radar.frequency.startswith('As soon'):
            engine = AIMarketRadarEngine()
            matches = engine.find_matches({
                "location": radar.area,
                "area_sqft": 1000, 
                "bedrooms": 3 if radar.min_beds == 'Any' else int(radar.min_beds.replace('+','')),
                "bathrooms": 2,
                "price_bdt": radar.max_budget
            })

            if matches:

                if radar.notify_push:
                    RadarNotification.objects.create(
                        user=profile,
                        message=f"AI found {len(matches)} initial matches in {radar.area}!",
                        icon='fa-satellite-dish'
                    )

                if radar.notify_email:
                    send_mail(
                        "AI Radar: Matches Found!",
                        f"Your AI Radar found {len(matches)} matches in {radar.area}. Visit your dashboard to view them.",
                        settings.EMAIL_HOST_USER,
                        [profile.user.email],
                        fail_silently=True,
                    )

        return Response({"message": "Radar Deployed!"}, status=status.HTTP_201_CREATED)

class RadarActionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, uid):
        AIRadarAlert.objects.filter(uid=uid, user=request.user.profile).delete()
        return Response({"message": "Radar Deleted"}, status=status.HTTP_200_OK)

    def patch(self, request, uid):
        radar = AIRadarAlert.objects.filter(uid=uid, user=request.user.profile).first()
        if radar:
            radar.is_active = request.data.get('is_active', radar.is_active)
            radar.save()
            return Response({"message": "Radar Updated"}, status=status.HTTP_200_OK)
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class NavbarNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        notifs = RadarNotification.objects.filter(user=request.user.profile).order_by('-created_at')[:5]
        data = [{"id": n.id, "message": n.message, "icon": n.icon, "link": n.link, "is_read": n.is_read} for n in notifs]
        return Response(data, status=status.HTTP_200_OK)
    


def trigger_radars_view(request):

    expected_secret = os.environ.get('CRON_SECRET_KEY', 'my_local_secret_123')
    provided_secret = request.GET.get('secret')

    if provided_secret != expected_secret:
        return JsonResponse({"error": "Unauthorized. Wrong secret key."}, status=401)

    try:

        call_command('send_radars')
        return JsonResponse({"status": "Success", "message": "AI Radars triggered successfully!"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def keep_alive_view(request):

    return JsonResponse({"status": "Alive", "message": "Server is awake and running!"})




class BannerAdView(APIView):

    def get(self, request):
        hero_banners = HeroBanner.objects.filter(is_active=True).order_by('-created_at')[:3]
        full_ads = AdBanner.objects.filter(position='home_full', is_active=True).order_by('-id')[:1]
        sidebar_ads = AdBanner.objects.filter(position='home_sidebar', is_active=True).order_by('-id')[:1]

        return Response({
            "hero_banners": [{"id": b.id, "image": request.build_absolute_uri(b.image.url)} for b in hero_banners],
            "full_ad": request.build_absolute_uri(full_ads[0].image.url) if full_ads.exists() else None,
            "sidebar_ad": request.build_absolute_uri(sidebar_ads[0].image.url) if sidebar_ads.exists() else None,
        }, status=status.HTTP_200_OK)


class NLPSearchEngine:
    def __init__(self):
        try:
            model_dir = settings.MODEL_DIR
            self.parser = joblib.load(os.path.join(model_dir, 'nlp_search_parser.joblib'))
        except Exception as e:
            print(f"Warning: NLP Model not loaded. {e}")
            self.parser = None

    def parse_query(self, query_text):
        if self.parser:

            pass
        

        text = query_text.lower()
        result = {"purpose": "Rent", "property_type": "Apartment", "area": "Any", "beds": "Any", "budget": 200000}
        
        if "buy" in text or "sale" in text: result["purpose"] = "Sale"
        if "house" in text or "duplex" in text: result["property_type"] = "House"
        if "commercial" in text or "office" in text: result["property_type"] = "Commercial"
        

        bed_match = re.search(r'(\d+)\s*(bed|bhk)', text)
        if bed_match: result["beds"] = bed_match.group(1)
        

        budget_match = re.search(r'(under|max)\s*(\d+)(k|lakh)', text)
        if budget_match:
            val = int(budget_match.group(2))
            if budget_match.group(3) == 'k': result["budget"] = val * 1000
            elif budget_match.group(3) == 'lakh': result["budget"] = val * 100000
            

        areas = ["gulshan", "banani", "dhanmondi", "zindabazar", "bashundhara"]
        for a in areas:
            if a in text: result["area"] = a.capitalize()
            
        return result

class NLPSearchView(APIView):
    def post(self, request):
        query_text = request.data.get('query_text', '')
        if not query_text:
            return Response({"error": "Please enter a search query."}, status=status.HTTP_400_BAD_REQUEST)
        
        engine = NLPSearchEngine()
        parsed_filters = engine.parse_query(query_text)
        
        return Response(parsed_filters, status=status.HTTP_200_OK)
    




class ContactFormView(APIView):
    def post(self, request):
        try:
            ContactMessage.objects.create(
                name=request.data.get('name'),
                email=request.data.get('email'),
                subject=request.data.get('subject'),
                department=request.data.get('department'),
                message=request.data.get('message')
            )
            return Response({"success": "Message sent successfully! We will get back to you soon."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": "Failed to send message."}, status=status.HTTP_400_BAD_REQUEST)


class FAQChatbotView(APIView):

    _vector_db = None

    @classmethod
    def get_vector_db(cls):

        if cls._vector_db is None:
            print("🚀 Loading FAISS AI into RAM... (This only happens once!)")
            index_path = os.path.join(settings.MODEL_DIR, 'sylhetstay_faq_faiss_index')
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            cls._vector_db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        return cls._vector_db

    def post(self, request):
        user_message = request.data.get('user_message', '')
        if not user_message:
            return Response({"error": "Please enter a question."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:

            vector_db = self.get_vector_db()
            

            docs_and_scores = vector_db.similarity_search_with_score(user_message, k=2)
            
            valid_answers = []
            for doc, score in docs_and_scores:
                if score < 1.2:  
                    valid_answers.append(doc.page_content)
            
            if valid_answers:
                ai_answer = "\n\n".join(valid_answers)
            else:
                ai_answer = "I'm sorry, I couldn't find an answer to that in my FAQ database. Please use the contact form to reach our human team!"
            
            return Response({"answer": ai_answer}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": f"FAISS Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)