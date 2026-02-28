from django.urls import path
from .views import RadarAlertView, RadarActionView, NavbarNotificationView, trigger_radars_view, keep_alive_view, BannerAdView, NLPSearchView, ContactFormView, FAQChatbotView

urlpatterns = [
    path('radars/', RadarAlertView.as_view(), name='radars'),
    path('radars/<uuid:uid>/', RadarActionView.as_view(), name='radar-actions'),
    path('notifications/', NavbarNotificationView.as_view(), name='navbar-notifications'),
    path('trigger-radars/', trigger_radars_view, name='trigger_radars'),
    path('keep-alive/', keep_alive_view, name='keep_alive'),
    path('content/banners/', BannerAdView.as_view(), name='banners'),
    path('nlp-search/', NLPSearchView.as_view(), name='nlp_search'),
    path('contact/submit/', ContactFormView.as_view(), name='contact_submit'),
    path('contact/chatbot/', FAQChatbotView.as_view(), name='contact_chatbot'),
]