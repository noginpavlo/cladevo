from django.urls import path
from . import views
from .views import submit_sequences, show_result, submit_file, get_method

urlpatterns = [
    path("parameters/", views.parameters, name="parameters"),
    path("sequence_input/", views.sequence_input, name="sequence_input"),
    path("submit_sequences/", submit_sequences, name="submit_sequences"),
    path("result/<str:unique_id>/", show_result, name="show_result"),
    path("submit_file/", submit_file, name="submit_file"),
    path("get-method/", get_method, name="get-method"),
]