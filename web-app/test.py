"""Test code for web-app"""

# pylint: disable=C0302
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import ANY, patch, MagicMock, Mock
import subprocess
import json
import pytest
import re
from bson import ObjectId
from app import (
    app,
    get_user_by_id,
    update_user_by_id,
    normalize_text,
    search_exercise,
    get_exercise,
    get_all_exercises,
    get_todo,
    get_today_todo,
    add_todo_api,
    add_search_history_api,
    get_exercise_in_todo,
    get_instruction,
    get_search_history,
    parse_voice_command,
    insert_transcription_entry_api,
    load_user,
)
import requests


@pytest.fixture
def client():
    """client fixture"""
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.config["UPLOAD_FOLDER"] = "/tmp"
    with app.test_client() as client:
        yield client

DB_SERVICE_URL = "http://db-service:5112/"

### Test get_user_by_id function ###
@patch("requests.get")
def test_get_user_by_id_success(mock_get):
    """Test get_user_by_id function with successful API response."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "id": 1,
        "name": "testuser",
        "email": "testuser@gmail.com",
    }
    user = get_user_by_id(1)

    assert user is not None
    assert user["id"] == 1
    assert user["name"] == "testuser"
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/1")


@patch("requests.get")
def test_get_user_by_id_not_found(mock_get):
    """Test get_user_by_id function with user not found."""
    mock_get.return_value.status_code = 404
    user = get_user_by_id(2)

    assert user is None
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/2")


@patch("requests.get")
def test_get_user_by_id_exception(mock_get):
    """Test get_user_by_id function when exception occurs."""
    mock_get.side_effect = requests.RequestException("Connection error")
    user = get_user_by_id(3)

    assert user is None
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/3")


### Test update_user_by_id function ###
@patch("requests.put")
def test_update_user_by_id_success(mock_put):
    """Test update_user_by_id function with successful update."""
    mock_put.return_value.status_code = 200

    update_fields = {"name": "testusers", "email": "testuser@gmail.com"}
    result = update_user_by_id(1, update_fields)

    assert result is True
    mock_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/1",
        json=update_fields
    )


@patch("requests.put")
def test_update_user_by_id_failure(mock_put):
    """Test update_user_by_id function when update fails."""
    mock_put.return_value.status_code = 400

    update_fields = {"name": "testuser"}
    result = update_user_by_id(2, update_fields)

    assert result is False
    mock_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/2",
        json=update_fields
    )


@patch("requests.put")
def test_update_user_by_id_exception(mock_put):
    """Test update_user_by_id function when exception occurs."""
    mock_put.side_effect = requests.RequestException("Connection error")
    update_field = {"name": "testuser"}

    result = update_user_by_id(3, update_field)

    assert result is False
    mock_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/3",
        json=update_field
    )

### Test normalize_text function ###
@patch("app.normalize_text")
def test_normalize_text_success(mock_normalize_text):
    """Test normalize_text function with valid inputs."""
    mock_normalize_text.side_effect = lambda text: re.sub(r"[\s\-]", "", text).lower()

    test_cases = [
        ("Hello World", "helloworld"),
        ("HELLO-WORLD", "helloworld"),
        ("hello-world ", "helloworld"),
        ("Hello  World", "helloworld"),
        ("search-query-test", "searchquerytest"),
        ("", ""),
        ("  ", ""),
        ("123-456 789", "123456789"),
        ("special!@#", "special!@#"),
    ]

    for input_text, expected_output in test_cases:
        result = normalize_text(input_text)
        assert result == expected_output

### Test search_exercise function ###
@patch("requests.post")
def test_search_exercise_success(mock_post):
    """Test search_exercise function with a successful API response."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = [
        {"id": 1, "name": "Push-Up"},
        {"id": 2, "name": "Pull-Up"},
    ]
    
    query = "Push"
    results = search_exercise(query)
    
    assert results is not None
    assert len(results) == 2
    assert results[0]["name"] == "Push-Up"
    assert results[1]["name"] == "Pull-Up"
    mock_post.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/search", json={"query": query})


@patch("requests.post")
def test_search_exercise_no_results(mock_post):
    """Test search_exercise function with no results found."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = []
    
    query = "Nonexistent Exercise"
    results = search_exercise(query)
    
    assert results == []
    mock_post.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/search", json={"query": query})


@patch("requests.post")
def test_search_exercise_api_failure(mock_post):
    """Test search_exercise function when the API fails."""
    mock_post.return_value.status_code = 500
    
    query = "Push"
    results = search_exercise(query)
    
    assert results == []
    mock_post.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/search", json={"query": query})


@patch("requests.post")
def test_search_exercise_request_exception(mock_post):
    """Test search_exercise function when a RequestException is raised."""
    mock_post.side_effect = requests.RequestException("API is unavailable")
    query = "Push Up"
    results = search_exercise(query)
    
    assert results == []
    mock_post.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/search", json={"query": query})

### Test get_exercise function ###
@patch("requests.get")
def test_get_exercise_success(mock_get):
    """Test get_exercise function with a successful API response."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "id": "123",
        "name": "Push-Up",
        "description": "An upper-body exercise",
    }

    exercise_id = "123"
    exercise = get_exercise(exercise_id)
    
    assert exercise is not None
    assert exercise["id"] == "123"
    assert exercise["name"] == "Push-Up"
    assert exercise["description"] == "An upper-body exercise"
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/get/{exercise_id}")


@patch("requests.get")
def test_get_exercise_not_found(mock_get):
    """Test get_exercise function when the exercise is not found."""
    mock_get.return_value.status_code = 404
    exercise_id = "999"
    exercise = get_exercise(exercise_id)

    assert exercise is None
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/get/{exercise_id}")


@patch("requests.get")
def test_get_exercise_api_failure(mock_get):
    """Test get_exercise function when the API fails."""
    mock_get.return_value.status_code = 500
    exercise_id = "123"
    exercise = get_exercise(exercise_id)
    
    assert exercise is None
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/get/{exercise_id}")


@patch("requests.get")
def test_get_exercise_request_exception(mock_get):
    """Test get_exercise function for a RequestException."""
    mock_get.side_effect = requests.RequestException("API is unavailable")
    exercise_id = "123"
    exercise = get_exercise(exercise_id)
    
    assert exercise is None
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/get/{exercise_id}")

### Test get_all_exercises function ###
@patch("requests.get")
def test_get_all_exercises_success(mock_get):
    """Test get_all_exercises function with a successful API response."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"id": "1", "name": "Push-Up"},
        {"id": "2", "name": "Pull-Up"},
    ]
    
    exercises = get_all_exercises()
    assert len(exercises) == 2
    assert exercises[0]["name"] == "Push-Up"
    assert exercises[1]["name"] == "Pull-Up"
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/all")


@patch("requests.get")
def test_get_all_exercises_empty(mock_get):
    """Test when no exercises are found."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []
    exercises = get_all_exercises()
    
    assert len(exercises) == 0
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/all")


@patch("requests.get")
def test_get_all_exercises_api_failure(mock_get):
    """Test when the API fails."""
    mock_get.return_value.status_code = 500
    exercises = get_all_exercises()
    
    assert exercises == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/all")


@patch("requests.get")
def test_get_all_exercises_request_exception(mock_get):
    """Test get_all_exercises function when a RequestException is raised."""
    mock_get.side_effect = requests.RequestException("API is unavailable")
    exercises = get_all_exercises()
    
    assert exercises == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/exercises/all")

### Test get_todo function ###
@patch("requests.get")
@patch("app.current_user")
def test_get_todo_success(mock_current_user, mock_get):
    """Test get_todo function with a successful API response."""
    mock_current_user.id = 123

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "todo": [
            {"id": 1, "task": "Buy groceries", "status": "incomplete"},
            {"id": 2, "task": "Clean the house", "status": "complete"},
        ]
    }
    todo_list = get_todo()
    assert len(todo_list) == 2
    assert todo_list[0]["task"] == "Buy groceries"
    assert todo_list[1]["status"] == "complete"
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")


@patch("requests.get")
@patch("app.current_user")
def test_get_todo_empty(mock_current_user, mock_get):
    """Test get_todo function when no items are found in the to-do list."""
    mock_current_user.id = 123

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"todo": []}
    todo_list = get_todo()

    assert len(todo_list) == 0
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")


@patch("requests.get")
@patch("app.current_user")
def test_get_todo_api_failure(mock_current_user, mock_get):
    """Test get_todo function when the API fails."""
    mock_current_user.id = 123

    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Internal Server Error"
    todo_list = get_todo()

    assert todo_list == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")


@patch("requests.get")
@patch("app.current_user")
def test_get_todo_request_exception(mock_current_user, mock_get):
    """Test get_todo function when a RequestException is raised."""
    mock_current_user.id = 123
    mock_get.side_effect = requests.RequestException("API is unavailable")

    todo_list = get_todo()
    assert todo_list == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")

### Test get_today_todo function ###
@patch("app.requests.get")
@patch("app.current_user")
def test_get_today_todo_success(mock_current_user, mock_requests):
    """Test get_today_todo function with a successful API response."""
    mock_current_user.id = 123
    eastern_time = datetime.now(ZoneInfo("America/New_York"))
    utc_time = eastern_time.astimezone(ZoneInfo("UTC"))
    today_date = utc_time.strftime("%Y-%m-%d")

    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "todo": [
            {"id": 1, "time": today_date, "task": "Test Task Today"},
            {"id": 2, "time": "2024-12-01", "task": "Old Task"},
        ]
    }

    today_todo = get_today_todo()

    assert len(today_todo) == 1
    assert today_todo[0]["task"] == "Test Task Today"
    assert today_todo[0]["time"] == today_date
    mock_requests.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")

