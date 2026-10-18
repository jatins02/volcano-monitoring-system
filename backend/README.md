# Backend scaffold

FastAPI and Uvicorn are pinned in the root requirements.in/requirements.lock and installed into .venv by `make setup-python`. Stage 1 checks their versions and importability, but does not implement an API or start a backend server. Stage 7 owns typed routes, validation, SQLite and subprocess coordination.

Production modules must not import tests/reference_model.py. Do not substitute Python monitoring calculations for Logisim or assembly results.
