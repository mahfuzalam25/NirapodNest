from django.urls import path
from .views import ChatDetailView, CreatePropertyView, EstimatePriceView, InboxView, NavbarInboxView, PropertyListView, PropertyDetailView, NeighborhoodInsightsView, SendMessageView, AdvancedSearchView

urlpatterns = [
    path('create/', CreatePropertyView.as_view(), name='create-property'),
    path('estimate-price/', EstimatePriceView.as_view(), name='estimate-price'),
    path('list/', PropertyListView.as_view(), name='property-list'),
    path('details/<uuid:uid>/', PropertyDetailView.as_view(), name='property-detail'),
    path('neighborhood-ai/', NeighborhoodInsightsView.as_view(), name='neighborhood-ai'),
    path('message/<uuid:uid>/', SendMessageView.as_view(), name='send-message'),
    path('navbar-inbox/', NavbarInboxView.as_view(), name='navbar-inbox'),
    path('inbox/', InboxView.as_view(), name='inbox'),
    path('chat/<uuid:uid>/', ChatDetailView.as_view(), name='chat-detail'),
    path('search/', AdvancedSearchView.as_view(), name='advanced_search'),
]