from django.urls import path

from .views import AboutView, DocsView, HomeView, TheoryView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("docs/", DocsView.as_view(), name="docs"),
    path("theory/", TheoryView.as_view(), name="theory"),
    path("about/", AboutView.as_view(), name="about"),
]
