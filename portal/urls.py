from django.urls import path
from . import views
from portal.ml.dti_api import run_pharmalnet_prediction  # ✅ Add this import

urlpatterns = [
    # ---------------- AUTH ----------------
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ---------------- MODULE PAGES ----------------
    path('module/<str:name>/', views.module_detail, name='module_detail'),

    # Pharmal-Net Pages
    path('module/Pharmal-Net/', views.pharmalnet_train, name='pharmalnet_train'),
    path('module/Pharmal-Net/predict/', views.pharmalnet_predict, name='pharmalnet_predict'),

    # ---------------- DOWNLOADS ----------------
    path('download/', views.download_user_data, name='download_user_data'),
    path('module/<str:name>/download/', views.download_module_data, name='download_module_data'),

    # ---------------- API ----------------
    path('pharmalnet/train/', views.pharmalnet_train_api_view, name='pharmalnet_train_api'),
    path('pharmalnet/predict/', run_pharmalnet_prediction, name='pharmalnet_predict_api'),  # ✅ Keep only this one
]
