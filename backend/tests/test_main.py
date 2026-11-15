from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "app_name" in data


def test_cors_headers() -> None:
    """Test CORS middleware is configured."""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_app_startup() -> None:
    """Test that the FastAPI application starts correctly."""
    assert app is not None
    assert app.title == "AI Resume Screening Backend"
    assert app.version == "0.1.0"