@patch("app.requests.get")
@patch("app.current_user")
def test_get_today_todo_no_tasks(mock_current_user, mock_requests):
    """Test get_today_todo function when no tasks are returned for today."""
    mock_current_user.id = 123
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "todo": [
            {"id": 1, "time": "2024-12-01", "task": "Squat"}
        ]
    }
    today_todo = get_today_todo()
    assert len(today_todo) == 0
    mock_requests.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")

@patch("app.requests.get")
@patch("app.current_user")
def test_get_today_todo_api_error(mock_current_user, mock_requests):
    """Test get_today_todo function when API returns an error."""
    mock_current_user.id = 123
    mock_requests.return_value.status_code = 500

    today_todo = get_today_todo()
    assert today_todo == []
    mock_requests.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")

@patch("app.requests.get")
@patch("app.current_user")
def test_get_today_todo_empty_response(mock_current_user, mock_requests):
    """Test get_today_todo function with an empty response."""
    mock_current_user.id = 123
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {}

    today_todo = get_today_todo()
    assert today_todo == []
    mock_requests.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")

### Test add_todo_api function ###
@patch("app.requests.post")
@patch("app.current_user")
@patch("app.get_exercise")
def test_add_todo_api_success(mock_get_exercise, mock_current_user, mock_post):
    """Test add_todo_api function with successful addition."""
    mock_current_user.id = 123
    mock_get_exercise.return_value = {"workout_name": "Test Exercise"}

    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True}

    result = add_todo_api(
        exercise_id="exercise123",
        date="2024-12-04",
        working_time=30,
        reps=10,
        weight=50,
    )

    assert result is True
    mock_get_exercise.assert_called_once_with("exercise123")
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/add",
        json={
            "user_id": 123,
            "date": "2024-12-04",
            "exercise_item": {
                "exercise_todo_id": ANY,
                "exercise_id": "exercise123",
                "workout_name": "Test Exercise",
                "working_time": 30,
                "reps": 10,
                "weight": 50,
                "time": ANY,
            },
        },
    )


@patch("app.requests.post")
@patch("app.current_user")
@patch("app.get_exercise")
def test_add_todo_api_failure(mock_get_exercise, mock_current_user, mock_post):
    """Test add_todo_api function when exercise retrieval fails."""
    mock_current_user.id = 123
    mock_get_exercise.return_value = None

    result = add_todo_api(
        exercise_id="invalid_exercise",
        date="2024-12-02",
        working_time=30,
        reps=10,
        weight=50,
    )

    assert result is False
    mock_get_exercise.assert_called_once_with("invalid_exercise")
    mock_post.assert_not_called()


@patch("app.requests.post")
@patch("app.current_user")
@patch("app.get_exercise")
def test_add_todo_api_request_exception(mock_get_exercise, mock_current_user, mock_post):
    """Test add_todo_api function when an exception occurs during the API call."""
    mock_current_user.id = 123
    mock_get_exercise.return_value = {"workout_name": "Test Exercise"}
    mock_post.side_effect = requests.RequestException("API error")

    result = add_todo_api(
        exercise_id="exercise123",
        date="2024-12-04",
        working_time=30,
        reps=10,
        weight=50,
    )

    assert result is False
    mock_get_exercise.assert_called_once_with("exercise123")
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/add",
        json={
            "user_id": 123,
            "date": "2024-12-04",
            "exercise_item": {
                "exercise_todo_id": ANY,
                "exercise_id": "exercise123",
                "workout_name": "Test Exercise",
                "working_time": 30,
                "reps": 10,
                "weight": 50,
                "time": ANY,
            },
        },
    )


### Test add_search_history_api function ###
@patch("app.requests.post")
@patch("app.current_user")
def test_add_search_history_api_success(mock_current_user, mock_post):
    """Test add_search_history_api function with successful addition."""
    mock_current_user.id = 123
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True}

    result = add_search_history_api(content="test query")

    assert result is True
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/search-history/add",
        json={
            "user_id": 123,
            "content": "test query",
        },
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_add_search_history_api_failure(mock_current_user, mock_post):
    """Test add_search_history_api function when API returns failure."""
    mock_current_user.id = 123
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": False}
    result = add_search_history_api(content="test query")

    assert result is False
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/search-history/add",
        json={
            "user_id": 123,
            "content": "test query",
        },
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_add_search_history_api_request_exception(mock_current_user, mock_post):
    """Test add_search_history_api function when an exception occurs."""
    mock_current_user.id = 123
    mock_post.side_effect = requests.RequestException("API error")
    result = add_search_history_api(content="test query")

    assert result is False
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/search-history/add",
        json={
            "user_id": 123,
            "content": "test query",
        },
    )


### Test get_search_history function ###
@patch("app.requests.get")
@patch("app.current_user")
def test_get_search_history_success(mock_current_user, mock_get):
    """Test get_search_history function with successful retrieval."""
    mock_current_user.id = 123
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"content": "testquery1", "timestamp": "2024-12-05T10:00:00Z"},
        {"content": "testquery2", "timestamp": "2024-12-05T11:00:00Z"},
    ]

    result = get_search_history()

    assert result == [
        {"content": "testquery1", "timestamp": "2024-12-05T10:00:00Z"},
        {"content": "testquery2", "timestamp": "2024-12-05T11:00:00Z"},
    ]
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/search-history/get/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_get_search_history_empty(mock_current_user, mock_get):
    """Test get_search_history function when the API returns no history."""
    mock_current_user.id = 123
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = []

    result = get_search_history()
    assert result == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/search-history/get/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_get_search_history_failure(mock_current_user, mock_get):
    """Test get_search_history function when the API returns an error."""
    mock_current_user.id = 123
    mock_get.return_value.status_code = 500
    result = get_search_history()

    assert result == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/search-history/get/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_get_search_history_request_exception(mock_current_user, mock_get):
    """Test get_search_history function when a request exception occurs."""
    mock_current_user.id = 123
    mock_get.side_effect = requests.RequestException("API error")
    result = get_search_history()

    assert result == []
    mock_get.assert_called_once_with(f"{DB_SERVICE_URL}/search-history/get/123")


### Test get exercise in todo function ###
@patch("app.get_todo")
def test_get_exercise_in_todo_found(mock_get_todo):
    """Test get_exercise_in_todo function when the exercise is found."""
    mock_get_todo.return_value = [
        {"exercise_todo_id": 1, "task": "Push-Ups"},
        {"exercise_todo_id": 2, "task": "Sit-Ups"},
    ]
    result = get_exercise_in_todo(1)

    assert result == {"exercise_todo_id": 1, "task": "Push-Ups"}
    mock_get_todo.assert_called_once()


@patch("app.get_todo")
def test_get_exercise_in_todo_not_found(mock_get_todo):
    """Test get_exercise_in_todo function when the exercise is not found."""
    mock_get_todo.return_value = [
        {"exercise_todo_id": 1, "task": "Push-Ups"},
        {"exercise_todo_id": 2, "task": "Sit-Ups"},
    ]

    result = get_exercise_in_todo(3)

    assert result is None
    mock_get_todo.assert_called_once()


@patch("app.get_todo")
def test_get_exercise_in_todo_empty_list(mock_get_todo):
    """Test get_exercise_in_todo function when the to-do list is empty."""
    mock_get_todo.return_value = []
    result = get_exercise_in_todo(1)

    assert result is None
    mock_get_todo.assert_called_once()

### Test get instruction function ###
@patch("app.get_exercise")
def test_get_instruction_success(mock_get_exercise):
    """Test get_instruction function with a valid exercise ID."""
    mock_get_exercise.return_value = {
        "workout_name": "Push-Ups",
        "instruction": "Keep your back straight and lower yourself to the floor.",
    }
    res = get_instruction("exercise123")

    assert res == {
        "workout_name": "Push-Ups",
        "instruction": "Keep your back straight and lower yourself to the floor.",
    }
    mock_get_exercise.assert_called_once_with("exercise123")


@patch("app.get_exercise")
def test_get_instruction_missing_instruction(mock_get_exercise):
    """Test get_instruction function when instruction is missing."""
    mock_get_exercise.return_value = {
        "workout_name": "Sit-Ups",
    }
    res = get_instruction("exercise456")

    assert res == {
        "workout_name": "Sit-Ups",
        "instruction": "No instructions for this exercise.",
    }
    mock_get_exercise.assert_called_once_with("exercise456")


@patch("app.get_exercise")
def test_get_instruction_exercise_not_found(mock_get_exercise):
    """Test get_instruction function when the exercise is not found."""
    mock_get_exercise.return_value = None
    result = get_instruction("exercise789")

    assert result == {"error": "Exercise with ID exercise789 not found."}
    mock_get_exercise.assert_called_once_with("exercise789")

### Test parse_voice_command function ###
def test_parse_voice_command():
    """Test the parse_voice_command function."""
    transcription = "Use 25 kilograms for the workout."
    result = parse_voice_command(transcription)
    assert result == {"time": None, "groups": None, "weight": 25}
    transcription = "Let's just chat today."
    result = parse_voice_command(transcription)
    assert result == {"time": None, "groups": None, "weight": None}
    transcription = "Set 20 kg for 40 minutes and 2 groups."
    result = parse_voice_command(transcription)
    assert result == {"time": 40, "groups": 2, "weight": 20}
    transcription = "Workout with 50 kg for 10 minutes and 3 groups."
    result = parse_voice_command(transcription)
    assert result == {"time": 10, "groups": 3, "weight": 50}

