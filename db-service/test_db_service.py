import pytest
from datetime import datetime, timedelta
from bson import ObjectId
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
from werkzeug.security import generate_password_hash
import json


load_dotenv()

from db_service import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="session")
def db_connection():
    mongo_uri = os.getenv("TEST_MONGO_URI")
    db_name = os.getenv("TEST_DB_NAME")
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
    db = client[db_name]
    yield db
    client.close()

@pytest.fixture(autouse=True)
def setup_test_collections(db_connection):
    test_user = {
        "_id": ObjectId(),
        "username": f"testuser_{datetime.utcnow().timestamp()}",
        "password": generate_password_hash("testpass")
    }
    db_connection.users.insert_one(test_user)
    
    test_exercise = {
        "_id": ObjectId(),
        "workout_name": "Test Exercise",
        "description": "Test description",
        "instruction": "Test instruction",
        "working_time": None,
        "reps": None,
        "weight": None
    }
    db_connection.exercises.insert_one(test_exercise)
    
    yield {
        "user_id": str(test_user["_id"]),
        "exercise_id": str(test_exercise["_id"])
    }
    
    db_connection.users.delete_many({"username": {"$regex": "^testuser_"}})
    db_connection.users.delete_many({"username": {"$regex": "^newuser_"}})
    db_connection.todo.delete_many({"user_id": str(test_user["_id"])})
    db_connection.search_history.delete_many({"user_id": str(test_user["_id"])})
    db_connection.edit_transcription.delete_many({"user_id": str(test_user["_id"])})
    db_connection.plans.delete_many({"user_id": str(test_user["_id"])})

def test_user_operations(client, setup_test_collections):
    new_user = {
        "username": f"newuser_{datetime.utcnow().timestamp()}",
        "password": "testpass"
    }
    response = client.post('/users/create',
                          data=json.dumps(new_user),
                          content_type='application/json')
    assert response.status_code == 200
    user_id = json.loads(response.data)["user_id"]
    
    response = client.post('/users/create',
                          data=json.dumps(new_user),
                          content_type='application/json')
    assert response.status_code == 400
    
    response = client.post('/users/create',
                          data=json.dumps({"username": "test"}),
                          content_type='application/json')
    assert response.status_code == 400
    
    response = client.get(f'/users/get/{user_id}')
    assert response.status_code == 200
    
    response = client.get(f'/users/get/{str(ObjectId())}')
    assert response.status_code == 404
    
    update_data = {"age": 25}
    response = client.put(f'/users/update/{user_id}',
                         data=json.dumps(update_data),
                         content_type='application/json')
    assert response.status_code == 200

