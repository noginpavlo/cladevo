import json
import os

from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from tree_builder.services.calculator_upgma import TreeBuilder

calculator = TreeBuilder()
method = "upgma"


def _clear_plots() -> str:
    """Delete all files in the plots directory if there are more than 20."""
    plots_directory = os.path.join(settings.BASE_DIR, "static", "plots")
    entries = os.listdir(plots_directory)
    files = [entry for entry in entries if os.path.isfile(os.path.join(plots_directory, entry))]
    if len(files) > 20:
        for file in files:
            file_path = os.path.join(plots_directory, file)
            try:
                os.remove(file_path)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")
        return "All plots were deleted."
    print("No plots were deleted (less than 20 files).")
    return "No plots were deleted (less than 20 files)."


def _clear_uploads() -> str:
    """Delete all files in the uploads directory if there are more than 20."""
    uploads_directory = os.path.join(settings.BASE_DIR, "static", "uploads")
    entries = os.listdir(uploads_directory)
    files = [entry for entry in entries if os.path.isfile(os.path.join(uploads_directory, entry))]
    if len(files) > 20:
        for file in files:
            file_path = os.path.join(uploads_directory, file)
            try:
                os.remove(file_path)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")
        return "All uploads were deleted."
    return "No uploads were deleted (less than 20 files)."


class ParametersView(TemplateView):
    """Renders the algorithm and input-type selection page."""

    template_name = "tree_builder/parameters.html"


class SequenceInputView(TemplateView):
    """Renders the manual DNA sequence entry page."""

    template_name = "tree_builder/input.html"


class ShowResultView(TemplateView):
    """Renders the result page displaying the generated phylogenetic tree."""

    template_name = "tree_builder/result.html"

    def get_context_data(self, **kwargs) -> dict:
        """Inject the unique_id URL kwarg into the template context."""
        context = super().get_context_data(**kwargs)
        unique_id = self.kwargs.get("unique_id")
        if not unique_id:
            print("Error: No unique ID provided")
        else:
            print(f"Received unique_id: {unique_id}")
        context["unique_id"] = unique_id
        return context


class CsrfTokenView(View):
    """Returns the current CSRF token as JSON for use in AJAX requests."""

    def get(self, request) -> JsonResponse:
        """Respond with the CSRF token."""
        return JsonResponse({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class GetMethodView(View):
    """Accepts a POST request to update the global tree-building algorithm choice."""

    def post(self, request) -> JsonResponse:
        """Store the selected method ('upgma' or 'nj') in the module-level global."""
        global method
        selected = request.POST.get("method")
        if selected:
            method = selected
            print(f"Now method used is {method}")
            return JsonResponse({"message": "Method updated successfully"}, status=200)
        return JsonResponse({"error": "No method selected"}, status=400)


@method_decorator(csrf_protect, name="dispatch")
class SubmitSequencesView(View):
    """Accepts a JSON POST of named DNA sequences and runs the full tree pipeline."""

    def post(self, request) -> JsonResponse:
        """Parse the request body, run the pipeline, and return a redirect URL."""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        sequence_names = data.get("sequence_name", [])
        sequence_data = data.get("sequence_data", [])

        print("Received Sequences:", sequence_names, sequence_data)

        _clear_uploads()
        _clear_plots()
        calculator.align_sequences(sequence_names, sequence_data)
        calculator.calculate_dissimilarity_matrix()
        calculator.build_tree(method)

        unique_id = calculator.visualize_tree()

        if unique_id is None:
            return JsonResponse({"error": "Tree visualization failed"}, status=400)

        redirect_url = f"/tree_builder/result/{unique_id}/"
        return JsonResponse(
            {"message": "Data received successfully!", "redirect_url": redirect_url}
        )


@method_decorator(csrf_protect, name="dispatch")
class SubmitFileView(View):
    """Accepts a file upload (FASTA or Excel) and runs the full tree pipeline."""

    def post(self, request) -> JsonResponse:
        """
        Save the uploaded file, run the appropriate pipeline entry point, and return a redirect URL.
        """
        if not request.FILES.get("file-upload"):
            return JsonResponse({"error": "Invalid request"}, status=400)

        file = request.FILES["file-upload"]

        _clear_uploads()

        upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.name)

        with open(file_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        if file.name.lower().endswith(".fasta"):
            calculator.align_sequences(fasta_file=file_path)
        elif file.name.lower().endswith((".xls", ".xlsx")):
            calculator.reformat(file_path)
        else:
            return JsonResponse({"error": "Unsupported file type"}, status=400)

        _clear_plots()
        calculator.calculate_dissimilarity_matrix()
        calculator.build_tree(method)
        unique_id = calculator.visualize_tree()

        if unique_id is None:
            return JsonResponse({"error": "Tree visualization failed"}, status=400)

        redirect_url = f"/tree_builder/result/{unique_id}/"
        return JsonResponse({"redirect_url": redirect_url})