### Test insert_transcription_entry_api function ###
@patch("app.requests.post")
@patch("app.current_user")
def test_insert_transcription_entry_api_success(mock_current_user, mock_post):
    """Test insert_transcription_entry_api function with successful API call."""
    mock_current_user.id = 123
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "transcript_123"}

    res = insert_transcription_entry_api(content="Test transcription.")

    assert res == "transcript_123"
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/transcriptions/add",
        json={"user_id": 123, "content": "Test transcription."},
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_insert_transcription_entry_api_failure(mock_current_user, mock_post):
    """Test insert_transcription_entry_api function when the API returns an error."""
    mock_current_user.id = 123
    mock_post.return_value.status_code = 500
    mock_post.return_value.json.return_value = {}

    res = insert_transcription_entry_api(content="Test transcription.")

    assert res is None
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/transcriptions/add",
        json={"user_id": 123, "content": "Test transcription."},
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_insert_transcription_entry_api_request_exception(mock_current_user, mock_post):
    """Test insert_transcription_entry_api function when a request exception occurs."""
    mock_current_user.id = 123
    mock_post.side_effect = requests.RequestException("API error")
    result = insert_transcription_entry_api(content="This is a test transcription.")

    assert result is None
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/transcriptions/add",
        json={"user_id": 123, "content": "This is a test transcription."},
    )

### Test load_user function ###
@patch("app.User.get") 
def test_load_user(mock_get):
    """Test load_user function."""
    mock_get.return_value = {"id": 123, "username": "testuser"}
    result = load_user(123)

    # Assertions
    assert result == {"id": 123, "username": "testuser"}
    mock_get.assert_called_once_with(123)


### Test home route ###
def test_home_redirect(client):
    """Test that the home route redirects to the To-Do page."""
    response = client.get("/")
    assert response.status_code == 302
    assert response.location.endswith("/todo") 

### Test signup_page route ###
def test_signup_page(client):
    """Test that the signup page renders the signup template."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"<h1>Sign Up</h1>" in response.data


### Test login_page route ###
def test_login_page(client):
    """Test that the login page renders the login template."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"<h1>Login</h1>" in response.data  

### Test register route ###
@patch("app.requests.post")
def test_register_success(mock_post, client):
    """Test successful user registration."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"user_id": 123}

    response = client.post(
        "/register", data={"username": "newuser", "password": "password123"}
    )

    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["message"] == "Register successful! Please Login now."
    assert response.json["redirect_url"] == "/todo"


@patch("app.requests.post")
def test_register_missing_credentials(mock_post, client):
    """Test registration with missing username or password."""
    response = client.post("/register", data={"username": "", "password": "password123"})
    assert response.status_code == 400
    assert response.json["success"] is False
    assert response.json["message"] == "Username and password are required!"

    response = client.post("/register", data={"username": "newuser", "password": ""})
    assert response.status_code == 400
    assert response.json["success"] is False
    assert response.json["message"] == "Username and password are required!"
    mock_post.assert_not_called()


@patch("app.requests.post")
def test_register_service_error(mock_post, client):
    """Test registration when the database service returns an error."""
    mock_post.return_value.status_code = 500
    mock_post.return_value.json.return_value = {"message": "Internal Server Error"}

    response = client.post(
        "/register", data={"username": "newuser", "password": "password123"}
    )

    assert response.status_code == 400
    assert response.json["success"] is False
    assert response.json["message"] == "Internal Server Error"


@patch("app.requests.post")
def test_register_request_exception(mock_post, client):
    """Test registration when a request exception occurs."""
    mock_post.side_effect = requests.RequestException("Service unreachable")
    response = client.post(
        "/register", data={"username": "newuser", "password": "password123"}
    )

    assert response.status_code == 500
    assert response.json["success"] is False
    assert response.json["message"] == "Error communicating with database service"

### Test login route ###
@patch("app.requests.post")
@patch("app.login_user")
@patch("app.User")
def test_login_success(mock_user, mock_login_user, mock_requests_post, client):
    """Test successful login."""
    mock_requests_post.return_value.status_code = 200
    mock_requests_post.return_value.json.return_value = {
        "_id": "123",
        "username": "testuser"
    }
    mock_user.return_value = MagicMock()
    response = client.post("/login", data={"username": "testuser", "password": "testpassword"})

    assert response.status_code == 200
    assert response.json["message"] == "Login successful!"
    assert response.json["success"] is True
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/auth",
        json={"username": "testuser", "password": "testpassword"}
    )
    mock_login_user.assert_called_once_with(mock_user.return_value)


@patch("app.requests.post")
def test_login_invalid_credentials(mock_requests_post, client):
    """Test login with invalid username or password."""
    mock_requests_post.return_value.status_code = 401
    mock_requests_post.return_value.json.return_value = {}
    response = client.post("/login", data={"username": "wronguser", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json["message"] == "Invalid username or password!"
    assert response.json["success"] is False
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/auth",
        json={"username": "wronguser", "password": "wrongpassword"}
    )


@patch("app.requests.post")
def test_login_internal_error(mock_requests_post, client):
    """Test login when an internal error occurs."""
    mock_requests_post.side_effect = requests.RequestException("Service unavailable")
    response = client.post("/login", data={"username": "testuser", "password": "testpassword"})

    assert response.status_code == 500
    assert response.json["message"] == "Login failed due to internal error!"
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/auth",
        json={"username": "testuser", "password": "testpassword"}
    )

### Test logout route ###
@patch("app.logout_user")
@patch("app.current_user")
def test_logout(mock_current_user, mock_logout_user, client):
    """Test that an authenticated user can log out and is redirected to the login page."""
    with app.app_context():
        mock_current_user.is_authenticated = True
        response = client.get("/logout")

        assert response.status_code == 302
        assert response.location.endswith("/login")
        mock_logout_user.assert_called_once()


@patch("app.current_user")
def test_logout_unauthenticated_user(mock_current_user, client):
    """Test that an unauthenticated user trying to logout is redirected to the login page."""
    mock_current_user.is_authenticated = False
    response = client.get("/logout")

    assert response.status_code == 302
    assert "/login" in response.location


### Test todo route ###
@patch("app.get_todo")
@patch("app.current_user")
def test_todo_route(mock_current_user, mock_get_todo, client):
    """Test tthe todo route"""
    mock_current_user.is_authenticated = True
    mock_current_user.id = 123 
    mock_get_todo.return_value = [
        {"exercise_id": "1", "name": "Push Ups"},
        {"exercise_id": "2", "name": "Squats"},
    ]
    response = client.get("/todo")

    assert response.status_code == 200
    assert b"exercise-btn" in response.data
    mock_get_todo.assert_called_once()

@patch("app.current_user")
def test_todo_route_unauthenticated(mock_current_user, client):
    """Test that an unauthenticated user is redirected to the login page when accessing /todo."""
    mock_current_user.is_authenticated = False
    response = client.get("/todo")

    assert response.status_code == 200

### Test /search route ###
@patch("app.search_exercise")
@patch("app.add_search_history_api")
@patch("app.url_for")
def test_search_post_success(mock_url_for, mock_add_search_history_api, mock_search_exercise, client):
    """Test POST search with successful results."""
    mock_search_exercise.return_value = [
        {"exercise_id": "1", "name": "Push Ups"},
        {"exercise_id": "2", "name": "Sit Ups"}
    ]
    mock_url_for.return_value = "/add"
    with client.session_transaction() as session:
        session["results"] = []
    response = client.post("/search", data={"query": "push"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/add")
    mock_search_exercise.assert_called_once_with("push")
    mock_add_search_history_api.assert_called_once_with("push")
    with client.session_transaction() as session:
        assert session["results"] == mock_search_exercise.return_value

@patch("app.search_exercise")
def test_search_post_empty_query(mock_search_exercise, client):
    """Test POST search with an empty query."""
    response = client.post("/search", data={"query": ""}, follow_redirects=False)
    assert response.status_code == 400
    assert response.json["message"] == "Search content cannot be empty."
    mock_search_exercise.assert_not_called()


@patch("app.search_exercise")
def test_search_post_no_results(mock_search_exercise, client):
    """Test POST search with no matching results."""
    mock_search_exercise.return_value = []
    response = client.post("/search", data={"query": "nonexistent"}, follow_redirects=False)

    assert response.status_code == 404
    assert response.json["message"] == "Exercise was not found."
    mock_search_exercise.assert_called_once_with("nonexistent")


@patch("app.get_search_history")
@patch("app.search_exercise")
@patch("app.render_template")
def test_search_get(mock_render_template, mock_search_exercise, mock_get_search_history, client):
    """Test GET search to display search history and suggestions."""
    mock_get_search_history.return_value = [{"content": "push"}, {"content": "squats"}]
    mock_search_exercise.side_effect = [
        [{"exercise_id": "1", "name": "Push Ups"}],
        [{"exercise_id": "2", "name": "Squats"}],
    ]
    mock_render_template.return_value = "Test Search Page"
    response = client.get("/search", follow_redirects=False)

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test Search Page"
    mock_get_search_history.assert_called_once()
    mock_search_exercise.assert_any_call("push")
    mock_search_exercise.assert_any_call("squats")

    mock_render_template.assert_called_once_with(
        "search.html",
        exercises=[
            {"exercise_id": "1", "name": "Push Ups"},
            {"exercise_id": "2", "name": "Squats"},
        ]
    )


### Test add route ###
@patch("app.render_template")
def test_add_route(mock_render_template, client):
    """Test the add route."""
    with client.session_transaction() as session:
        session["results"] = [
            {"exercise_id": "1", "name": "Push Ups"},
            {"exercise_id": "2", "name": "Squats"},
        ]
    mock_render_template.return_value = "Test Add Page"

    response = client.get("/add")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test Add Page"
    mock_render_template.assert_called_once_with(
        "add.html",
        exercises=session["results"],
        exercises_length=len(session["results"]),
    )


### Test add_exercise route ###
@patch("app.add_todo_api")
def test_add_exercise_success(mock_add_todo_api, client):
    """Test adding an exercise successfully."""
    mock_add_todo_api.return_value = True
    response = client.post("/add_exercise?exercise_id=1&date=2024-12-05")

    assert response.status_code == 200
    assert response.json["message"] == "Added successfully"
    mock_add_todo_api.assert_called_once_with("1", "2024-12-05")


@patch("app.add_todo_api")
def test_add_exercise_missing_exercise_id(mock_add_todo_api, client):
    """Test adding an exercise with a missing exercise_id."""
    response = client.post("/add_exercise?date=2024-12-05")
    assert response.status_code == 400
    assert response.json["message"] == "Exercise ID is required"
    mock_add_todo_api.assert_not_called()


@patch("app.add_todo_api")
def test_add_exercise_missing_date(mock_add_todo_api, client):
    """Test adding an exercise with a missing date."""
    response = client.post("/add_exercise?exercise_id=1")

    assert response.status_code == 400
    assert response.json["message"] == "Date is required"
    mock_add_todo_api.assert_not_called()


@patch("app.add_todo_api")
def test_add_exercise_failure(mock_add_todo_api, client):
    """Test adding an exercise when the API call fails."""
    mock_add_todo_api.return_value = False
    response = client.post("/add_exercise?exercise_id=1&date=2024-12-05")

    assert response.status_code == 400
    assert response.json["message"] == "Failed to add"
    mock_add_todo_api.assert_called_once_with("1", "2024-12-05")

### Test /edit route ###
@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_get_edit_success(mock_current_user, mock_render_template, mock_requests_get, client):
    """Test successful retrieval of exercise details for editing."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "task": "Push Ups",
        "reps": 10,
        "weight": 50
    }

    mock_render_template.return_value = "Test Edit Page"
    response = client.get("/edit?exercise_todo_id=1&date=Thursday, December 04, 2024")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test Edit Page"

    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_exercise_by_id",
        params={
            "user_id": "123",
            "date": "2024-12-04",
            "exercise_todo_id": "1"
        }
    )

    mock_render_template.assert_called_once_with(
        "edit.html",
        exercise_todo_id="1",
        date="2024-12-04",
        exercise={"task": "Push Ups", "reps": 10, "weight": 50},
    )



