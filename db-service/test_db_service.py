# test_db_service.py

import os
import pytest
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from db_service import app, users_collection, todo_collection, exercises_collection, search_history_collection, edit_transcription_collection
from dotenv import load_dotenv

@pytest.fixture(scope='function')
def test_client():
    load_dotenv()

    users_collection.delete_many({})
    todo_collection.delete_many({})
    exercises_collection.delete_many({})
    search_history_collection.delete_many({})
    edit_transcription_collection.delete_many({})

    client = app.test_client()
    yield client

    users_collection.delete_many({})
    todo_collection.delete_many({})
    exercises_collection.delete_many({})
    search_history_collection.delete_many({})
    edit_transcription_collection.delete_many({})

def test_create_user(test_client):
    """Test creating a new user."""
    response = test_client.post('/users/create', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'user_id' in data

    user = users_collection.find_one({'_id': ObjectId(data['user_id'])})
    assert user is not None
    assert user['username'] == 'testuser'
    assert check_password_hash(user['password'], 'testpass')

def test_authenticate_user(test_client):
    """Test authenticating a user."""
    hashed_password = generate_password_hash('testpass', method='pbkdf2:sha256')
    user_id = users_collection.insert_one({
        'username': 'testuser',
        'password': hashed_password
    }).inserted_id

    response = test_client.post('/users/auth', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['_id'] == str(user_id)
    assert data['username'] == 'testuser'

def test_get_user(test_client):
    """Test getting a user by ID."""
    user_id = users_collection.insert_one({
        'username': 'testuser',
        'password': 'hashedpassword'
    }).inserted_id

    response = test_client.get(f'/users/get/{user_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['_id'] == str(user_id)
    assert data['username'] == 'testuser'

def test_add_todo(test_client):
    """Test adding a todo exercise."""
    user_id = str(ObjectId())
    exercise_item = {
        'exercise_todo_id': 1,
        'exercise_id': str(ObjectId()),
        'name': 'Push-up',
        'reps': 10
    }
    date_str = datetime.utcnow().strftime('%Y-%m-%d')

    response = test_client.post('/todo/add', json={
        'user_id': user_id,
        'exercise_item': exercise_item,
        'date': date_str
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']

    today_start = datetime.strptime(date_str, '%Y-%m-%d')
    todo_entry = todo_collection.find_one({
        'user_id': user_id,
        'date': {
            '$gte': today_start,
            '$lt': today_start + timedelta(days=1)
        }
    })
    assert todo_entry is not None
    assert todo_entry['todo'][0]['name'] == 'Push-up'

def test_get_todo(test_client):
    """Test getting a user's todo list."""
    user_id = str(ObjectId())
    today_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todo_collection.insert_one({
        'user_id': user_id,
        'date': today_date,
        'todo': [
            {
                'exercise_todo_id': 1,
                'exercise_id': str(ObjectId()),
                'name': 'Squat',
                'reps': 15
            }
        ]
    })

    response = test_client.get(f'/todo/get/{user_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['user_id'] == user_id
    assert len(data['todo']) == 1
    assert data['todo'][0]['name'] == 'Squat'

def test_delete_todo(test_client):
    """Test deleting a todo exercise."""
    user_id = str(ObjectId())
    exercise_todo_id = "exercise123"
    today_date_str = datetime.utcnow().strftime("%Y-%m-%d")
    todo_collection.insert_one({
        'user_id': user_id,
        'date': datetime.strptime(today_date_str, '%Y-%m-%d'),
        'todo': [
            {
                'exercise_todo_id': exercise_todo_id,
                'exercise_id': str(ObjectId()),
                'name': 'Lunge',
                'reps': 12
            }
        ]
    })

    response = test_client.post('/todo/delete_exercise', json={
        'user_id': user_id,
        'date': today_date_str,
        'exercise_id': exercise_todo_id
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']

    todo_entry = todo_collection.find_one({'user_id': user_id, 'date': datetime.strptime(today_date_str, '%Y-%m-%d')})
    assert todo_entry is not None
    assert len(todo_entry['todo']) == 0

def test_edit_todo_item(test_client):
    """Test updating a todo exercise."""
    user_id = str(ObjectId())
    exercise_todo_id = "exercise_edit_123"
    today_date_str = datetime.utcnow().strftime("%Y-%m-%d")

    todo_collection.insert_one({
        'user_id': user_id,
        'date': datetime.strptime(today_date_str, '%Y-%m-%d'),
        'todo': [
            {
                'exercise_todo_id': exercise_todo_id,
                'exercise_id': str(ObjectId()),
                'name': 'Plank',
                'duration': '60s'
            }
        ]
    })

    update_fields = {'duration': '90s'}
    response = test_client.post('/todo/update_exercise', json={
        'user_id': user_id,
        'date': today_date_str,
        'exercise_todo_id': exercise_todo_id,
        'update_fields': update_fields
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']

    todo_entry = todo_collection.find_one({'user_id': user_id, 'date': datetime.strptime(today_date_str, '%Y-%m-%d')})
    assert todo_entry['todo'][0]['duration'] == '90s'

def test_get_todo_item(test_client):
    """Test getting a todo exercise by ID."""
    user_id = str(ObjectId())
    exercise_todo_id = 1
    todo_item = {
        'exercise_todo_id': exercise_todo_id,
        'exercise_id': str(ObjectId()),
        'name': 'Burpee',
        'reps': 20
    }
    todo_collection.insert_one({
        'user_id': user_id,
        'date': datetime.utcnow(),
        'todo': [todo_item]
    })

    response = test_client.get(f'/todo/get-item/{user_id}/{exercise_todo_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Burpee'
    assert data['reps'] == 20

def test_search_exercises(test_client):
    """Test searching for exercises."""
    exercises_collection.insert_many([
        {'workout_name': 'Push-up'},
        {'workout_name': 'Pull-up'},
        {'workout_name': 'Squat'}
    ])

    response = test_client.post('/exercises/search', json={'query': 'push'})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['workout_name'] == 'Push-up'

def test_get_exercise(test_client):
    """Test getting an exercise by ID."""
    exercise_id = exercises_collection.insert_one({
        'workout_name': 'Burpee',
        'description': 'A full-body exercise.'
    }).inserted_id

    response = test_client.get(f'/exercises/get/{exercise_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['_id'] == str(exercise_id)
    assert data['workout_name'] == 'Burpee'

def test_add_search_history(test_client):
    """Test adding a search history entry."""
    user_id = str(ObjectId())
    content = 'Deadlift'

    response = test_client.post('/search-history/add', json={
        'user_id': user_id,
        'content': content
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']

    history_entry = search_history_collection.find_one({'user_id': user_id})
    assert history_entry is not None
    assert history_entry['content'] == content

def test_get_search_history(test_client):
    """Test getting a user's search history."""
    user_id = str(ObjectId())
    search_history_collection.insert_many([
        {'user_id': user_id, 'content': 'Bench Press', 'time': datetime.utcnow()},
        {'user_id': user_id, 'content': 'Overhead Press', 'time': datetime.utcnow()}
    ])

    response = test_client.get(f'/search-history/get/{user_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['user_id'] == user_id

def test_add_transcription(test_client):
    """Test adding a transcription."""
    user_id = str(ObjectId())
    content = 'Transcribed workout notes.'

    response = test_client.post('/transcriptions/add', json={
        'user_id': user_id,
        'content': content
    })
    assert response.status_code == 200
    data = response.get_json()
    assert 'id' in data

    transcription = edit_transcription_collection.find_one({'_id': ObjectId(data['id'])})
    assert transcription is not None
    assert transcription['content'] == content

def test_update_user(test_client):
    """Test updating a user's information."""
    user_id = users_collection.insert_one({
        'username': 'testuser',
        'password': 'hashedpassword',
        'age': 25
    }).inserted_id

    response = test_client.put(f'/users/update/{user_id}', json={
        'age': 26
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success']

    user = users_collection.find_one({'_id': user_id})
    assert user['age'] == 26

def test_get_all_exercises(test_client):
    """Test getting all exercises."""
    exercises_collection.insert_many([
        {'workout_name': 'Sit-up'},
        {'workout_name': 'Jumping Jack'}
    ])

    response = test_client.get('/exercises/all')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2

def test_get_todos(test_client):
    """Test getting all todos."""
    user_id = str(ObjectId())
    todo_collection.insert_many([
        {
            'user_id': user_id,
            'date': datetime.utcnow(),
            'todo': [{'exercise_todo_id': 1, 'name': 'Plank'}]
        },
        {
            'user_id': user_id,
            'date': datetime.utcnow() - timedelta(days=1),
            'todo': [{'exercise_todo_id': 2, 'name': 'Crunch'}]
        }
    ])

    response = test_client.get(f'/todo/{user_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['user_id'] == user_id

def test_get_todo_by_date(test_client):
    """Test getting todos by date range."""
    user_id = str(ObjectId())
    date_today = datetime.utcnow().strftime('%Y-%m-%d')
    date_yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

    todo_collection.insert_many([
        {
            'user_id': user_id,
            'date': datetime.strptime(date_today, '%Y-%m-%d'),
            'todo': [{'exercise_todo_id': 1, 'name': 'Jumping Jack'}]
        },
        {
            'user_id': user_id,
            'date': datetime.strptime(date_yesterday, '%Y-%m-%d'),
            'todo': [{'exercise_todo_id': 2, 'name': 'Sit-up'}]
        }
    ])

    response = test_client.get(f'/todo/get_by_date/{user_id}', query_string={
        'start_date': date_yesterday,
        'end_date': date_today
    })
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2

def test_add_or_skip_todo(test_client):
    """Test adding or skipping a todo exercise."""
    import db_service
    from db_service import add_or_skip_todo
    db_service.date = datetime.utcnow().strftime("%Y-%m-%d")

    user_id = str(ObjectId())
    result = add_or_skip_todo(user_id)
    assert result.get('created', False) or result.get('exists', False), f"Unexpected result: {result}"

def test_create_user_missing_fields(test_client):
    """Test creating a user with missing fields."""
    response = test_client.post('/users/create', json={
        'username': 'testuser'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data['message'] == 'Username and password are required!'

def test_create_user_duplicate_username(test_client):
    """Test creating a user with a duplicate username."""
    users_collection.insert_one({
        'username': 'testuser',
        'password': 'hashedpassword'
    })

    response = test_client.post('/users/create', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data['message'] == 'Username already exists!'

def test_authenticate_user_invalid_credentials(test_client):
    """Test authenticating a user with invalid credentials."""
    response = test_client.post('/users/auth', json={
        'username': 'nonexistent',
        'password': 'wrongpass'
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Invalid username or password'

def test_get_user_not_found(test_client):
    """Test getting a user that does not exist."""
    fake_user_id = ObjectId()
    response = test_client.get(f'/users/get/{fake_user_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'User not found'

def test_get_todo_by_date_missing_params(test_client):
    """Test getting todos by date range with missing parameters."""
    user_id = str(ObjectId())
    response = test_client.get(f'/todo/get_by_date/{user_id}', query_string={
        'start_date': '2024-01-01'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'start_date and end_date are required'

def test_get_todo_by_date_invalid_date_format(test_client):
    """Test getting todos by date range with invalid date format."""
    user_id = str(ObjectId())
    response = test_client.get(f'/todo/get_by_date/{user_id}', query_string={
        'start_date': 'invalid-date',
        'end_date': '2024-01-02'
    })
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data

def test_get_exercise_not_found(test_client):
    """Test getting an exercise that does not exist."""
    fake_exercise_id = ObjectId()
    response = test_client.get(f'/exercises/get/{fake_exercise_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Exercise not found'

def test_get_exercise_by_id_missing_params(test_client):
    """Test getting an exercise by ID with missing parameters."""
    response = test_client.get('/todo/get_exercise_by_id', query_string={
        'date': '2024-01-01',
        'exercise_todo_id': 'some_id'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_update_exercise_missing_fields(test_client):
    """Test updating a todo exercise with missing fields."""
    response = test_client.post('/todo/update_exercise', json={
        'user_id': str(ObjectId()),
        'exercise_todo_id': 'missing_date',
        'update_fields': {'duration': '30s'}
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_delete_exercise_not_found(test_client):
    """Test deleting a todo exercise that does not exist."""
    user_id = str(ObjectId())
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    response = test_client.post('/todo/delete_exercise', json={
        'user_id': user_id,
        'date': date_str,
        'exercise_id': 'nonexistent_exercise'
    })
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] == False
    assert data['message'] == 'No todos found for the specified date'

def test_search_exercises_no_match(test_client):
    """Test searching for exercises with no match."""
    response = test_client.post('/exercises/search', json={'query': 'unmatchable'})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 0

def test_plan_save_missing_fields(test_client):
    """Test saving a plan with missing fields."""
    response = test_client.post('/plan/save', json={
        'user_id': str(ObjectId())
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data['message'] == 'user_id and plan data are required'

def test_plan_save_exception(test_client, monkeypatch):
    """Test saving a plan with a database exception."""
    def mock_insert_one(doc):
        raise Exception("Mock DB Error")
    monkeypatch.setattr("db_service.plan_collection.insert_one", mock_insert_one)

    response = test_client.post('/plan/save', json={
        'user_id': str(ObjectId()),
        'plan': {'workout': 'Running'}
    })
    assert response.status_code == 500
    data = response.get_json()
    assert data['success'] == False
    assert 'Mock DB Error' in data['message']

def test_add_search_history_missing_fields(test_client):
    """Test adding a search history entry with missing fields."""
    response = test_client.post('/search-history/add', json={
        'user_id': str(ObjectId())
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_add_transcription_missing_fields(test_client):
    """Test adding a transcription with missing fields."""
    response = test_client.post('/transcriptions/add', json={
        'user_id': str(ObjectId())
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_add_user_db_error(test_client, monkeypatch):
    """Test creating a user with a database exception."""
    def mock_insert_one(doc):
        raise Exception("Mock Insert Error")
    monkeypatch.setattr("db_service.users_collection.insert_one", mock_insert_one)

    response = test_client.post('/users/create', json={
        'username': 'erroruser',
        'password': 'pass'
    })
    assert response.status_code == 500
    data = response.get_json()
    assert data['message'] == 'Internal server error'

def test_get_user_db_error(test_client, monkeypatch):
    """Test getting a user with a database exception."""
    def mock_find_one(query):
        raise Exception("Mock Find Error")
    monkeypatch.setattr("db_service.users_collection.find_one", mock_find_one)

    fake_user_id = ObjectId()
    response = test_client.get(f'/users/get/{fake_user_id}')
    assert response.status_code == 404 or response.status_code == 500

def test_update_exercise_no_match(test_client):
    """Test updating a todo exercise that does not exist."""
    user_id = str(ObjectId())
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    response = test_client.post('/todo/update_exercise', json={
        'user_id': user_id,
        'date': date_str,
        'exercise_todo_id': 'nonexistent_id',
        'update_fields': {'duration': '100s'}
    })
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert data['message'] == 'No matching exercise found'

def test_get_todo_invalid_date_format(test_client):
    """Test getting a todo with an invalid date format."""
    user_id = str(ObjectId())
    exercise_item = {
        'exercise_todo_id': 1,
        'exercise_id': str(ObjectId()),
        'name': 'Invalid Date Test',
        'reps': 5
    }
    response = test_client.post('/todo/add', json={
        'user_id': user_id,
        'exercise_item': exercise_item,
        'date': 'invalid-date-format'
    })
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data

def test_get_exercise_by_id_invalid_date(test_client):
    """Test getting an exercise by ID with an invalid date."""
    response = test_client.get('/todo/get_exercise_by_id', query_string={
        'user_id': str(ObjectId()),
        'date': 'invalid-date',
        'exercise_todo_id': 'some_id'
    })
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data

def test_get_todo_db_exception(test_client, monkeypatch):
    """Test getting a todo with a database exception."""
    def mock_find_one(query):
        raise Exception("Mock DB error in get_todo")
    monkeypatch.setattr("db_service.todo_collection.find_one", mock_find_one)

    user_id = str(ObjectId())
    response = test_client.get(f'/todo/get/{user_id}')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data
    assert 'Mock DB error in get_todo' in data['error']

def test_get_all_exercises_db_exception(test_client, monkeypatch):
    """Test getting all exercises with a database exception."""
    def mock_find(filter, projection):
        raise Exception("Mock DB error in get_all_exercises")
    monkeypatch.setattr("db_service.exercises_collection.find", mock_find)

    response = test_client.get('/exercises/all')
    assert response.status_code == 500 or response.status_code == 200

def test_get_todos_db_exception(test_client, monkeypatch):
    """Test getting all todos with a database exception."""
    def mock_find(query):
        raise Exception("Mock DB error in get_todos")
    monkeypatch.setattr("db_service.todo_collection.find", mock_find)

    user_id = str(ObjectId())
    response = test_client.get(f'/todo/{user_id}')
    assert response.status_code == 500
    data = response.get_json()
    assert data['error'] == 'Failed to retrieve todos'

def test_get_by_date_db_exception(test_client, monkeypatch):
    """Test getting todos by date range with a database exception."""
    def mock_find(query):
        raise Exception("Mock DB error in get_by_date")
    monkeypatch.setattr("db_service.todo_collection.find", mock_find)

    user_id = str(ObjectId())
    date_today = datetime.utcnow().strftime('%Y-%m-%d')
    date_yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

    response = test_client.get(f'/todo/get_by_date/{user_id}', query_string={
        'start_date': date_yesterday,
        'end_date': date_today
    })
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data
    assert 'Mock DB error in get_by_date' in data['message']

def test_users_update_db_exception(test_client, monkeypatch):
    """Test updating a user with a database exception."""
    def mock_update_one(filter, update):
        raise Exception("Mock DB error in users_update")
    monkeypatch.setattr("db_service.users_collection.update_one", mock_update_one)

    user_id = ObjectId()
    response = test_client.put(f'/users/update/{user_id}', json={
        'age': 30
    })
    assert response.status_code == 500
    data = response.get_json()
    assert data['error'] == 'Failed to update user'

def test_search_exercises_empty_query(test_client):
    """Test searching for exercises with an empty query."""
    response = test_client.post('/exercises/search', json={'query': ''})
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_todo_add_no_exercise_item(test_client):
    """Test adding a todo with no exercise item."""
    user_id = str(ObjectId())
    date_str = datetime.utcnow().strftime('%Y-%m-%d')

    response = test_client.post('/todo/add', json={
        'user_id': user_id,
        'date': date_str
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_update_exercise_invalid_date_format(test_client):
    """Test updating a todo exercise with an invalid date format."""
    response = test_client.post('/todo/update_exercise', json={
        'user_id': str(ObjectId()),
        'date': 'invalid-date',
        'exercise_todo_id': 'some_id',
        'update_fields': {'duration': '30s'}
    })
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data

def test_exercises_get_invalid_id_format(test_client):
    """Test getting an exercise with an invalid ID format."""
    response = test_client.get('/exercises/get/not_a_valid_id')
    assert response.status_code in (404, 500)

def test_users_get_invalid_id_format(test_client):
    """Test getting a user with an invalid ID format."""
    response = test_client.get('/users/get/invalid_user_id')
    assert response.status_code in (404, 500)

def test_create_user_no_json(test_client):
    """Test creating a user with no JSON data."""
    response = test_client.post('/users/create')
    assert response.status_code in (400, 500)

def test_plan_save_no_json(test_client):
    """Test saving a plan with no JSON data."""
    response = test_client.post('/plan/save')
    assert response.status_code in (400, 500)

def test_plan_save_invalid_json(test_client):
    """Test saving a plan with invalid JSON data."""    
    response = test_client.post('/plan/save', json={
        'user_id': str(ObjectId())
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data['message'] == 'user_id and plan data are required'

def test_todo_get_by_date_end_before_start(test_client):
    """Test getting todos by date range with end date before start date."""
    user_id = str(ObjectId())
    start_date = datetime.utcnow().strftime('%Y-%m-%d')
    end_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    response = test_client.get(f'/todo/get_by_date/{user_id}', query_string={
        'start_date': start_date,
        'end_date': end_date
    })
    assert response.status_code in (200, 500)

def test_todo_delete_exercise_no_exercise_id(test_client):
    """Test deleting a todo exercise with no exercise ID."""
    user_id = str(ObjectId())
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    response = test_client.post('/todo/delete_exercise', json={
        'user_id': user_id,
        'date': date_str
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' not in data
    assert data['message'] == 'user_id, date, and exercise_id are required'
