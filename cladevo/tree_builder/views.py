from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt  # Temporary (Not recommended for production)
#import calculator_upgma here


method = "nj"

# Create your views here.
def parameters(request):
    return render(request, "tree_builder/parameters.html")

def sequence_input(request):
    return render(request, "tree_builder/input.html")

@csrf_exempt  # Only for testing; remove it when using CSRF tokens in AJAX
def submit_sequences(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Read JSON data

            sequence_names = data.get("sequence_name", [])  # Get array of names
            sequence_data = data.get("sequence_data", [])  # Get array of sequences

            print("Received Sequences:", sequence_names, sequence_data)
            # (Optional) Save to database or process the data

            return JsonResponse({"message": "Data received successfully!", "redirect_url": "/success/"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)
