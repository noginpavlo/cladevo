from django.urls import path
from . import views

urlpatterns = [
    path("parameters/", views.parameters, name="parameters"),
    path("sequence_input/", views.sequence_input, name="sequence_input"),
]