@patch("app.requests.get")
@patch("app.current_user")
def test_get_edit_missing_param(mock_current_user, mock_requests_get, client):
    """Test editing an exercise with missing parameters."""
    mock_current_user.id = "123"
    response = client.get("/edit?date=Friday, December 05, 2024")

    assert response.status_code == 400
    assert response.json["message"] == "exercise_todo_id and date are required"
    mock_requests_get.assert_not_called()


@patch("app.requests.get")
@patch("app.current_user")
def test_get_edit_exercise_not_found(mock_current_user, mock_requests_get, client):
    """Test editing an exercise that is not found."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 404
    response = client.get("/edit?exercise_todo_id=1&date=Friday, December 05, 2024")

    assert response.status_code == 404
    assert response.json["message"] == "Exercise not found in your To-Do list"
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_exercise_by_id",
        params={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1"
        }
    )


@patch("app.requests.get")
@patch("app.current_user")
def test_get_edit_request_exception(mock_current_user, mock_requests_get, client):
    """Test editing an exercise when an exception occurs during the request."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = requests.RequestException("Service unavailable")
    response = client.get("/edit?exercise_todo_id=1&date=Friday, December 05, 2024")

    assert response.status_code == 404
    assert response.json["message"] == "Exercise not found in your To-Do list"
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_exercise_by_id",
        params={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1"
        }
    )

### Test post edit route ###
@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_success(mock_current_user, mock_requests_post, client):
    """Test successful update of exercise details."""
    mock_current_user.id = "123"
    mock_requests_post.return_value.status_code = 200
    response = client.post(
        "/edit",
        data={
            "exercise_todo_id": "1",
            "date": "2024-12-05",
            "working_time": "20",
            "weight": "50",
            "reps": "10"
        }
    )

    assert response.status_code == 200
    assert response.json["message"] == "Exercise updated successfully"
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/update_exercise",
        json={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1",
            "update_fields": {
                "working_time": "20",
                "weight": "50",
                "reps": "10"
            }
        }
    )

@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_missing_param(mock_current_user, mock_requests_post, client):
    """Test updating an exercise with missing parameters."""
    mock_current_user.id = "123"
    response = client.post(
        "/edit",
        data={
            "date": "2024-12-05",
            "working_time": "20",
            "weight": "50"
        }
    )
    assert response.status_code == 400
    assert response.json["message"] == "exercise_todo_id and date are required"
    mock_requests_post.assert_not_called()


@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_no_fields_to_update(mock_current_user, mock_requests_post, client):
    """Test updating an exercise with no fields provided."""
    mock_current_user.id = "123"
    response = client.post(
        "/edit",
        data={
            "exercise_todo_id": "1",
            "date": "2024-12-05"
        }
    )

    assert response.status_code == 400
    assert response.json["message"] == "No fields to update"
    mock_requests_post.assert_not_called()


@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_api_failure(mock_current_user, mock_requests_post, client):
    """Test updating an exercise when the external API fails."""
    mock_current_user.id = "123"
    mock_requests_post.return_value.status_code = 500

    response = client.post(
        "/edit",
        data={
            "exercise_todo_id": "1",
            "date": "2024-12-05",
            "working_time": "30"
        }
    )
    assert response.status_code == 500
    assert response.json["message"] == "Failed to update exercise"

    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/update_exercise",
        json={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1",
            "update_fields": {
                "working_time": "30"
            }
        }
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_request_exception(mock_current_user, mock_requests_post, client):
    """Test updating an exercise when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_post.side_effect = requests.RequestException("Service unavailable")

    response = client.post(
        "/edit",
        data={
            "exercise_todo_id": "1",
            "date": "2024-12-05",
            "working_time": "30"
        }
    )

    assert response.status_code == 500
    assert response.json["message"] == "An error occurred while updating the exercise"

    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/update_exercise",
        json={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1",
            "update_fields": {
                "working_time": "30"
            }
        }
    )

### Test instructions route ###
@patch("app.get_instruction")
@patch("app.render_template")
def test_instructions_success(mock_render_template, mock_get_instruction, client):
    """Test fetching and displaying exercise instructions successfully."""
    mock_get_instruction.return_value = {
        "workout_name": "Push Ups",
        "instruction": "Keep your back straight and go down slowly."
    }
    mock_render_template.return_value = "Test Instruction Page"
    response = client.get("/instructions?exercise_id=1")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test Instruction Page"
    mock_get_instruction.assert_called_once_with("1")
    mock_render_template.assert_called_once_with(
        "instructions.html",
        exercise={
            "workout_name": "Push Ups",
            "instruction": "Keep your back straight and go down slowly."
        }
    )

@patch("app.get_instruction")
def test_instructions_exercise_not_found(mock_get_instruction, client):
    """Test fetching instructions when the exercise is not found."""
    mock_get_instruction.return_value = {"error": "Exercise not found"}
    response = client.get("/instructions?exercise_id=invalid")

    assert response.status_code == 404
    assert response.json["message"] == "Exercise not found"
    mock_get_instruction.assert_called_once_with("invalid")


### Test upload_audio function ###
def test_upload_audio_no_file(client):
    # pylint: disable=redefined-outer-name
    """Test audio upload with no file."""
    response = client.post("/upload-audio", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.json["error"] == "No audio file uploaded"


@patch("subprocess.run")
def test_upload_audio_success(mock_subprocess, client):
    # pylint: disable=redefined-outer-name
    """Test successful audio upload with mocked transcription."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
    test_audio_path = "/tmp/test_audio.mp3"
    with open(test_audio_path, "wb") as f:
        f.write(b"dummy audio data")

    with open(test_audio_path, "rb") as audio_file:
        data = {"audio": (audio_file, "test_audio.mp3")}
        response = client.post(
            "/upload-audio", data=data, content_type="multipart/form-data"
        )

    assert response.status_code == 200

### Test upload_transcription function ###
@patch("app.insert_transcription_entry_api")
@patch("app.current_user")
def test_upload_transcription_success(
    mock_current_user, mock_insert_transcription_entry_api, client
):
    """Test successful transcription upload."""
    # pylint: disable=redefined-outer-name
    mock_current_user.is_authenticated = True
    mock_current_user.id = "507f1f77bcf86cd799439011"
    mock_insert_transcription_entry_api.return_value = "507f1f77bcf86cd799439012"

    load = {"content": "This is a transcription test."}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data == {
        "message": "Transcription saved successfully!",
        "id": "507f1f77bcf86cd799439012",
    }

