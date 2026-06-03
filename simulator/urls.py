from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('api/step/', views.step_simulation_api, name='api_step'),
    path('api/toggle_leak/', views.toggle_leak_api, name='api_toggle_leak'),
    path('api/toggle_pump/', views.toggle_pump_api, name='api_toggle_pump'),
    path('api/toggle_nepa/', views.toggle_nepa_api, name='api_toggle_nepa'),
    path('api/change_calendar/', views.change_calendar_api, name='api_change_calendar'),
    path('api/change_lang/', views.change_lang_api, name='api_change_lang'),
    path('api/reset/', views.reset_simulation_api, name='api_reset'),
    path('api/inject_scenario/', views.inject_scenario_api, name='api_inject_scenario'),
    path('api/toggle_node_status/', views.toggle_node_status_api, name='api_toggle_node_status'),
]
