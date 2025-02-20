from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, "home.html")

def docs(request):
    return render(request, "docs.html")

def theory(request):
    return render(request, "theory.html")

def about(request):
    return render(request, "about.html")