"""Test code for web-app"""

# pylint: disable=C0302
# pylint: disable=redefined-outer-name
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import ANY, patch, MagicMock
import subprocess
import json
import re
import pytest
from flask import make_response
import requests
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
    add_plan,
    get_workout_data,
    save_plan,
    delete_todo_by_date,
    delete_exercise_by_date,
)


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
        f"{DB_SERVICE_URL}/users/update/1", json=update_fields
    )


@patch("requests.put")
def test_update_user_by_id_failure(mock_put):
    """Test update_user_by_id function when update fails."""
    mock_put.return_value.status_code = 400

    update_fields = {"name": "testuser"}
    result = update_user_by_id(2, update_fields)

    assert result is False
    mock_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/2", json=update_fields
    )


@patch("requests.put")
def test_update_user_by_id_exception(mock_put):
    """Test update_user_by_id function when exception occurs."""
    mock_put.side_effect = requests.RequestException("Connection error")
    update_field = {"name": "testuser"}

    result = update_user_by_id(3, update_field)

    assert result is False
    mock_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/3", json=update_field
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
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/exercises/search", json={"query": query}
    )


@patch("requests.post")
def test_search_exercise_no_results(mock_post):
    """Test search_exercise function with no results found."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = []

    query = "Nonexistent Exercise"
    results = search_exercise(query)
    assert results == []
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/exercises/search", json={"query": query}
    )


@patch("requests.post")
def test_search_exercise_api_failure(mock_post):
    """Test search_exercise function when the API fails."""
    mock_post.return_value.status_code = 500

    query = "Push"
    results = search_exercise(query)

    assert results == []
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/exercises/search", json={"query": query}
    )


@patch("requests.post")
def test_search_exercise_request_exception(mock_post):
    """Test search_exercise function when a RequestException is raised."""
    mock_post.side_effect = requests.RequestException("API is unavailable")
    query = "Push Up"
    results = search_exercise(query)

    assert results == []
    mock_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/exercises/search", json={"query": query}
    )


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
        "todo": [{"id": 1, "time": "2024-12-01", "task": "Squat"}]
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
    assert not today_todo
    mock_requests.assert_called_once_with(f"{DB_SERVICE_URL}/todo/get/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_get_today_todo_empty_response(mock_current_user, mock_requests):
    """Test get_today_todo function with an empty response."""
    mock_current_user.id = 123
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {}

    today_todo = get_today_todo()
    assert not today_todo
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
def test_add_todo_api_request_exception(
    mock_get_exercise, mock_current_user, mock_post
):
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
    response = client.post(
        "/register", data={"username": "", "password": "password123"}
    )
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
        "username": "testuser",
    }
    mock_user.return_value = MagicMock()
    response = client.post(
        "/login", data={"username": "testuser", "password": "testpassword"}
    )

    assert response.status_code == 200
    assert response.json["message"] == "Login successful!"
    assert response.json["success"] is True
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/auth",
        json={"username": "testuser", "password": "testpassword"},
    )
    mock_login_user.assert_called_once_with(mock_user.return_value)


@patch("app.requests.post")
def test_login_invalid_credentials(mock_requests_post, client):
    """Test login with invalid username or password."""
    mock_requests_post.return_value.status_code = 401
    mock_requests_post.return_value.json.return_value = {}
    response = client.post(
        "/login", data={"username": "wronguser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json["message"] == "Invalid username or password!"
    assert response.json["success"] is False
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/auth",
        json={"username": "wronguser", "password": "wrongpassword"},
    )


@patch("app.requests.post")
def test_login_internal_error(mock_requests_post, client):
    """Test login when an internal error occurs."""
    mock_requests_post.side_effect = requests.RequestException("Service unavailable")
    response = client.post(
        "/login", data={"username": "testuser", "password": "testpassword"}
    )

    assert response.status_code == 500
    assert response.json["message"] == "Login failed due to internal error!"
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/auth",
        json={"username": "testuser", "password": "testpassword"},
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
def test_search_post_success(
    mock_url_for, mock_add_search_history_api, mock_search_exercise, client
):
    """Test POST search with successful results."""
    mock_search_exercise.return_value = [
        {"exercise_id": "1", "name": "Push Ups"},
        {"exercise_id": "2", "name": "Sit Ups"},
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
    response = client.post(
        "/search", data={"query": "nonexistent"}, follow_redirects=False
    )

    assert response.status_code == 404
    assert response.json["message"] == "Exercise was not found."
    mock_search_exercise.assert_called_once_with("nonexistent")


@patch("app.get_search_history")
@patch("app.search_exercise")
@patch("app.render_template")
def test_search_get(
    mock_render_template, mock_search_exercise, mock_get_search_history, client
):
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
        ],
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
def test_get_edit_success(
    mock_current_user, mock_render_template, mock_requests_get, client
):
    """Test successful retrieval of exercise details for editing."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "task": "Push Ups",
        "reps": 10,
        "weight": 50,
    }

    mock_render_template.return_value = "Test Edit Page"
    response = client.get("/edit?exercise_todo_id=1&date=Thursday, December 04, 2024")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test Edit Page"

    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_exercise_by_id",
        params={"user_id": "123", "date": "2024-12-04", "exercise_todo_id": "1"},
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
        params={"user_id": "123", "date": "2024-12-05", "exercise_todo_id": "1"},
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
        params={"user_id": "123", "date": "2024-12-05", "exercise_todo_id": "1"},
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
            "reps": "10",
        },
    )

    assert response.status_code == 200
    assert response.json["message"] == "Exercise updated successfully"
    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/update_exercise",
        json={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1",
            "update_fields": {"working_time": "20", "weight": "50", "reps": "10"},
        },
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_missing_param(mock_current_user, mock_requests_post, client):
    """Test updating an exercise with missing parameters."""
    mock_current_user.id = "123"
    response = client.post(
        "/edit", data={"date": "2024-12-05", "working_time": "20", "weight": "50"}
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
        "/edit", data={"exercise_todo_id": "1", "date": "2024-12-05"}
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
        data={"exercise_todo_id": "1", "date": "2024-12-05", "working_time": "30"},
    )
    assert response.status_code == 500
    assert response.json["message"] == "Failed to update exercise"

    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/update_exercise",
        json={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1",
            "update_fields": {"working_time": "30"},
        },
    )


