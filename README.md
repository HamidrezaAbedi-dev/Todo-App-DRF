# Todo-App-DRF

## Running API tests

The test dependencies (`pytest` and `pytest-django`) are installed from the
root `requirements.txt` when the backend image is built. Run the tests through
the Docker Compose backend container:

```sh
docker compose exec backend python -m pytest
```

The pytest configuration is in `core/pytest.ini`; tests use the configured
Django settings and the database provided by Docker Compose.