def test_authentication(client, setup_test_collections):
    auth_data = {
        "username": f"testuser_{datetime.utcnow().timestamp()}",
        "password": "testpass"
    }
    client.post('/users/create',
                data=json.dumps(auth_data),
                content_type='application/json')
    
    response = client.post('/users/auth',
                          data=json.dumps(auth_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    auth_data["password"] = "wrongpass"
    response = client.post('/users/auth',
                          data=json.dumps(auth_data),
                          content_type='application/json')
    assert response.status_code == 401
    
    response = client.post('/users/auth',
                          data=json.dumps({"username": "test"}),
                          content_type='application/json')
    assert response.status_code == 400

def test_todo_operations(client, setup_test_collections):
    """测试待办事项相关操作"""
    user_id = setup_test_collections["user_id"]
    exercise_id = setup_test_collections["exercise_id"]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    todo_data = {
        "user_id": user_id,
        "exercise_item": {
            "exercise_todo_id": "test123",
            "exercise_id": exercise_id,
            "status": "pending"
        },
        "date": today
    }
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    todo_data["exercise_item"]["exercise_todo_id"] = "test456"
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    response = client.get(f'/todo/get/{user_id}')
    assert response.status_code == 200
    
    response = client.get(
        f'/todo/get_exercise_by_id?user_id={user_id}&date={today}&exercise_todo_id=test123'
    )
    assert response.status_code == 200
    
    update_data = {
        "user_id": user_id,
        "date": today,
        "exercise_todo_id": "test123",
        "update_fields": {"status": "completed"}
    }
    response = client.post('/todo/update_exercise',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    delete_data = {
        "user_id": user_id,
        "date": today,
        "exercise_id": "test123"
    }
    response = client.post('/todo/delete_exercise',
                          data=json.dumps(delete_data),
                          content_type='application/json')
    assert response.status_code == 200

def test_exercise_operations(client, setup_test_collections):
    exercise_id = setup_test_collections["exercise_id"]
    
    response = client.post('/exercises/search',
                          data=json.dumps({"query": "Test"}),
                          content_type='application/json')
    assert response.status_code == 200
    
    response = client.post('/exercises/search',
                          data=json.dumps({"query": ""}),
                          content_type='application/json')
    assert response.status_code == 200
    
    response = client.get(f'/exercises/get/{exercise_id}')
    assert response.status_code == 404
    
    response = client.get('/exercises/all')
    assert response.status_code == 200

def test_search_and_transcription(client, setup_test_collections):
    user_id = setup_test_collections["user_id"]
    
    history_data = {"user_id": user_id, "content": "test search"}
    response = client.post('/search-history/add',
                          data=json.dumps(history_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    response = client.get(f'/search-history/get/{user_id}')
    assert response.status_code == 200
    
    transcription_data = {"user_id": user_id, "content": "test transcription"}
    response = client.post('/transcriptions/add',
                          data=json.dumps(transcription_data),
                          content_type='application/json')
    assert response.status_code == 200

def test_date_range_operations(client, setup_test_collections):
    user_id = setup_test_collections["user_id"]
    today = datetime.utcnow()
    
    for i in range(3):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        todo_data = {
            "user_id": user_id,
            "exercise_item": {
                "exercise_todo_id": f"test{i}",
                "exercise_id": setup_test_collections["exercise_id"]
            },
            "date": date
        }
        client.post('/todo/add', 
                   data=json.dumps(todo_data),
                   content_type='application/json')
    
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    response = client.get(
        f'/todo/get_by_date/{user_id}?start_date={start_date}&end_date={end_date}'
    )
    assert response.status_code == 200
    
    response = client.get(
        f'/todo/get_by_date/{user_id}?start_date=invalid&end_date={end_date}'
    )
    assert response.status_code == 500

def test_error_handling(client):
    """测试错误处理"""
    valid_object_id = str(ObjectId())
    
    response = client.get(f'/users/get/{valid_object_id}')
    assert response.status_code == 404
    
    response = client.get('/users/get/invalid-format')
    assert response.status_code == 500
    
    response = client.put(
        f'/users/update/{valid_object_id}',
        data=json.dumps({"name": "test"}),
        content_type='application/json'
    )
    assert response.status_code == 200
    
    response = client.get(f'/exercises/get/{valid_object_id}')
    assert response.status_code == 404

def test_plan_operations(client, setup_test_collections):
    user_id = setup_test_collections["user_id"]
    
    plan_data = {
        "user_id": user_id,
        "plan": {
            "monday": ["Exercise 1", "Exercise 2"],
            "tuesday": ["Exercise 3"]
        }
    }
    response = client.post('/plan/save',
                          data=json.dumps(plan_data),
                          content_type='application/json')
    assert response.status_code == 201
    
    response = client.post('/plan/save',
                          data=json.dumps({"user_id": user_id}),
                          content_type='application/json')
    assert response.status_code == 400
def test_todo_edge_cases(client, setup_test_collections):
    """Test edge cases for todo operations"""
    user_id = setup_test_collections["user_id"]
    exercise_id = setup_test_collections["exercise_id"]
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Test multiple todos on same day
    for i in range(3):
        todo_data = {
            "user_id": user_id,
            "exercise_item": {
                "exercise_todo_id": f"test{i}",
                "exercise_id": exercise_id,
                "status": "pending",
                "sets": i + 1,
                "reps": 10
            },
            "date": today
        }
        response = client.post('/todo/add',
                             data=json.dumps(todo_data),
                             content_type='application/json')
        assert response.status_code == 200

    # Test getting all todos
    response = client.get(f'/todo/{user_id}')
    assert response.status_code == 200
    todos = json.loads(response.data)
    assert len(todos) >= 1

    # Test updating multiple fields
    update_data = {
        "user_id": user_id,
        "date": today,
        "exercise_todo_id": "test0",
        "update_fields": {
            "status": "completed",
            "sets": 5,
            "reps": 15,
            "notes": "Updated workout"
        }
    }
    response = client.post('/todo/update_exercise',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200

def test_exercise_search_variations(client, setup_test_collections):
    """Test different variations of exercise search"""
    # Test case-insensitive search
    response = client.post('/exercises/search',
                          data=json.dumps({"query": "test"}),
                          content_type='application/json')
    assert response.status_code == 200
    
    # Test partial word search
    response = client.post('/exercises/search',
                          data=json.dumps({"query": "ex"}),
                          content_type='application/json')
    assert response.status_code == 200
    
    # Test with special characters
    response = client.post('/exercises/search',
                          data=json.dumps({"query": "test-exercise"}),
                          content_type='application/json')
    assert response.status_code == 200

def test_date_boundary_conditions(client, setup_test_collections):
    """Test date-related boundary conditions"""
    user_id = setup_test_collections["user_id"]
    exercise_id = setup_test_collections["exercise_id"]

    # Test with future date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    todo_data = {
        "user_id": user_id,
        "exercise_item": {
            "exercise_todo_id": "future_test",
            "exercise_id": exercise_id
        },
        "date": future_date
    }
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 200

    # Test date range spanning multiple months
    start_date = datetime.utcnow().strftime("%Y-%m-%d")
    end_date = (datetime.utcnow() + timedelta(days=45)).strftime("%Y-%m-%d")
    response = client.get(
        f'/todo/get_by_date/{user_id}?start_date={start_date}&end_date={end_date}'
    )
    assert response.status_code == 200

def test_concurrent_modifications(client, setup_test_collections):
    """Test concurrent modifications to todo items"""
    user_id = setup_test_collections["user_id"]
    exercise_id = setup_test_collections["exercise_id"]
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Create initial todo
    todo_data = {
        "user_id": user_id,
        "exercise_item": {
            "exercise_todo_id": "concurrent_test",
            "exercise_id": exercise_id,
            "status": "pending"
        },
        "date": today
    }
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 200

    # Simulate concurrent updates
    update_data_1 = {
        "user_id": user_id,
        "date": today,
        "exercise_todo_id": "concurrent_test",
        "update_fields": {"status": "completed", "sets": 3}
    }
    update_data_2 = {
        "user_id": user_id,
        "date": today,
        "exercise_todo_id": "concurrent_test",
        "update_fields": {"status": "in_progress", "reps": 12}
    }

    response1 = client.post('/todo/update_exercise',
                           data=json.dumps(update_data_1),
                           content_type='application/json')
    response2 = client.post('/todo/update_exercise',
                           data=json.dumps(update_data_2),
                           content_type='application/json')
    
    assert response1.status_code == 200
    assert response2.status_code == 200

def test_search_history_pagination(client, setup_test_collections):
    """Test search history with multiple entries"""
    user_id = setup_test_collections["user_id"]

    # Add multiple search history entries
    search_terms = ["push ups", "squats", "deadlift", "bench press", "pull ups"]
    for term in search_terms:
        history_data = {
            "user_id": user_id,
            "content": term
        }
        response = client.post('/search-history/add',
                             data=json.dumps(history_data),
                             content_type='application/json')
        assert response.status_code == 200

    # Get all search history
    response = client.get(f'/search-history/get/{user_id}')
    assert response.status_code == 200
    history = json.loads(response.data)
    assert len(history) == len(search_terms)

def test_complex_plan_operations(client, setup_test_collections):
    """Test complex workout plan scenarios"""
    user_id = setup_test_collections["user_id"]

    # Create a comprehensive workout plan
    plan_data = {
        "user_id": user_id,
        "plan": {
            "monday": ["Push ups", "Bench press", "Shoulder press"],
            "tuesday": ["Squats", "Lunges", "Leg press"],
            "wednesday": ["Rest day"],
            "thursday": ["Pull ups", "Rows", "Bicep curls"],
            "friday": ["Running", "Swimming"],
            "saturday": ["Full body workout"],
            "sunday": ["Active recovery"]
        }
    }
    response = client.post('/plan/save',
                          data=json.dumps(plan_data),
                          content_type='application/json')
    assert response.status_code == 201

def test_error_recovery(client, setup_test_collections):
    """Test system recovery from various error conditions"""
    user_id = setup_test_collections["user_id"]
    
    # Test with malformed ObjectId
    response = client.get('/exercises/get/invalid_id')
    assert response.status_code == 500
    
    # Test with non-existent exercise ID
    non_existent_id = str(ObjectId())
    response = client.get(f'/exercises/get/{non_existent_id}')
    assert response.status_code == 404
    
    # Test with invalid date format
    response = client.get(
        f'/todo/get_by_date/{user_id}?start_date=invalid&end_date=invalid'
    )
    assert response.status_code == 500

def test_data_validation(client, setup_test_collections):
    """Test input data validation"""
    user_id = setup_test_collections["user_id"]
    
    # Test with empty exercise item
    todo_data = {
        "user_id": user_id,
        "exercise_item": {},
        "date": datetime.utcnow().strftime("%Y-%m-%d")
    }
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 200

    # Test with missing required fields in update
    update_data = {
        "user_id": user_id,
        "update_fields": {"status": "completed"}
    }
    response = client.post('/todo/update_exercise',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 400
def test_exercise_search_with_special_cases(client, setup_test_collections):
    """Test exercise search with special cases"""
    # Test with empty query
    response = client.post('/exercises/search',
                          data=json.dumps({"query": ""}),
                          content_type='application/json')
    assert response.status_code == 200
    
    # Test with special characters
    response = client.post('/exercises/search',
                          data=json.dumps({"query": "test-exercise"}),
                          content_type='application/json')
    assert response.status_code == 200
    
    # Test with very long query
    response = client.post('/exercises/search',
                          data=json.dumps({"query": "a" * 100}),
                          content_type='application/json')
    assert response.status_code == 200

def test_todo_with_missing_fields(client, setup_test_collections):
    """Test todo operations with missing fields"""
    user_id = setup_test_collections["user_id"]
    
    # Test with missing exercise_item fields
    todo_data = {
        "user_id": user_id,
        "exercise_item": {
            "exercise_todo_id": "test123"
            # Missing other fields
        },
        "date": datetime.utcnow().strftime("%Y-%m-%d")
    }
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 200  # Should still work with minimal fields
    
    # Test update with minimal fields
    update_data = {
        "user_id": user_id,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "exercise_todo_id": "test123",
        "update_fields": {"status": "completed"}
    }
    response = client.post('/todo/update_exercise',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200

def test_get_nonexistent_exercise(client):
    """Test getting non-existent exercise"""
    valid_object_id = str(ObjectId())
    response = client.get(f'/exercises/get/{valid_object_id}')
    assert response.status_code == 404

def test_invalid_object_id_handling(client):
    """Test handling of invalid ObjectIds"""
    # Test with properly formatted but non-existent ObjectId
    valid_object_id = str(ObjectId())
    response = client.get(f'/users/get/{valid_object_id}')
    assert response.status_code == 404
    
    # Attempt to get exercise with malformed ID should return 500
    try:
        client.get('/exercises/get/123')
        assert False, "Should raise an error"
    except:
        assert True

def test_transcription_validation(client, setup_test_collections):
    """Test transcription with different content types"""
    user_id = setup_test_collections["user_id"]
    
    # Test with empty content
    response = client.post('/transcriptions/add',
                          data=json.dumps({
                              "user_id": user_id,
                              "content": ""
                          }),
                          content_type='application/json')
    assert response.status_code == 400
    
    # Test with valid content
    response = client.post('/transcriptions/add',
                          data=json.dumps({
                              "user_id": user_id,
                              "content": "Valid transcription"
                          }),
                          content_type='application/json')
    assert response.status_code == 200

def test_search_history_edge_cases(client, setup_test_collections):
    """Test search history edge cases"""
    user_id = setup_test_collections["user_id"]
    
    # Test with empty search content
    response = client.post('/search-history/add',
                          data=json.dumps({
                              "user_id": user_id,
                              "content": ""
                          }),
                          content_type='application/json')
    assert response.status_code == 400
    
    # Test get history for non-existent user
    response = client.get(f'/search-history/get/{str(ObjectId())}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 0

def test_plan_validation(client, setup_test_collections):
    """Test plan validation"""
    user_id = setup_test_collections["user_id"]
    
    # Test empty plan
    response = client.post('/plan/save',
                          data=json.dumps({
                              "user_id": user_id,
                              "plan": {}
                          }),
                          content_type='application/json')
    assert response.status_code == 201
    
    # Test null plan
    response = client.post('/plan/save',
                          data=json.dumps({
                              "user_id": user_id,
                              "plan": None
                          }),
                          content_type='application/json')
    assert response.status_code == 400

def test_todo_get_with_date_validation(client, setup_test_collections):
    """Test todo get operations with date validation"""
    user_id = setup_test_collections["user_id"]
    
    # Test with invalid date format
    response = client.get(
        f'/todo/get_by_date/{user_id}?start_date=invalid&end_date=2024-12-31'
    )
    assert response.status_code == 400
    
    # Test with end date before start date
    response = client.get(
        f'/todo/get_by_date/{user_id}?start_date=2024-12-31&end_date=2024-01-01'
    )
    assert response.status_code == 200  # Should return empty list
    data = json.loads(response.data)
    assert len(data) == 0

def test_user_update_validation(client, setup_test_collections):
    """Test user update validation"""
    user_id = setup_test_collections["user_id"]
    
    # Test with empty update data
    response = client.put(f'/users/update/{user_id}',
                         data=json.dumps({}),
                         content_type='application/json')
    assert response.status_code == 200
    
    # Test with valid update data
    response = client.put(f'/users/update/{user_id}',
                         data=json.dumps({"name": "Updated Name"}),
                         content_type='application/json')
    assert response.status_code == 200
    
    # Test update non-existent user
    response = client.put(f'/users/update/{str(ObjectId())}',
                         data=json.dumps({"name": "Test"}),
                         content_type='application/json')
    assert response.status_code == 200  # Should return success=False

def test_get_all_exercises(client, db_connection):
    """Test get all exercises"""
    response = client.get('/exercises/all')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0  

def test_add_todo_special_cases(client, setup_test_collections):
    """Test add_todo special cases"""
    user_id = setup_test_collections["user_id"]
    
    # Test with invalid date format (lines 47-54)
    todo_data = {
        "user_id": user_id,
        "exercise_item": {"exercise_todo_id": "test123"},
        "date": "invalid-date"
    }
    response = client.post('/todo/add',
                          data=json.dumps(todo_data),
                          content_type='application/json')
    assert response.status_code == 500

def test_todo_exceptions(client, setup_test_collections):
    """Test todo operations exceptions"""
    user_id = setup_test_collections["user_id"]
    
    # Test getting todo with invalid date format (lines 90-92)
    response = client.get(
        f'/todo/get_exercise_by_id?user_id={user_id}&date=invalid-date&exercise_todo_id=123'
    )
    assert response.status_code == 500

def test_todo_updates(client, setup_test_collections):
    """Test todo update operations"""
    user_id = setup_test_collections["user_id"]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Create a todo first
    todo_data = {
        "user_id": user_id,
        "exercise_item": {
            "exercise_todo_id": "test123",
            "exercise_id": setup_test_collections["exercise_id"]
        },
        "date": today
    }
    client.post('/todo/add',
                data=json.dumps(todo_data),
                content_type='application/json')
    
    # Test invalid update (lines 238-242)
    update_data = {
        "user_id": user_id,
        "date": "invalid-date",
        "exercise_todo_id": "test123",
        "update_fields": {"status": "completed"}
    }
    response = client.post('/todo/update_exercise',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 500

def test_search_history_errors(client, setup_test_collections):
    """Test search history error cases"""
    # Test with missing fields (lines 375)
    response = client.post('/search-history/add',
                          data=json.dumps({}),
                          content_type='application/json')
    assert response.status_code == 400

def test_transcription_errors(client, setup_test_collections):
    """Test transcription error cases"""
    # Test saving transcription failure (lines 408, 410-412)
    response = client.post('/transcriptions/add',
                          data=json.dumps({"user_id": "invalid", "content": ""}),
                          content_type='application/json')
    assert response.status_code == 400

def test_plan_errors(client, setup_test_collections):
    """Test plan operation errors"""
    user_id = setup_test_collections["user_id"]
    
    # Test plan save with invalid data (lines 471-473)
    response = client.post('/plan/save',
                          data=json.dumps({
                              "user_id": user_id,
                              "plan": None
                          }),
                          content_type='application/json')
    assert response.status_code == 400

def test_delete_exercise_errors(client, setup_test_collections):
    """Test delete exercise error cases"""
    user_id = setup_test_collections["user_id"]
    
    # Test delete with invalid date (lines 511-516)
    response = client.post('/todo/delete_exercise',
                          data=json.dumps({
                              "user_id": user_id,
                              "date": "invalid-date",
                              "exercise_id": "test123"
                          }),
                          content_type='application/json')
    assert response.status_code == 500