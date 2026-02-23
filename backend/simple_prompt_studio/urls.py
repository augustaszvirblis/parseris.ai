from django.urls import path

from . import views

urlpatterns = [
    path("upload", views.sps_upload, name="sps-upload"),
    path("extract", views.sps_extract, name="sps-extract"),
    path("status", views.sps_status, name="sps-status"),
]