@patch("app.requests.post")
@patch("app.current_user")
def test_post_edit_request_exception(mock_current_user, mock_requests_post, client):
    """Test updating an exercise when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_post.side_effect = requests.RequestException("Service unavailable")

    response = client.post(
        "/edit",
        data={"exercise_todo_id": "1", "date": "2024-12-05", "working_time": "30"},
    )

    assert response.status_code == 500
    assert response.json["message"] == "An error occurred while updating the exercise"

    mock_requests_post.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/update_exercise",
        json={
            "user_id": "123",
            "date": "2024-12-05",
            "exercise_todo_id": "1",
            "update_fields": {"working_time": "30"},
        },
    )


### Test instructions route ###
@patch("app.get_instruction")
@patch("app.render_template")
def test_instructions_success(mock_render_template, mock_get_instruction, client):
    """Test fetching and displaying exercise instructions successfully."""
    mock_get_instruction.return_value = {
        "workout_name": "Push Ups",
        "instruction": "Keep your back straight and go down slowly.",
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
            "instruction": "Keep your back straight and go down slowly.",
        },
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
        {
            "date": "2024-12-01",
            "todo": [{"workout_name": "Push Ups"}, {"workout_name": "Sit Ups"}],
        },
        {"date": "2024-12-02", "todo": [{"workout_name": "Squats"}]},
    ]
    response = client.get("/plan/week?start_date=2024-12-01&end_date=2024-12-07")

    assert response.status_code == 200
    assert response.json == {
        "2024-12-01": ["Push Ups", "Sit Ups"],
        "2024-12-02": ["Squats"],
    }
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-07"},
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
        params={"start_date": "2024-12-01", "end_date": "2024-12-07"},
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
        params={"start_date": "2024-12-01", "end_date": "2024-12-07"},
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
        {
            "date": "2024-12-08",
            "todo": [{"workout_name": "Rest"}, {"workout_name": "Squats"}],
        },
    ]
    response = client.get("/plan/month?month=2024-12")

    assert response.status_code == 200
    assert response.json == {
        "2024-12-01": ["Push Ups"],
        "2024-12-08": ["Rest", "Squats"],
        "2024-12-15": [],
        "2024-12-22": [],
        "2024-12-29": [],
    }
    mock_requests_get.assert_called_once_with(
        f"{DB_SERVICE_URL}/todo/get_by_date/123",
        params={"start_date": "2024-12-01", "end_date": "2024-12-31"},
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
        params={"start_date": "2024-12-01", "end_date": "2024-12-31"},
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
        params={"start_date": "2024-12-01", "end_date": "2024-12-31"},
    )


### Test user_profile route ###
@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_user_profile_success(
    mock_current_user, mock_render_template, mock_requests_get, client
):
    """Test fetching a user profile successfully."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "username": "testuser",
        "email": "test@example.com",
    }
    mock_render_template.return_value = "Test User Profile Page"
    response = client.get("/user")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Test User Profile Page"
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")
    mock_render_template.assert_called_once_with(
        "user.html", user={"username": "testuser", "email": "test@example.com"}
    )


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

    response = client.post(
        "/update", json={"username": "newuser", "email": "new@example.com"}
    )

    assert response.status_code == 200
    assert response.json == {"message": "Profile updated successfully."}
    mock_requests_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/123",
        json={"username": "newuser", "email": "new@example.com"},
    )


