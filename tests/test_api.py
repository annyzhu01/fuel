import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    mock_sb = MagicMock()
    mock_sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])
    with patch("utils.get_supabase_client", return_value=mock_sb):
        from fastapi.testclient import TestClient
        import importlib
        import api as api_module
        importlib.reload(api_module)
        yield TestClient(api_module.app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_log_workout_missing_fields(client):
    response = client.post("/log-workout", json={})
    assert response.status_code == 422


def test_log_meal_invalid_slot(client):
    with patch("api.get_supabase_client"):
        response = client.post("/log-meal", json={
            "meal_slot": "brunch",
            "description": "test",
            "calories": 400,
            "protein_g": 30,
            "carbs_g": 40,
            "fat_g": 10,
        })
    assert response.status_code == 400
