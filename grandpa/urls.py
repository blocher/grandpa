
from django.urls import path
from . import views

urlpatterns = [
    path('', views.calendar_view, name='calendar_home'),
    path('month/<int:year>/<int:month>/', views.calendar_view, name='calendar_month'),
    path('day/<int:year>/<int:month>/<int:day>/', views.calendar_view, name='calendar_day'),
    # Add other routes as needed
]