@patch("app.requests.put")
@patch("app.current_user")
def test_update_profile_post_failure(mock_current_user, mock_requests_put, client):
    """Test updating a profile when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_put.return_value.status_code = 500

    response = client.post(
        "/update", json={"username": "newuser", "email": "new@example.com"}
    )

    assert response.status_code == 500
    assert response.json == {"message": "Failed to update profile."}
    mock_requests_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/123",
        json={"username": "newuser", "email": "new@example.com"},
    )


@patch("app.requests.put")
@patch("app.current_user")
def test_update_profile_post_request_exception(
    mock_current_user, mock_requests_put, client
):
    """Test updating a profile when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_put.side_effect = requests.RequestException("Network error")
    response = client.post(
        "/update", json={"username": "newuser", "email": "new@example.com"}
    )

    assert response.status_code == 500
    assert response.json == {"message": "Error updating profile."}
    mock_requests_put.assert_called_once_with(
        f"{DB_SERVICE_URL}/users/update/123",
        json={"username": "newuser", "email": "new@example.com"},
    )


@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_update_profile_get_success(
    mock_current_user, mock_render_template, mock_requests_get, client
):
    """Test the update profile route."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = {
        "username": "testuser",
        "email": "test@example.com",
    }
    mock_render_template.return_value = "Mocked Update Profile Page"

    response = client.get("/update")

    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Mocked Update Profile Page"
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")
    mock_render_template.assert_called_once_with(
        "update.html", user={"username": "testuser", "email": "test@example.com"}
    )


@patch("app.requests.get")
@patch("app.render_template")
@patch("app.current_user")
def test_update_profile_get_failure(
    mock_current_user, mock_render_template, mock_requests_get, client
):
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
    assert response.json is None
    mock_update_user_by_id.assert_not_called()


@patch("app.update_user_by_id")
@patch("app.current_user")
def test_save_profile_no_valid_fields(
    mock_current_user, mock_update_user_by_id, client
):
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


### Test generate_weekly_plan function ###
@patch("app.add_plan")
@patch("app.requests.post")
@patch("app.requests.get")
@patch("app.current_user")
def test_generate_weekly_plan_success(
    mock_current_user, mock_requests_get, mock_requests_post, mock_add_plan, client
):
    """Test generating a weekly plan successfully."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = [
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "sex": "Male",
                    "height": 180,
                    "weight": 75,
                    "goal_weight": 70,
                    "fat_rate": 20,
                    "goal_fat_rate": 15,
                }
            ),
        ),
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[{"workout_name": "Push Ups"}, {"workout_name": "Sit Ups"}]
            ),
        ),
    ]
    mock_requests_post.return_value = MagicMock(
        status_code=200, json=MagicMock(return_value={"plan": "sample_plan"})
    )
    mock_add_plan.return_value = None

    response = client.post("/api/generate-weekly-plan")

    assert response.status_code == 200
    assert response.json == {"success": True, "plan": {"plan": "sample_plan"}}
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/users/get/123")
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/exercises/all")
    mock_requests_post.assert_called_once_with(
        "http://machine-learning-client:8080/plan",
        json={
            "workout": ["Push Ups", "Sit Ups"],
            "user_id": "123",
            "sex": "Male",
            "height": 180,
            "weight": 75,
            "goal_weight": 70,
            "fat_rate": 20,
            "goal_fat_rate": 15,
            "additional_note": "",
        },
        timeout=10,
    )

    actual_call_args = mock_add_plan.call_args[0]
    assert actual_call_args[0].date() == datetime.now().date()
    assert actual_call_args[1] == {"plan": "sample_plan"}


