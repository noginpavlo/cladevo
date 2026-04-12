from django.urls import path

from .views import (
    GetMethodView,
    ParametersView,
    SequenceInputView,
    ShowResultView,
    SubmitFileView,
    SubmitSequencesView,
)

urlpatterns = [
    path("parameters/", ParametersView.as_view(), name="parameters"),
    path("sequence_input/", SequenceInputView.as_view(), name="sequence_input"),
    path("submit_sequences/", SubmitSequencesView.as_view(), name="submit_sequences"),
    path("result/<str:unique_id>/", ShowResultView.as_view(), name="show_result"),
    path("submit_file/", SubmitFileView.as_view(), name="submit_file"),
    path("get-method/", GetMethodView.as_view(), name="get-method"),
]
