from django.shortcuts import render

# Create your views here.
def parameters(request):
    return render(request, "tree_builder/parameters.html")