@patch("app.requests.get")
@patch("app.current_user")
def test_generate_weekly_plan_user_not_found(
    mock_current_user, mock_requests_get, client
):
    """Test generating a weekly plan when the user is not found."""
    mock_current_user.id = "123"
    mock_requests_get.return_value = MagicMock(status_code=404)
    response = client.post("/api/generate-weekly-plan")

    assert response.status_code == 404
    assert response.json == {"success": False, "message": "User not found"}
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/users/get/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_generate_weekly_plan_exercises_failure(
    mock_current_user, mock_requests_get, client
):
    """Test generating a weekly plan when the exercises API call fails."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = [
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "sex": "Male",
                    "height": 180,
                    "weight": 75,
                    "goal_weight": 70,
                    "fat_rate": 20,
                    "goal_fat_rate": 15,
                }
            ),
        ),
        MagicMock(status_code=500),
    ]
    response = client.post("/api/generate-weekly-plan")

    assert response.status_code == 500
    assert response.json == {
        "success": False,
        "message": "Failed to retrieve exercises",
    }
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/users/get/123")
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/exercises/all")


@patch("app.requests.post")
@patch("app.requests.get")
@patch("app.current_user")
def test_generate_weekly_plan_ml_failure(
    mock_current_user, mock_requests_get, mock_requests_post, client
):
    """Test generating a weekly plan when the ML API call fails."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = [
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "sex": "Male",
                    "height": 180,
                    "weight": 75,
                    "goal_weight": 70,
                    "fat_rate": 20,
                    "goal_fat_rate": 15,
                }
            ),
        ),
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[{"workout_name": "Push Ups"}, {"workout_name": "Sit Ups"}]
            ),
        ),
    ]
    mock_requests_post.return_value = MagicMock(status_code=500)
    response = client.post("/api/generate-weekly-plan")

    assert response.status_code == 500
    assert response.json == {"success": False, "message": "Failed to generate plan"}
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/users/get/123")
    mock_requests_post.assert_called_once()


