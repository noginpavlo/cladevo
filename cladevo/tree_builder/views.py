from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt  # Temporary (Not recommended for production)
from tree_builder.services.calculator_upgma import TreeBuilder

calculator = TreeBuilder()

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

            calculator.align_sequences(sequence_names, sequence_data)
            calculator.calculate_dissimilarity_matrix()
            calculator.build_tree(method)

            unique_id = calculator.visualize_tree()

            if unique_id is None:
                return JsonResponse({'error': 'Tree visualization failed'}), 400

            redirect_url = "/show_result/"

            return JsonResponse({"message": "Data received successfully!", "redirect_url": redirect_url})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)

def show_result(request, unique_id):
    print(f"Received unique_id: {unique_id}")
    if not unique_id:
        print("Error: No unique ID provided")
        return "Error: No unique ID provided", 400

    return render(request, "tree_builder/result.html")