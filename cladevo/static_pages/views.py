"""Class-based views for the static informational pages of Cladevo."""

from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Renders the home landing page."""

    template_name = "home.html"


class DocsView(TemplateView):
    """Renders the how-to-use documentation page."""

    template_name = "docs.html"


class TheoryView(TemplateView):
    """Renders the algorithm theory page."""

    template_name = "theory.html"


class AboutView(TemplateView):
    """Renders the about page."""

    template_name = "about.html"