@patch("app.requests.post")
@patch("app.requests.get")
@patch("app.current_user")
def test_generate_weekly_plan_request_exception(
    mock_current_user, mock_requests_get, mock_requests_post, client
):
    """Test generating a weekly plan when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = [
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "sex": "Male",
                    "height": 180,
                    "weight": 75,
                    "goal_weight": 70,
                    "fat_rate": 20,
                    "goal_fat_rate": 15,
                }
            ),
        ),
        MagicMock(
            status_code=200,
            json=MagicMock(
                return_value=[{"workout_name": "Push Ups"}, {"workout_name": "Sit Ups"}]
            ),
        ),
    ]
    mock_requests_post.side_effect = requests.RequestException("Network error")
    response = client.post("/api/generate-weekly-plan")

    assert response.status_code == 500
    assert response.json == {
        "success": False,
        "message": "Error communicating with ML Client",
    }
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/users/get/123")
    mock_requests_get.assert_any_call(f"{DB_SERVICE_URL}/exercises/all")
    mock_requests_post.assert_called_once()


### Test add_plan function ###
@patch("app.search_exercise")
@patch("app.add_todo_api")
def test_add_plan_success(mock_add_todo_api, mock_search_exercise):
    """Test adding a plan successfully."""
    mock_search_exercise.side_effect = lambda name: (
        [{"_id": f"{name}_id"}] if name != "Nonexistent" else []
    )
    date = datetime(2024, 12, 1)
    plan = {
        "Day 1": ["Push Ups", "Sit Ups"],
        "Day 2": ["Nonexist", "Squats"],
        "Explaining": "Details about the plan.",
    }

    add_plan(date, plan)

    mock_search_exercise.assert_any_call("Push Ups")
    mock_search_exercise.assert_any_call("Sit Ups")
    mock_search_exercise.assert_any_call("Nonexist")
    mock_search_exercise.assert_any_call("Squats")

    mock_add_todo_api.assert_any_call("Push Ups_id", "2024-12-01")
    mock_add_todo_api.assert_any_call("Sit Ups_id", "2024-12-01")
    mock_add_todo_api.assert_any_call("Squats_id", "2024-12-02")
    assert mock_add_todo_api.call_count == 4


@patch("app.search_exercise")
@patch("app.add_todo_api")
def test_add_plan_empty_plan(mock_add_todo_api, mock_search_exercise):
    """Test adding an empty plan."""
    date = datetime(2024, 12, 1)
    plan = {}
    add_plan(date, plan)

    mock_search_exercise.assert_not_called()
    mock_add_todo_api.assert_not_called()


@patch("app.search_exercise")
@patch("app.add_todo_api")
def test_add_plan_no_matching_exercises(mock_add_todo_api, mock_search_exercise):
    """Test adding a plan with no matching exercises."""
    mock_search_exercise.side_effect = lambda name: []
    date = datetime(2024, 12, 1)
    plan = {
        "Day 1": ["Nonexistent Exercise"],
        "Day 2": ["Another Nonexistent Exercise"],
    }

    add_plan(date, plan)

    mock_search_exercise.assert_any_call("Nonexistent Exercise")
    mock_search_exercise.assert_any_call("Another Nonexistent Exercise")
    mock_add_todo_api.assert_not_called()


### Test get_workout_data function ###
@patch("app.requests.get")
@patch("app.current_user")
def test_get_workout_data_success(mock_current_user, mock_requests_get):
    """Test get_workout_data with successful API call."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = [
        {
            "date": "Mon, 04 Dec 2023 10:00:00 EST",
            "todo": [{"workout_name": "Push Ups"}, {"workout_name": "Sit Ups"}],
        },
        {
            "date": "Tue, 05 Dec 2023 10:00:00 EST",
            "todo": [{"workout_name": "Squats"}],
        },
    ]

    with app.test_request_context("/api/workout-data"):
        response = get_workout_data()
        assert response.status_code == 200
        assert response.json == {
            "2023-12-04": 2,
            "2023-12-05": 1,
        }
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_get_workout_data_no_workouts(mock_current_user, mock_requests_get):
    """Test get_workout_data when there are no workouts."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = []

    with app.test_request_context("/api/workout-data"):
        response = get_workout_data()
        assert response.status_code == 200
        assert response.json == {}


@patch("app.requests.get")
@patch("app.current_user")
def test_get_workout_data_api_failure(mock_current_user, mock_requests_get, client):
    """Test get_workout_data when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 500
    response = client.get("/api/workout-data")

    assert response.status_code == 500
    assert response.json == {"error": "Failed to retrieve workout data"}
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/123")