def test_upload_transcription_invalid_content_type(client):
    """Test invalid content type."""
    # pylint: disable=redefined-outer-name
    response = client.post(
        "/upload-transcription",
        data="This is not JSON",
        content_type="text/plain",
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid content type. JSON expected"}


def test_upload_transcription_missing_content(client):
    """Test missing transcription content."""
    # pylint: disable=redefined-outer-name
    load = {}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Content is required"}

@patch("app.insert_transcription_entry_api")
@patch("app.current_user")
def test_upload_transcription_save_failure(
    mock_current_user, mock_transcription_entry_api, client
):
    """Test transcription save fail."""
    # pylint: disable=redefined-outer-name
    mock_current_user.is_authenticated = True
    mock_current_user.id = "507f1f77bcf86cd799439011"
    mock_transcription_entry_api.return_value = None
    load = {"content": "This is a transcription test."}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )
    assert response.status_code == 500
    assert response.get_json() == {"error": "Failed to save transcription"}

### Test get_plan function ###
@patch("app.render_template")
def test_get_plan(mock_render_template, client):
    """Test the get_plan route."""
    mock_render_template.return_value = "Test Plan Page"
    response = client.get("/plan")
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test Plan Page"


@patch("app.requests.get")
@patch("app.current_user")
def test_get_week_plan_success(mock_current_user, mock_requests_get, client):
    """Test get_week_plan with successful API call."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = [
        {"date": "2024-12-01", "todo": [{"workout_name": "Push Ups"}, {"workout_name": "Sit Ups"}]},
        {"date": "2024-12-02", "todo": [{"workout_name": "Squats"}]}
    ]
    response = client.get("/plan/week?start_date=2024-12-01&end_date=2024-12-07")
    
    assert response.status_code == 200
    assert response.json == {
        "2024-12-01": ["Push Ups", "Sit Ups"],
        "2024-12-02": ["Squats"]
    }
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-07"}
    )


@patch("app.requests.get")
@patch("app.current_user")
def test_get_week_plan_missing_dates(mock_current_user, mock_requests_get, client):
    """Test get_week_plan with missing start_date and end_date."""
    mock_current_user.id = "123"
    response = client.get("/plan/week?start_date=2024-12-01")

    assert response.status_code == 400
    assert response.json == {"error": "start_date and end_date are required!"}
    mock_requests_get.assert_not_called()


@patch("app.requests.get")
@patch("app.current_user")
def test_get_week_plan_api_failure(mock_current_user, mock_requests_get, client):
    """Test get_week_plan when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 500
    response = client.get("/plan/week?start_date=2024-12-01&end_date=2024-12-07")

    assert response.status_code == 500
    assert response.json == {"error": "Failed to get todo list"}
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-07"}
    )


@patch("app.requests.get")
@patch("app.current_user")
def test_get_week_plan_request_exception(mock_current_user, mock_requests_get, client):
    """Test get_week_plan when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = requests.RequestException("Network error")
    response = client.get("/plan/week?start_date=2024-12-01&end_date=2024-12-07")

    assert response.status_code == 500
    assert response.json == {"error": "An error occurred", "message": "Network error"}
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-07"}
    )

### Test get_month_plan function ###
@patch("app.requests.get")
@patch("app.current_user")
def test_get_month_plan_success(mock_current_user, mock_requests_get, client):
    """Test get_month_plan with successful API call."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = [
        {"date": "2024-12-01", "todo": [{"workout_name": "Push Ups"}]},
        {"date": "2024-12-08", "todo": [{"workout_name": "Rest"}, {"workout_name": "Squats"}]},
    ]
    response = client.get("/plan/month?month=2024-12")

    assert response.status_code == 200
    assert response.json == {
        "2024-12-01": ["Push Ups"],
        "2024-12-08": ["Rest", "Squats"],
        "2024-12-15": [],
        "2024-12-22": [],
        "2024-12-29": []
    }
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-31"}
    )

@patch("app.requests.get")
@patch("app.current_user")
def test_get_month_plan_api_failure(mock_current_user, mock_requests_get, client):
    """Test get_month_plan when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 500
    response = client.get("/plan/month?month=2024-12")

    assert response.status_code == 500
    assert response.json == {"error": "Failed to get todo list"}
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-31"}
    )

@patch("app.requests.get")
@patch("app.current_user")
def test_get_month_plan_missing_month(mock_current_user, mock_requests_get, client):
    """Test get_month_plan with missing month."""
    mock_current_user.id = "123"
    response = client.get("/plan/month")

    assert response.status_code == 400
    assert response.json == {"error": "month is required!"}
    mock_requests_get.assert_not_called()

@patch("app.requests.get")
@patch("app.current_user")
def test_get_month_plan_request_exception(mock_current_user, mock_requests_get, client):
    """Test get_month_plan when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = requests.RequestException("Network error")
    response = client.get("/plan/month?month=2024-12")

    assert response.status_code == 500
    assert response.json == {"error": "An error occurred", "message": "Network error"}
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-31"}
    )

### Test user_profile route ###
@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_user_profile_success(mock_current_user, mock_render_template, mock_requests_get, client):
    """Test fetching a user profile successfully."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {"username": "testuser", "email": "test@example.com"}
    mock_render_template.return_value = "Test User Profile Page"
    response = client.get("/user")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test User Profile Page"
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")
    mock_render_template.assert_called_once_with("user.html", user={"username": "testuser", "email": "test@example.com"})


@patch("app.requests.get")
@patch("app.current_user")
def test_user_profile_not_found(mock_current_user, mock_requests_get, client):
    """Test fetching a user profile that does not exist."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 404

    response = client.get("/user")

    assert response.status_code == 404
    assert response.json == {"error": "User not found"}
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")


### Test /update route ###
@patch("app.requests.put")
@patch("app.current_user")
def test_update_profile_post_success(mock_current_user, mock_requests_put, client):
    """Test updating a profile successfully."""
    mock_current_user.id = "123"
    mock_requests_put.return_value.status_code = 200
    mock_requests_put.return_value.json.return_value = {"success": True}

    response = client.post("/update", json={"username": "newuser", "email": "new@example.com"})

    assert response.status_code == 200
    assert response.json == {"message": "Profile updated successfully."}
    mock_requests_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/123",
        json={"username": "newuser", "email": "new@example.com"}
    )


@patch("app.requests.put")
@patch("app.current_user")
def test_update_profile_post_failure(mock_current_user, mock_requests_put, client):
    """Test updating a profile when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_put.return_value.status_code = 500

    response = client.post("/update", json={"username": "newuser", "email": "new@example.com"})

    assert response.status_code == 500
    assert response.json == {"message": "Failed to update profile."}
    mock_requests_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/123",
        json={"username": "newuser", "email": "new@example.com"}
    )

@patch("app.requests.put")
@patch("app.current_user")
def test_update_profile_post_request_exception(mock_current_user, mock_requests_put, client):
    """Test updating a profile when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_put.side_effect = requests.RequestException("Network error")
    response = client.post("/update", json={"username": "newuser", "email": "new@example.com"})

    assert response.status_code == 500
    assert response.json == {"message": "Error updating profile."}
    mock_requests_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/123",
        json={"username": "newuser", "email": "new@example.com"}
    )


@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_update_profile_get_success(mock_current_user, mock_render_template, mock_requests_get, client):
    """Test the update profile route."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {"username": "testuser", "email": "test@example.com"}
    mock_render_template.return_value = "Mocked Update Profile Page"

    response = client.get("/update")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Mocked Update Profile Page"
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")
    mock_render_template.assert_called_once_with("update.html", user={"username": "testuser", "email": "test@example.com"})


@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_update_profile_get_failure(mock_current_user, mock_render_template, mock_requests_get, client):
    """Test the update profile route when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = requests.RequestException("Network error")
    mock_render_template.return_value = "Mocked Update Profile Page with Error"

    response = client.get("/update")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Mocked Update Profile Page with Error"
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")
    mock_render_template.assert_called_once_with("update.html", user={})

### Test save_profile function ###
@patch("app.update_user_by_id")
@patch("app.current_user")
def test_save_profile_success(mock_current_user, mock_update_user_by_id, client):
    """Test saving a user profile successfully."""
    mock_current_user.id = "123"
    mock_update_user_by_id.return_value = True
    response = client.post(
        "/save-profile",
        json={
            "name": "testuser",
            "sex": "Male",
            "height": 180,
            "weight": 75,
            "goal_weight": 70,
        },
    )
    assert response.status_code == 200
    assert response.json == {
        "message": "User profile updated successfully.",
        "updated_data": {
            "name": "testuser",
            "sex": "Male",
            "height": 180,
            "weight": 75,
            "goal_weight": 70,
        },
    }
    mock_update_user_by_id.assert_called_once_with(
        "123",
        {
            "name": "testuser",
            "sex": "Male",
            "height": 180,
            "weight": 75,
            "goal_weight": 70,
        },
    )

@patch("app.update_user_by_id")
@patch("app.current_user")
def test_save_profile_invalid_input(mock_current_user, mock_update_user_by_id, client):
    """Test saving a user profile with invalid input."""
    mock_current_user.id = "123"
    response = client.post("/save-profile", json=None)

    assert response.status_code == 415
    assert response.json == None
    mock_update_user_by_id.assert_not_called()

@patch("app.update_user_by_id")
@patch("app.current_user")
def test_save_profile_no_valid_fields(mock_current_user, mock_update_user_by_id, client):
    """Test saving a user profile with no valid fields to update."""
    mock_current_user.id = "123"
    response = client.post(
        "/save-profile",
        json={"invalid_field": "value"},
    )
    assert response.status_code == 400
    assert response.json == {"error": "No valid fields to update"}
    mock_update_user_by_id.assert_not_called()

