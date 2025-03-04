from django.shortcuts import render
import json
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token
from tree_builder.services.calculator_upgma import TreeBuilder

# branch


calculator = TreeBuilder()
method = "upgma"


def clear_plots():
    plots_directory = os.path.join(settings.BASE_DIR, 'static', 'plots')
    entries = os.listdir(plots_directory)
    files = [entry for entry in entries if os.path.isfile(os.path.join(plots_directory, entry))]
    if len(files) > 20:
        for file in files:
            file_path = os.path.join(plots_directory, file)
            try:
                os.remove(file_path)
                print(f'Deleted: {file}')
            except Exception as e:
                print(f'Error deleting {file}: {e}')

        return "All plots were deleted."
    print("No plots were deleted (less than 20 files).")
    return "No plots were deleted (less than 20 files)."


def clear_uploads():
    uploads_directory = os.path.join(settings.BASE_DIR, 'static', 'uploads')
    entries = os.listdir(uploads_directory)
    files = [entry for entry in entries if os.path.isfile(os.path.join(uploads_directory, entry))]
    if len(files) > 20:
        for file in files:
            file_path = os.path.join(uploads_directory, file)
            try:
                os.remove(file_path)
                print(f'Deleted: {file}')
            except Exception as e:
                print(f'Error deleting {file}: {e}')

        return "All uploads were deleted."
    return "No uploads were deleted (less than 20 files)."


def parameters(request):
    return render(request, "tree_builder/parameters.html")


def sequence_input(request):
    return render(request, "tree_builder/input.html")


def show_result(request, unique_id):
    print(f"Received unique_id: {unique_id}")
    if not unique_id:
        print("Error: No unique ID provided")
        return "Error: No unique ID provided", 400

    return render(request, "tree_builder/result.html", {"unique_id": unique_id})


def get_csrf_token(request):
    """ Return the CSRF token as JSON for AJAX requests. """
    return JsonResponse({'csrfToken': get_token(request)})


@csrf_protect  # Enables CSRF protection
def get_method(request):
    global method

    if request.method == 'POST':
        method = request.POST.get('method')  # Get method from POST data
        if method:
            print(f"Now method used is {method}")
            return JsonResponse({"message": "Method updated successfully"}, status=200)
        else:
            return JsonResponse({"error": "No method selected"}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@csrf_protect
def submit_sequences(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Read JSON data

            sequence_names = data.get("sequence_name", [])  # Get array of names
            sequence_data = data.get("sequence_data", [])  # Get array of sequences

            print("Received Sequences:", sequence_names, sequence_data)

            clear_uploads()
            clear_plots()
            calculator.align_sequences(sequence_names, sequence_data)
            calculator.calculate_dissimilarity_matrix()
            calculator.build_tree(method)

            unique_id = calculator.visualize_tree()

            if unique_id is None:
                return JsonResponse({'error': 'Tree visualization failed'}, status=400)

            redirect_url = f"/tree_builder/result/{unique_id}/"

            return JsonResponse({"message": "Data received successfully!", "redirect_url": redirect_url})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


@csrf_protect
def submit_file(request):
    if request.method == "POST" and request.FILES.get("file-upload"):
        file = request.FILES["file-upload"]

        clear_uploads()

        # Save the uploaded file
        upload_dir = "static/uploads"  # Directory to save files
        os.makedirs(upload_dir, exist_ok=True)  # Ensure the directory exists
        file_path = os.path.join(upload_dir, file.name)

        with open(file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)


        # Check file extensions
        if file.name.lower().endswith(".fasta"):
            # Handle FASTA file
            calculator.align_sequences(fasta_file=file_path)
        elif file.name.lower().endswith((".xls", ".xlsx")):
            # Handle Excel file
            calculator.reformat(file_path)
        else:
            # For unsupported file types
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        clear_plots()
        calculator.calculate_dissimilarity_matrix()
        calculator.build_tree(method)
        unique_id = calculator.visualize_tree()

        if unique_id is None:
            return JsonResponse({"error": "Tree visualization failed"}, status=400)

        # Build the redirect URL
        redirect_url = f"/tree_builder/result/{unique_id}/"

        # Return the URL as JSON
        return JsonResponse({"redirect_url": redirect_url})

    return JsonResponse({"error": "Invalid request"}, status=400)
