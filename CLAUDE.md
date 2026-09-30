# Cladevo — Claude Code Instructions

## Project
Django web application. Business logic lives in `tree_builder/services/`.

## Code Style

- OOP
- Follow clean code principles, SOLID, and OOP best practices
- Keep methods small and focused on a single responsibility
- Prefer classic, well-established solutions over clever or unusual ones
- Avoid code duplication

## Python Specifics

- Always use type hints on all method parameters and return types
- Use the `typing` module where needed (`Optional`, `List`, `Dict`, `Tuple`)
- Never use mutable default arguments (e.g. `def f(x=[])` or `def f(x={})`)
- Never use bare or overly generic exceptions (`except Exception`, `except:`) — always catch specific exceptions
- Prefer explicit over implicit

## Django

- Use class-based views (CBVs) — choose the most appropriate built-in generic view for each case
- Follow standard Django project structure and conventions

## Documentation

- Every class must have a docstring
- Every method must have a docstring
- No inline comments or block comments — code should be self-explanatory

