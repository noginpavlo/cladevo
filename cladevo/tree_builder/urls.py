from django.urls import path
from . import views
from .views import submit_sequences

urlpatterns = [
    path("parameters/", views.parameters, name="parameters"),
    path("sequence_input/", views.sequence_input, name="sequence_input"),
    path("submit_sequences/", submit_sequences, name="submit_sequences"),
]