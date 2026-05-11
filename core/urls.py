from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('geomap/', views.geomap, name='geomap'),
    path('monitoring/', views.monitoring, name='monitoring'),
    path('review/', views.review_queue, name='review_queue'),
    path('api/review/<int:pk>/', views.api_review_action, name='api_review_action'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/deactivate/', views.user_deactivate, name='user_deactivate'),
    path('api/waste-stats/', views.api_waste_stats, name='api_waste_stats'),
    path('api/waste-timeseries/', views.api_waste_timeseries, name='api_waste_timeseries'),
    path('api/recent-items/', views.api_recent_items, name='api_recent_items'),
    path('api/geomap-data/', views.api_geomap_data, name='api_geomap_data'),
    path('api/add-waste-item/', views.api_add_waste_item, name='api_add_waste_item'),
]