@patch("app.update_user_by_id")
@patch("app.current_user")
def test_save_profile_update_failure(mock_current_user, mock_update_user_by_id, client):
    """Test saving a user profile when the API call fails."""
    mock_current_user.id = "123"
    mock_update_user_by_id.return_value = False
    response = client.post(
        "/save-profile",
        json={
            "name": "testuser",
            "sex": "Male",
        },
    )
    assert response.status_code == 500
    assert response.json == {"error": "Failed to update profile"}
    mock_update_user_by_id.assert_called_once_with(
        "123",
        {"name": "testuser", "sex": "Male"},
    )


'''
### Test edit function ###
@patch("app.get_exercise_in_todo")
def test_edit_get_route(mock_get_exercise_in_todo, client):
    """Test edit get route"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        mock_get_exercise_in_todo.return_value = {
            "exercise_todo_id": "123",
            "name": "Test Exercise",
            "reps": 10,
            "weight": 50,
        }
        # pylint: disable=redefined-outer-name
        response = client.get("/edit?exercise_todo_id=123")
        assert response.status_code == 200
        mock_get_exercise_in_todo.assert_called_once_with("123")


@patch("app.edit_exercise")
@patch("app.get_exercise_in_todo")
def test_edit_route(mock_get_exercise_in_todo, mock_edit_exercise, client):
    """Test edit route"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        mock_get_exercise_in_todo.return_value = {
            "exercise_todo_id": "123",
            "name": "Test Exercise",
            "reps": "10",
            "weight": "50",
        }

        mock_edit_exercise.return_value = True
        # post request successful
        response = client.post(
            "/edit?exercise_todo_id=123",
            data={"working_time": "30", "weight": "70", "reps": "15"},
        )

        assert response.status_code == 200
        assert b"Edited successfully" in response.data
        mock_edit_exercise.assert_called_once_with("123", "30", "70", "15")

        # post request fail
        mock_edit_exercise.reset_mock()
        mock_edit_exercise.return_value = False

        response = client.post(
            "/edit?exercise_todo_id=123",
            data={"working_time": "30", "weight": "70", "reps": "15"},
        )

        assert response.status_code == 400
        assert b"Failed to edit" in response.data
        mock_edit_exercise.assert_called_once_with("123", "30", "70", "15")


@patch("app.edit_transcription_collection")
def test_insert_transcription_entry(mock_edit_transcription_collection):
    """Test insert_transcription_entry function"""
    mock_result = MagicMock()
    mock_result.inserted_id = "mock_id"
    mock_edit_transcription_collection.insert_one.return_value = mock_result

    user_id = "test_user"
    content = "Test transcription content"
    inserted_id = insert_transcription_entry(user_id, content)

    assert inserted_id == "mock_id"

    mock_edit_transcription_collection.insert_one.assert_called_once()
    call_args = mock_edit_transcription_collection.insert_one.call_args[0][0]
    assert call_args["user_id"] == user_id
    assert call_args["content"] == content
    assert isinstance(call_args["time"], datetime)

    mock_edit_transcription_collection.insert_one.return_value.inserted_id = None
    failed_inserted_id = insert_transcription_entry(user_id, content)
    assert failed_inserted_id is None


### Test search function ###
@patch("app.search_exercise")
@patch("app.add_search_history")
@patch("app.get_matching_exercises_from_history")
def test_search_route(mock_get_history, mock_add_history, mock_search_exercise, client):
    """Test search route"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        mock_get_history.return_value = [
            {"_id": "1", "name": "Push Up"},
            {"_id": "2", "name": "Squats"},
        ]
        response = client.get("/search")

        # valid check
        mock_search_exercise.return_value = [{"_id": "1", "name": "Push Up"}]
        response = client.post("/search", data={"query": "push"})

        # redirect check
        assert response.status_code == 302
        mock_search_exercise.assert_called_once_with("push")
        mock_add_history.assert_called_once_with("push")

        # empty search query
        response = client.post("/search", data={"query": ""})
        assert response.status_code == 400
        assert b"Search content cannot be empty." in response.data

        # non-existent search query
        mock_search_exercise.reset_mock()
        mock_search_exercise.return_value = []
        # pylint: disable=redefined-outer-name
        response = client.post("/search", data={"query": "nonexistent"})

        # fail search
        assert response.status_code == 404
        assert b"Exercise was not found." in response.data
        mock_search_exercise.assert_called_once_with("nonexistent")


### Test add function ###
@patch("app.add_todo")
def test_add_exercise_route(mock_add_todo, client):
    """Test add exercise route"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        # add successful
        mock_add_todo.return_value = True
        response = client.post("/add_exercise?exercise_id=123")
        assert response.status_code == 200
        assert b"Added successfully" in response.data
        mock_add_todo.assert_called_once_with("123")

        # miss exercise id to add
        mock_add_todo.reset_mock()
        # pylint: disable=redefined-outer-name
        response = client.post("/add_exercise")
        assert response.status_code == 400
        assert b"Exercise ID is required" in response.data
        mock_add_todo.assert_not_called()

        # add exercise fail
        mock_add_todo.reset_mock()
        mock_add_todo.return_value = False
        # pylint: disable=redefined-outer-name
        response = client.post("/add_exercise?exercise_id=456")

        # add exercise fail
        assert response.status_code == 400
        assert b"Failed to add" in response.data
        mock_add_todo.assert_called_once_with("456")


def test_add_route_with_results_in_session(client):
    """Test add route with results"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        with client.session_transaction() as session:
            session["results"] = [
                {"_id": "1", "name": "Push Up"},
                {"_id": "2", "name": "Squats"},
            ]
        response = client.get("/add")
        assert response.status_code == 200
        assert b"exercise_id=1" in response.data
        assert b"exercise_id=2" in response.data
        assert b"const exercisesLength = 2" in response.data


def test_add_route_empty_session(client):
    """Test add route with empty session"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        with client.session_transaction() as session:
            session.pop("results", None)
        response = client.get("/add")

        assert response.status_code == 200
        assert b"const exercisesLength = 0" in response.data


### Test delete route ###
@patch("app.get_todo")
def test_delete_exercise_route(mock_get_todo, client):
    """Test delete exercise route"""
    # pylint: disable=redefined-outer-name
    with app.app_context():
        mock_get_todo.return_value = [
            {"_id": "1", "name": "Push Up"},
            {"_id": "2", "name": "Squats"},
        ]
        response = client.get("/delete_exercise")
        assert response.status_code == 200
        assert b"exercise-" in response.data
        mock_get_todo.assert_called_once()


### Test delete exercise id function ###
@patch("app.delete_todo")
def test_delete_exercise_id_success(mock_delete_todo, client):
    """Test delete exercise id"""
    # pylint: disable=redefined-outer-name
    mock_delete_todo.return_value = True

    response = client.delete("/delete_exercise/123")

    assert response.status_code == 204
    assert response.data == b""
    mock_delete_todo.assert_called_once_with(123)


@patch("app.delete_todo")
def test_delete_exercise_id_failure(mock_delete_todo, client):
    """Test delete exercise id fail"""
    # pylint: disable=redefined-outer-name
    mock_delete_todo.return_value = False

    response = client.delete("/delete_exercise/456")
    assert response.status_code == 404
    assert b"Failed to delete" in response.data
    mock_delete_todo.assert_called_once_with(456)


### Test search_exercise function ###
@patch("app.exercises_collection")
@patch("app.normalize_text")
def test_search_exercise(mock_normalize_text, mock_exercises_collection):
    """Test search exercise."""
    mock_normalize_text.return_value = "up"
    mock_exercises_collection.find.return_value = [
        {"workout_name": "Push Up"},
        {"workout_name": "Pull Up"},
        {"workout_name": "Sit Up"},
    ]

    query = "Up"
    result = search_exercise(query)

    assert result == [
        {"workout_name": "Push Up"},
        {"workout_name": "Pull Up"},
        {"workout_name": "Sit Up"},
    ]

    mock_normalize_text.assert_called_once_with(query)
    # pylint: disable=R0801
    mock_exercises_collection.find.assert_called_once_with(
        {
            "$expr": {
                "$regexMatch": {
                    "input": {
                        "$replaceAll": {
                            "input": {
                                "$replaceAll": {
                                    "input": "$workout_name",
                                    "find": "-",
                                    "replacement": "",
                                }
                            },
                            "find": " ",
                            "replacement": "",
                        }
                    },
                    "regex": "up",
                    "options": "i",
                }
            }
        }
    )


### Test search_exercise_rigid function ###
@patch("app.exercises_collection")
@patch("app.normalize_text")
def test_search_exercise_rigid(mock_normalize_text, mock_exercises_collection):
    """Test search exercise rigid."""
    mock_normalize_text.return_value = "pushup"
    mock_exercises_collection.find.return_value = [
        {"workout_name": "Push Up"},
        {"workout_name": "PUSH-UP"},
        {"workout_name": "pushup"},
    ]

    result = search_exercise_rigid("Push Up")
    assert result == [
        {"workout_name": "Push Up"},
        {"workout_name": "PUSH-UP"},
        {"workout_name": "pushup"},
    ]

    mock_normalize_text.assert_called_once_with("Push Up")
    # pylint: disable=R0801
    mock_exercises_collection.find.assert_called_once_with(
        {
            "$expr": {
                "$eq": [
                    {
                        "$toLower": {
                            "$replaceAll": {
                                "input": {
                                    "$replaceAll": {
                                        "input": "$workout_name",
                                        "find": "-",
                                        "replacement": "",
                                    }
                                },
                                "find": " ",
                                "replacement": "",
                            }
                        }
                    },
                    "pushup",
                ]
            }
        }
    )


### Test get_exercise function ###
@patch("app.exercises_collection")
def test_get_exercise(mock_exercises_collection):
    """Test get exercise"""
    random_object_id = ObjectId()
    mock_exercise = {"_id": random_object_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_object_id)
    result = get_exercise(exercise_id)

    assert result == mock_exercise
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}
    )


### Test get_todo function ###
@patch("app.current_user")
@patch("app.todo_collection")
def test_get_todo_with_todo_list(mock_todo_collection, mock_current_user):
    """Test get todo from the todo list"""
    mock_current_user.id = "user123"

    mock_todo_list = {"user_id": "user123", "todo": ["task1", "task2", "task3"]}
    mock_todo_collection.find_one.return_value = mock_todo_list

    result = get_todo()

    assert result == ["task1", "task2", "task3"]
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_todo_without_todo_list(mock_todo_collection, mock_current_user):
    """Test get todo without todo list"""
    mock_current_user.id = "user123"
    mock_todo_collection.find_one.return_value = None
    result = get_todo()
    assert result == []
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_todo_with_empty_todo_list(mock_todo_collection, mock_current_user):
    """Test get todo with empty todo list"""
    mock_current_user.id = "user123"

    mock_todo_list = {"user_id": "user123"}
    mock_todo_collection.find_one.return_value = mock_todo_list

    result = get_todo()

    assert result == []
    mock_todo_collection.find_one.assert_called_once_with({"user_id": "user123"})


### Test delete_todo function ###
@patch("app.current_user")
@patch("app.todo_collection")
def test_delete_todo_success(mock_todo_collection, mock_current_user):
    """Test delete todo successful"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.modified_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = ObjectId()
    result = delete_todo(exercise_todo_id)

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}},
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_delete_todo_failure(mock_todo_collection, mock_current_user):
    """Test delete todo fail"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.modified_count = 0
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = ObjectId()
    result = delete_todo(exercise_todo_id)

    assert result is False
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}},
    )


### Test add_todo function ###
@patch("app.current_user")
@patch("app.exercises_collection")
@patch("app.todo_collection")
def test_add_todo_success(
    mock_todo_collection, mock_exercises_collection, mock_current_user
):
    """Test add todo successful"""
    mock_current_user.id = "user123"

    random_object_id = ObjectId()
    mock_exercise = {"_id": random_object_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    mock_todo = {"user_id": "user123", "todo": [{"exercise_todo_id": 1000}]}
    mock_todo_collection.find_one.return_value = mock_todo

    mock_result = MagicMock()
    mock_result.modified_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    result = add_todo(str(random_object_id))

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": "user123"},
        {
            "$push": {
                "todo": {
                    "exercise_todo_id": 1001,
                    "exercise_id": mock_exercise["_id"],
                    "workout_name": mock_exercise["workout_name"],
                    "working_time": None,
                    "reps": None,
                    "weight": None,
                }
            }
        },
    )


@patch("app.current_user")
@patch("app.exercises_collection")
@patch("app.todo_collection")
def test_add_todo_failure(
    mock_todo_collection, mock_exercises_collection, mock_current_user
):
    """Test add todo fail"""
    mock_current_user.id = "user123"

    mock_exercises_collection.find_one.return_value = None

    random_object_id = ObjectId()
    result = add_todo(str(random_object_id))

    assert result is False
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": random_object_id}
    )
    mock_todo_collection.update_one.assert_not_called()
    mock_todo_collection.insert_one.assert_not_called()


@patch("app.current_user")
@patch("app.todo_collection")
def test_edit_exercise_success(mock_todo_collection, mock_current_user):
    """Test edit exercise successful"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.matched_count = 1
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = 1001
    working_time = 30
    weight = 50
    reps = 10
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is True
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": "user123", "todo.exercise_todo_id": exercise_todo_id},
        {
            "$set": {
                "todo.$.working_time": working_time,
                "todo.$.weight": weight,
                "todo.$.reps": reps,
            }
        },
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_edit_exercise_no_fields_to_update(mock_todo_collection, mock_current_user):
    """Test edit exercise with no update"""
    mock_current_user.id = "user123"

    exercise_todo_id = 1001
    working_time = None
    weight = None
    reps = None
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is False
    mock_todo_collection.update_one.assert_not_called()


@patch("app.current_user")
@patch("app.todo_collection")
def test_edit_exercise_not_found(mock_todo_collection, mock_current_user):
    """Test edit exercise with no result found"""
    mock_current_user.id = "user123"

    mock_result = MagicMock()
    mock_result.matched_count = 0
    mock_todo_collection.update_one.return_value = mock_result

    exercise_todo_id = 1001
    working_time = 20
    weight = 60
    reps = 5
    result = edit_exercise(exercise_todo_id, working_time, weight, reps)

    assert result is False
    mock_todo_collection.update_one.assert_called_once_with(
        {"user_id": mock_current_user.id, "todo.exercise_todo_id": exercise_todo_id},
        {
            "$set": {
                "todo.$.working_time": working_time,
                "todo.$.weight": weight,
                "todo.$.reps": reps,
            }
        },
    )


### Test get_exercise_in_todo function ###
@patch("app.current_user")
@patch("app.todo_collection")
def test_get_exercise_in_todo_found(mock_todo_collection, mock_current_user):
    """Test get exercise in todo"""
    mock_current_user.id = "user123"

    random_exercise_id_1 = ObjectId()
    random_exercise_id_2 = ObjectId()

    mock_todo_item = {
        "user_id": "user123",
        "todo": [
            {
                "exercise_todo_id": 1001,
                "exercise_id": random_exercise_id_1,
                "workout_name": "Push Up",
            },
            {
                "exercise_todo_id": 1002,
                "exercise_id": random_exercise_id_2,
                "workout_name": "Pull Up",
            },
        ],
    }
    mock_todo_collection.find_one.return_value = mock_todo_item

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result == {
        "exercise_todo_id": 1001,
        "exercise_id": random_exercise_id_1,
        "workout_name": "Push Up",
    }
    mock_todo_collection.find_one.assert_called_once_with(
        {"user_id": mock_current_user.id}
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_exercise_in_todo_not_found(mock_todo_collection, mock_current_user):
    """Test get exercise in todo with no results found"""
    mock_current_user.id = "user123"

    random_exercise_id_1 = ObjectId()
    mock_todo_item = {
        "user_id": "user123",
        "todo": [
            {
                "exercise_todo_id": 1002,
                "exercise_id": random_exercise_id_1,
                "workout_name": "Pull Up",
            }
        ],
    }
    mock_todo_collection.find_one.return_value = mock_todo_item

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result is None
    mock_todo_collection.find_one.assert_called_once_with(
        {"user_id": mock_current_user.id}
    )


@patch("app.current_user")
@patch("app.todo_collection")
def test_get_exercise_in_todo_no_todo_item(mock_todo_collection, mock_current_user):
    """Test get exercise in todo with no todo item"""
    mock_current_user.id = "user123"

    mock_todo_collection.find_one.return_value = None

    exercise_todo_id = 1001
    result = get_exercise_in_todo(exercise_todo_id)

    assert result is None
    mock_todo_collection.find_one.assert_called_once_with(
        {"user_id": mock_current_user.id}
    )


### Test get_instruction function ###
@patch("app.exercises_collection")
def test_get_instruction_with_instruction(mock_exercises_collection):
    """Test get instructions with instruction"""
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")
    mock_exercise = {
        "_id": random_exercise_id,
        "workout_name": "Push Up",
        "instruction": "Slowly lower your body to the ground, then push back up.",
    }
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "workout_name": "Push Up",
        "instruction": "Slowly lower your body to the ground, then push back up.",
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )


@patch("app.exercises_collection")
def test_get_instruction_without_instruction(mock_exercises_collection):
    """Test get instruction without instruction"""
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")
    mock_exercise = {"_id": random_exercise_id, "workout_name": "Push Up"}
    mock_exercises_collection.find_one.return_value = mock_exercise

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {
        "workout_name": "Push Up",
        "instruction": "No instructions for this exercise.",
    }
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )


@patch("app.exercises_collection")
def test_get_instruction_not_found(mock_exercises_collection):
    """Test get instruction with no result found"""
    mock_exercises_collection.find_one.return_value = None
    random_exercise_id = ObjectId("507f1f77bcf86cd799439011")

    exercise_id = str(random_exercise_id)
    result = get_instruction(exercise_id)

    assert result == {"error": f"Exercise with ID {exercise_id} not found."}
    mock_exercises_collection.find_one.assert_called_once_with(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )


### Test get_matching_exercises_from_history function ###
@patch("app.get_search_history")
@patch("app.search_exercise_rigid")
def test_get_matching_exercises_from_history_empty_history(
    mock_search_exercise_rigid, mock_get_search_history
):
    """Test get matching exercise from history"""
    mock_get_search_history.return_value = []
    result = get_matching_exercises_from_history()
    assert not result, "Expected an empty list when search history is empty"
    mock_search_exercise_rigid.assert_not_called()  # search_exercise_rigid should not be called


@patch(
    "app.get_search_history",
)
@patch("app.search_exercise_rigid")
def test_get_matching_exercises_from_history_with_matches(
    mock_search_exercise_rigid, mock_get_search_history
):
    """Test get matching exercise from history"""
    mock_get_search_history.return_value = [
        {"content": "exercise1"},
        {"content": "exercise2"},
    ]
    # search_exercise_rigid to return specific results for each content name
    mock_search_exercise_rigid.side_effect = lambda name: [{"name": f"matching_{name}"}]
    result = get_matching_exercises_from_history()

    expected_result = [{"name": "matching_exercise1"}, {"name": "matching_exercise2"}]
    assert (
        result == expected_result
    ), "Expected list of matching exercises based on search history content"
    mock_search_exercise_rigid.assert_any_call("exercise1")
    mock_search_exercise_rigid.assert_any_call("exercise2")


@patch("app.get_search_history")
@patch("app.search_exercise_rigid")
def test_get_matching_exercises_from_history_with_partial_matches(
    mock_search_exercise_rigid, mock_get_search_history
):
    """Test get matching exercise from history with partial match"""
    mock_get_search_history.return_value = [
        {"content": "exercise1"},
        {"content": "exercise2"},
    ]
    # Mock search_exercise_rigid to return an empty list
    mock_search_exercise_rigid.side_effect = lambda name: (
        [{"name": "matching_exercise1"}] if name == "exercise1" else []
    )
    result = get_matching_exercises_from_history()

    expected_result = [{"name": "matching_exercise1"}]
    assert (
        result == expected_result
    ), "Expected list with only matching exercises where results were found"
    mock_search_exercise_rigid.assert_any_call("exercise1")
    mock_search_exercise_rigid.assert_any_call("exercise2")





### Test login page function ###
def test_login_page(client):
    """Test login page"""
    # pylint: disable=redefined-outer-name
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


# sign up page
def test_signup_page(client):
    """Test signup page"""
    # pylint: disable=redefined-outer-name
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Sign Up" in response.data


### Test login function ###
@patch("app.users_collection.find_one")
@patch("app.check_password_hash")
@patch("app.login_user")
def test_login_success(
    mock_login_user, mock_check_password_hash, mock_find_one, client
):
    """Test login successful"""
    # pylint: disable=redefined-outer-name
    mock_find_one.return_value = {
        "_id": "mock_user_id",
        "username": "testuser",
        "password": "hashed_password",
    }
    mock_check_password_hash.return_value = True
    response = client.post(
        "/login", data={"username": "testuser", "password": "testpassword"}
    )

    assert response.status_code == 200
    assert response.json == {"message": "Login successful!", "success": True}
    mock_login_user.assert_called_once()


# Invalid username
@patch("app.users_collection.find_one")
def test_login_invalid_username(mock_find_one, client):
    """Test login with invalid username"""
    # pylint: disable=redefined-outer-name
    # user not found in the database
    mock_find_one.return_value = None
    response = client.post(
        "/login", data={"username": "unknownuser", "password": "testpassword"}
    )

    assert response.status_code == 401
    assert response.json == {
        "message": "Invalid username or password!",
        "success": False,
    }


# Invalid password
@patch("app.users_collection.find_one")
@patch("app.check_password_hash")
def test_login_invalid_password(mock_check_password_hash, mock_find_one, client):
    """Test login with invalid password"""
    # pylint: disable=redefined-outer-name
    mock_find_one.return_value = {
        "_id": "mock_user_id",
        "username": "testuser",
        "password": "hashed_password",
    }
    mock_check_password_hash.return_value = False

    response = client.post(
        "/login", data={"username": "testuser", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert response.json == {
        "message": "Invalid username or password!",
        "success": False,
    }


@patch("app.current_user")
@patch("app.search_history_collection")
def test_add_search_history(mock_search_history_collection, mock_current_user):
    """Test adding search history."""
    mock_current_user.id = "user123"

    content = "Test Search Content"
    add_search_history(content)
    mock_search_history_collection.insert_one.assert_called_once()

    inserted_entry = mock_search_history_collection.insert_one.call_args[0][0]

    assert inserted_entry["user_id"] == "user123"
    assert inserted_entry["content"] == content
    assert isinstance(inserted_entry["time"], datetime)


@patch("app.current_user")
@patch("app.search_history_collection")
def test_get_search_history(mock_search_history_collection, mock_current_user):
    """Test getting search history"""
    mock_current_user.id = "user123"
    mock_results = [
        {
            "user_id": "user123",
            "content": "Test Content 1",
            "time": datetime(2024, 11, 12, 12, 0, 0),
        },
        {
            "user_id": "user123",
            "content": "Test Content 2",
            "time": datetime(2024, 11, 12, 11, 0, 0),
        },
    ]
    mock_search_history_collection.find.return_value.sort.return_value = mock_results

    history = get_search_history()

    assert len(history) == 2
    assert history[0]["content"] == "Test Content 1"
    assert history[1]["content"] == "Test Content 2"
    mock_search_history_collection.find.assert_called_once_with(
        {"user_id": "user123"}, {"_id": 0, "user_id": 1, "content": 1, "time": 1}
    )


@patch("app.get_exercise")
def test_instructions_route(mock_get_exercise, client):
    # pylint: disable=redefined-outer-name
    """Test instruction route."""
    mock_exercise = {
        "_id": "exercise123",
        "workout_name": "Push Up",
        "description": "A great upper body workout.",
        "instruction": "Make sure to keep your back straight while performing this exercise.",
    }
    mock_get_exercise.return_value = mock_exercise

    response = client.get("/instructions?exercise_id=exercise123")

    assert response.status_code == 200

    assert b"A great upper body workout." in response.data
    assert (
        b"Make sure to keep your back straight while performing this exercise."
        in response.data
    )


### Test upload_audio function ###
@patch("app.call_speech_to_text_service")
def test_upload_audio_conversion_error(mock_transcribe, client):
    # pylint: disable=redefined-outer-name
    """Test audio upload with conversion error."""
    mock_transcribe.return_value = "Mocked transcription"
    dummy_audio_path = "/tmp/test_audio.mp3"
    with open(dummy_audio_path, "wb") as f:
        f.write(b"dummy audio data")

    with open(dummy_audio_path, "rb") as audio_file:
        data = {"audio": (audio_file, "test_audio.mp3")}
        response = client.post(
            "/upload-audio", data=data, content_type="multipart/form-data"
        )

    assert response.status_code == 500


def test_upload_audio_no_file(client):
    # pylint: disable=redefined-outer-name
    """Test audio upload with no file."""
    response = client.post("/upload-audio", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.json["error"] == "No audio file uploaded"


@patch("subprocess.run")
def test_upload_audio_success(mock_subprocess, client):
    # pylint: disable=redefined-outer-name
    """Test successful audio upload with mocked transcription."""
    mock_subprocess.run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
    test_audio_path = "/tmp/test_audio.mp3"
    with open(test_audio_path, "wb") as f:
        f.write(b"dummy audio data")

    with open(test_audio_path, "rb") as audio_file:
        data = {"audio": (audio_file, "test_audio.mp3")}
        response = client.post(
            "/upload-audio", data=data, content_type="multipart/form-data"
        )

    assert response.status_code == 200


def test_upload_audio_transcription_error(client):
    # pylint: disable=redefined-outer-name
    """Test when transcription fails."""
    dummy_audio_path = "/tmp/test_audio.mp3"
    with open(dummy_audio_path, "wb") as f:
        f.write(b"dummy audio data")

    with open(dummy_audio_path, "rb") as audio_file:
        data = {"audio": (audio_file, "test_audio.mp3")}
        response = client.post(
            "/upload-audio", data=data, content_type="multipart/form-data"
        )

    assert response.status_code == 500, "Expected server error for failed transcription"





### Test upload_transcription function ###
@patch("app.insert_transcription_entry")
@patch("app.current_user")
def test_upload_transcription_success(
    mock_current_user, mock_insert_transcription_entry, client
):
    """Test successful transcription upload."""
    # pylint: disable=redefined-outer-name
    mock_current_user.is_authenticated = True
    mock_current_user.id = "507f1f77bcf86cd799439011"
    mock_insert_transcription_entry.return_value = "507f1f77bcf86cd799439012"

    load = {"content": "This is a transcription test."}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data == {
        "message": "Transcription saved successfully!",
        "id": "507f1f77bcf86cd799439012",
    }
    mock_insert_transcription_entry.assert_called_once_with(
        "507f1f77bcf86cd799439011", "This is a transcription test."
    )


def test_upload_transcription_invalid_content_type(client):
    """Test invalid content type."""
    # pylint: disable=redefined-outer-name
    response = client.post(
        "/upload-transcription",
        data="This is not JSON",
        content_type="text/plain",
    )
    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid content type. JSON expected"}


def test_upload_transcription_missing_content(client):
    """Test missing transcription content."""
    # pylint: disable=redefined-outer-name
    load = {}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Content is required"}


@patch("app.current_user")
def test_upload_transcription_unauthenticated(mock_current_user, client):
    """Test unauthenticated user attempting to save transcription."""
    # pylint: disable=redefined-outer-name
    mock_current_user.is_authenticated = False
    load = {"content": "This is a transcription test."}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.get_json() == {
        "error": "User must be logged in to save transcription"
    }


@patch("app.insert_transcription_entry")
@patch("app.current_user")
def test_upload_transcription_save_failure(
    mock_current_user, mock_transcription_entry, client
):
    """Test transcription save fail."""
    # pylint: disable=redefined-outer-name
    mock_current_user.is_authenticated = True
    mock_current_user.id = "507f1f77bcf86cd799439011"
    mock_transcription_entry.return_value = None
    load = {"content": "This is a transcription test."}
    response = client.post(
        "/upload-transcription",
        data=json.dumps(load),
        content_type="application/json",
    )
    assert response.status_code == 500
    assert response.get_json() == {"error": "Failed to save transcription"}
'''

if __name__ == "__main__":
    pytest.main()
