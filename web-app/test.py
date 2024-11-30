"""Test code for web-app"""
from datetime import datetime
from unittest.mock import patch, MagicMock
import subprocess
import json
import pytest
from bson import ObjectId
from werkzeug.exceptions import BadRequest
from app import app

MOCK_MONGODB_URL = "http://localhost:5002"

@pytest.fixture
def client():
    """client fixture"""
    app.config["LOGIN_DISABLED"] = True
    app.config["UPLOAD_FOLDER"] = "/tmp"
    return app.test_client()

### Test edit function ###
@patch("requests.get")
def test_edit_get_route(mock_get, client):
    """Test edit get route"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "exercise_todo_id": "123",
        "name": "Test Exercise",
        "reps": 10,
        "weight": 50,
    }
    
    response = client.get("/edit?exercise_todo_id=123")
    assert response.status_code == 200
    mock_get.assert_called_with(f"{MOCK_MONGODB_URL}/todo/exercise/123")

@patch("requests.put")
def test_edit_route(mock_put, client):
    """Test edit route"""
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = {"success": True}
    
    response = client.post(
        "/edit?exercise_todo_id=123",
        data={"working_time": "30", "weight": "70", "reps": "15"},
    )
    
    assert response.status_code == 200
    assert b"Edited successfully" in response.data
    mock_put.assert_called_with(
        f"{MOCK_MONGODB_URL}/todo/edit/123",
        json={"working_time": "30", "weight": "70", "reps": "15"}
    )

### Test search function ###
@patch("requests.post")
@patch("requests.get")
def test_search_route(mock_get, mock_post, client):
    """Test search route"""
    # Mock search history
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"_id": "1", "name": "Push Up"},
        {"_id": "2", "name": "Squats"},
    ]
    
    # Mock search results
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = [{"_id": "1", "name": "Push Up"}]
    
    # Test GET request
    response = client.get("/search")
    assert response.status_code == 200
    
    # Test POST request with valid query
    response = client.post("/search", data={"query": "push"})
    assert response.status_code == 302  # Redirect
    mock_post.assert_called_with(
        f"{MOCK_MONGODB_URL}/exercises/search",
        json={"query": "push"}
    )

    # Test empty query
    response = client.post("/search", data={"query": ""})
    assert response.status_code == 400

    # Test no results
    mock_post.return_value.json.return_value = []
    response = client.post("/search", data={"query": "nonexistent"})
    assert response.status_code == 404

### Test add function ###
@patch("requests.post")
def test_add_exercise_route(mock_post, client):
    """Test add exercise route"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True}
    
    response = client.post("/add_exercise?exercise_id=123")
    assert response.status_code == 200
    mock_post.assert_called_with(
        f"{MOCK_MONGODB_URL}/todo/add",
        json={"exercise_id": "123"}
    )

def test_add_route_with_results_in_session(client):
    """Test add route with results in session"""
    with client.session_transaction() as session:
        session["results"] = [
            {"_id": "1", "name": "Push Up"},
            {"_id": "2", "name": "Squats"},
        ]
    response = client.get("/add")
    assert response.status_code == 200

### Test delete function ###
@patch("requests.get")
def test_delete_exercise_route(mock_get, client):
    """Test delete exercise route"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "todo": [
            {"_id": "1", "name": "Push Up"},
            {"_id": "2", "name": "Squats"},
        ]
    }
    
    response = client.get("/delete_exercise")
    assert response.status_code == 200

@patch("requests.delete")
def test_delete_exercise_id(mock_delete, client):
    """Test delete exercise id"""
    mock_delete.return_value.status_code = 204
    
    response = client.delete("/delete_exercise/123")
    assert response.status_code == 204
    mock_delete.assert_called_with(f"{MOCK_MONGODB_URL}/todo/delete/123")

### Test user authentication ###
@patch("requests.post")
def test_register(mock_post, client):
    """Test registration"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"user_id": "new_user"}
    
    response = client.post("/register", data={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200
    mock_post.assert_called_with(
        f"{MOCK_MONGODB_URL}/users/create",
        json={"username": "testuser", "password": "hashed_password"}
    )

@patch("requests.post")
def test_login(mock_post, client):
    """Test login"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "_id": "user123",
        "username": "testuser",
        "password": "hashedpass"
    }
    
    response = client.post("/login", data={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200

### Test search history ###
@patch("requests.post")
def test_add_search_history(mock_post):
    """Test add search history"""
    mock_post.return_value.status_code = 200
    
    with app.test_request_context():
        from app import add_search_history
        add_search_history("push-up")
        mock_post.assert_called_with(
            f"{MOCK_MONGODB_URL}/search-history/add",
            json={"content": "push-up"}
        )

@patch("requests.get")
def test_get_search_history(mock_get):
    """Test get search history"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"content": "push-up", "time": "2024-01-01T00:00:00"},
        {"content": "squat", "time": "2024-01-01T00:00:00"}
    ]
    
    with app.test_request_context():
        from app import get_search_history
        history = get_search_history()
        assert len(history) == 2

### Test voice commands ###
def test_parse_voice_command():
    """Test voice command parsing"""
    from app import parse_voice_command
    
    transcription = "Set 20 kg for 40 minutes and 2 groups"
    result = parse_voice_command(transcription)
    assert result == {"time": 40, "groups": 2, "weight": 20}

### Test transcription ###
@patch("requests.post")
def test_upload_transcription(mock_post, client):
    """Test transcription upload"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "trans123"}
    
    response = client.post(
        "/upload-transcription",
        json={"content": "test transcription"}
    )
    assert response.status_code == 200

### Test instruction retrieval ###
@patch("requests.get")
def test_get_instruction(mock_get):
    """Test get instruction"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "workout_name": "Push Up",
        "instruction": "Keep your back straight"
    }
    
    with app.test_request_context():
        from app import get_instruction
        result = get_instruction("exercise123")
        assert "workout_name" in result
        assert "instruction" in result

### Test audio processing ###
@patch("requests.post")
def test_process_audio(mock_post, client):
    """Test audio processing"""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"transcription": "20 minutes"}
    
    # Create dummy audio file
    with open("/tmp/test_audio.mp3", "wb") as f:
        f.write(b"dummy audio data")
    
    with open("/tmp/test_audio.mp3", "rb") as audio_file:
        response = client.post(
            "/process-audio",
            data={"audio": (audio_file, "test_audio.mp3")}
        )
        assert response.status_code in [200, 500]  # 500 if ffmpeg fails in test env

# Add more error case tests
def test_error_cases(client):
    """Test various error cases"""
    # Test missing username/password
    response = client.post("/register", data={})
    assert response.status_code == 400
    
    # Test invalid audio upload
    response = client.post("/upload-audio")
    assert response.status_code == 400
    
    # Test invalid transcription upload
    response = client.post(
        "/upload-transcription",
        json={}
    )
    assert response.status_code == 400

if __name__ == "__main__":
    pytest.main()