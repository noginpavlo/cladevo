# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run from `cladevo/` (the Django project root, where `manage.py` lives).

```bash
# Install dependencies (from repo root)
pip install -r requirements.txt

# Run development server
cd cladevo && python manage.py runserver

# Run migrations
python manage.py migrate

# Run tests
python manage.py test

# Run a single app's tests
python manage.py test tree_builder
python manage.py test static_pages
```

ClustalW must be installed at `/usr/bin/clustalw` — it is a hard dependency called via subprocess for sequence alignment. On Debian/Ubuntu: `sudo apt install clustalw`.

## Architecture

The project is a Django 5.1 web app. The Django project config is at `cladevo/cladevo/` (settings, root URLs). There are two Django apps:

**`static_pages/`** — purely informational pages (home, about, theory, docs). No models, no forms. Views just call `render()`.

**`tree_builder/`** — the entire functional core. A single request pipeline:
1. `views.py` receives POST data (manual sequences, FASTA file, or Excel file)
2. Calls `TreeBuilder` methods in sequence: `align_sequences()` → `calculate_dissimilarity_matrix()` → `build_tree(method)` → `visualize_tree()`
3. Returns a redirect URL to `/tree_builder/result/<uuid>/`
4. The result page serves the PNG from `static/plots/tree_<uuid>.png`

**`services/calculator_upgma.py`** — the `TreeBuilder` class. This is the only file with real logic. It holds intermediate computation state on `self` (`aligned_file`, `dissimilarity_matrix`, `tree`). The `reformat()` method handles Excel input: it encodes binary SSR genotyping data (`1`/`0`) as `A`/`T` nucleotides to produce a synthetic alignment that bypasses ClustalW.

## Known Architectural Issues

- `calculator` and `method` in `views.py` are **module-level globals** — `TreeBuilder` is a singleton shared across all requests. Concurrent requests will corrupt each other's state.
- The method selection (UPGMA vs NJ) is sent to `get-method/` in a separate AJAX call before the computation request — introducing a race condition for concurrent users.
- All pipeline failures (`align_sequences`, `calculate_dissimilarity_matrix`, `build_tree`) fail silently by returning `None` rather than raising exceptions. The view only detects failure at the final `visualize_tree()` step.
- Generated tree PNGs are stored in `static/plots/` (wrong — user-generated files should use `MEDIA_ROOT`). Uploads go to `static/uploads/`.
- `SECRET_KEY` is hardcoded in `settings.py`. `DEBUG = True` and `ALLOWED_HOSTS = []` — not production-safe.

## URL Structure

| URL | View | Purpose |
|-----|------|---------|
| `/` | `static_pages.home` | Landing page |
| `/tree_builder/parameters/` | `parameters` | Algorithm + input type selection |
| `/tree_builder/sequence_input/` | `sequence_input` | Manual DNA entry UI |
| `/tree_builder/submit_sequences/` | `submit_sequences` | POST: manual sequence data |
| `/tree_builder/submit_file/` | `submit_file` | POST: FASTA or Excel file upload |
| `/tree_builder/get-method/` | `get_method` | POST: sets global algorithm choice |
| `/tree_builder/result/<uuid>/` | `show_result` | Displays generated tree PNG |