@patch("app.requests.get")
@patch("app.current_user")
def test_get_workout_data_request_exception(
    mock_current_user, mock_requests_get, client
):
    """Test get_workout_data when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_get.side_effect = requests.RequestException("Network error")
    response = client.get("/api/workout-data")

    assert response.status_code == 500
    assert response.json == {"error": "Failed to retrieve workout data"}
    mock_requests_get.assert_called_once_with(f"{DB_SERVICE_URL}/todo/123")


### Test save_plan function ###
@patch("app.requests.post")
@patch("app.current_user")
def test_save_plan_success(mock_current_user, mock_requests_post):
    """Test saving a plan successfully."""
    mock_current_user.id = "123"
    mock_requests_post.return_value.status_code = 200
    mock_requests_post.return_value.json.return_value = {
        "success": True,
        "message": "Plan saved successfully",
    }

    with app.test_request_context(
        "/api/plan/save",
        method="POST",
        json={"plan": {"Day 1": ["Push Ups", "Sit Ups"], "Day 2": ["Squats"]}},
    ):
        response_data, status_code = save_plan()

        assert status_code == 200
        assert response_data == {"success": True, "message": "Plan saved successfully"}
        mock_requests_post.assert_called_once_with(
            f"{DB_SERVICE_URL}/plan/save",
            json={
                "user_id": "123",
                "plan": {"Day 1": ["Push Ups", "Sit Ups"], "Day 2": ["Squats"]},
            },
        )


@patch("app.requests.post")
@patch("app.current_user")
def test_save_plan_no_data(mock_current_user, mock_requests_post):
    """Test saving a plan with no data."""
    mock_current_user.id = "123"

    with app.test_request_context(
        "/api/plan/save",
        method="POST",
        json={"random_field": "value"},
        headers={"Content-Type": "application/json"},
    ):
        response_data, status_code = save_plan()
        response = make_response(response_data, status_code)

        assert status_code == 400
        assert response.json == {"success": False, "message": "Plan data is required"}
        mock_requests_post.assert_not_called()


@patch("app.requests.post")
@patch("app.current_user")
def test_save_plan_no_plan_data(mock_current_user, mock_requests_post):
    """Test saving a plan with no plan data."""
    mock_current_user.id = "123"

    with app.test_request_context(
        "/api/plan/save", method="POST", json={"random_field": "value"}
    ):
        response_data, status_code = save_plan()
        response = make_response(response_data, status_code)

        assert status_code == 400
        assert response.json == {"success": False, "message": "Plan data is required"}
        mock_requests_post.assert_not_called()


@patch("app.requests.post")
@patch("app.current_user")
def test_save_plan_request_exception(mock_current_user, mock_requests_post):
    """Test saving a plan when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_post.side_effect = requests.RequestException("Network error")

    with app.test_request_context(
        "/api/plan/save",
        method="POST",
        json={"plan": {"Day 1": ["Push Ups", "Sit Ups"]}},
    ):
        response_data, status_code = save_plan()
        response = make_response(response_data, status_code)

        assert status_code == 500
        assert response.json == {"success": False, "message": "Network error"}
        mock_requests_post.assert_called_once_with(
            f"{DB_SERVICE_URL}/plan/save",
            json={
                "user_id": "123",
                "plan": {"Day 1": ["Push Ups", "Sit Ups"]},
            },
        )


### Test delete_todo_by_date function ###
@patch("app.requests.get")
@patch("app.current_user")
def test_delete_todo_by_date_success(mock_current_user, mock_requests_get):
    """Test deleting todos successfully."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = [
        {
            "todo": [
                {"exercise_todo_id": "1", "workout_name": "Push Ups"},
                {"exercise_todo_id": "2", "workout_name": "Squats"},
            ]
        }
    ]

    with app.test_request_context(
        "/todo/delete_by_date?date=Thursday, December 4, 2023", method="GET"
    ):
        response = delete_todo_by_date()
        response = make_response(response)

        assert response.status_code == 200
        assert b"delete-btn" in response.data
        mock_requests_get.assert_called_once_with(
            f"{DB_SERVICE_URL}/todo/get_by_date/123",
            params={"start_date": "2023-12-04", "end_date": "2023-12-04"},
        )


@patch("app.requests.get")
@patch("app.current_user")
def test_delete_todo_by_date_db_failure(mock_current_user, mock_requests_get):
    """Test deleting todos when the database service fails."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 500

    with app.test_request_context(
        "/todo/delete_by_date?date=Thursday, December 4, 2023", method="GET"
    ):
        response = delete_todo_by_date()
        response = make_response(response)

        assert response.status_code == 200
        mock_requests_get.assert_called_once_with(
            f"{DB_SERVICE_URL}/todo/get_by_date/123",
            params={"start_date": "2023-12-04", "end_date": "2023-12-04"},
        )


@patch("app.requests.get")
@patch("app.current_user")
def test_delete_todo_by_date_no_todos(mock_current_user, mock_requests_get):
    """Test deleting todos when there are no todos."""
    mock_current_user.id = "123"
    mock_requests_get.return_value.status_code = 200
    mock_requests_get.return_value.json.return_value = []

    with app.test_request_context(
        "/todo/delete_by_date?date=Thursday, December 4, 2023", method="GET"
    ):
        response = delete_todo_by_date()
        response = make_response(response)

        assert response.status_code == 200
        assert b"delete-btn" in response.data
        assert b"No exercises listed" not in response.data


### Test delete_exercise_by_date function ###
@patch("app.requests.post")
@patch("app.current_user")
def test_delete_exercise_by_date_success(mock_current_user, mock_requests_post):
    """Test deleting an exercise successfully."""
    mock_current_user.id = "123"
    mock_requests_post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(
            return_value={"success": True, "message": "Exercise deleted successfully"}
        ),
    )

    with app.test_request_context(
        "/api/exercise/delete",
        method="POST",
        json={"date": "Monday, December 4, 2023", "exercise_id": "ex123"},
        headers={"Content-Type": "application/json"},
    ):
        response = delete_exercise_by_date()
        response = make_response(*response)

        assert response.status_code == 200
        assert response.json == {
            "success": True,
            "message": "Exercise deleted successfully",
        }
        mock_requests_post.assert_called_once_with(
            f"{DB_SERVICE_URL}/todo/delete_exercise",
            json={"user_id": "123", "date": "2023-12-04", "exercise_id": "ex123"},
        )


@patch("app.requests.post")
@patch("app.current_user")
def test_delete_exercise_by_date_failure(mock_current_user, mock_requests_post):
    """Test deleting an exercise when the API call fails."""
    mock_current_user.id = "123"
    mock_requests_post.return_value = MagicMock(
        status_code=500, text="Internal Server Error"
    )

    with app.test_request_context(
        "/api/exercise/delete",
        method="POST",
        json={"date": "Monday, December 4, 2023", "exercise_id": "ex123"},
        headers={"Content-Type": "application/json"},
    ):
        response = delete_exercise_by_date()
        response = make_response(*response)

        assert response.status_code == 500
        assert response.json == {
            "success": False,
            "message": "Failed to delete exercise",
        }
        mock_requests_post.assert_called_once_with(
            f"{DB_SERVICE_URL}/todo/delete_exercise",
            json={"user_id": "123", "date": "2023-12-04", "exercise_id": "ex123"},
        )


@patch("app.requests.post")
@patch("app.current_user")
def test_delete_exercise_by_date_request_exception(
    mock_current_user, mock_requests_post
):
    """Test deleting an exercise when a request exception occurs."""
    mock_current_user.id = "123"
    mock_requests_post.side_effect = requests.RequestException("Network error")

    with app.test_request_context(
        "/api/exercise/delete",
        method="POST",
        json={"date": "Monday, December 4, 2023", "exercise_id": "ex123"},
        headers={"Content-Type": "application/json"},
    ):
        response = delete_exercise_by_date()
        response = make_response(*response)

        assert response.status_code == 500
        assert response.json == {
            "success": False,
            "message": "Error communicating with db-service: Network error",
        }
        mock_requests_post.assert_called_once_with(
            f"{DB_SERVICE_URL}/todo/delete_exercise",
            json={"user_id": "123", "date": "2023-12-04", "exercise_id": "ex123"},
        )


if __name__ == "__main__":
    pytest.main()
