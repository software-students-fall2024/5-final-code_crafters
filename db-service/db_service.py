"""Database service module for fitness application."""
import os
import copy
from datetime import datetime, timedelta
import certifi
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "fitness_db")

# Determine if using MongoDB Atlas URI, enable TLS if so
if mongo_uri.startswith("mongodb+srv://"):
    client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
else:
    client = MongoClient(mongo_uri)

db = client[db_name]

app = Flask(__name__)

todo_collection = db["todo"]
exercises_collection = db["exercises"]
users_collection = db["users"]
search_history_collection = db["search_history"]
edit_transcription_collection = db["edit_transcription"]
plan_collection = db["plans"]


def add_or_skip_todo(user_id):
    """
    Check if a To-Do entry for the given user and date already exists.
    If it exists, do not create a new one.
    If it does not exist, create a new empty entry.
    NOTE: 'date' is not defined in original code. We'll use today_date as fallback.
    """
    try:
        today_date = datetime.utcnow().strftime("%Y-%m-%d")
        existing_todo = todo_collection.find_one({
            "user_id": str(user_id),
            "date": {
                "$gte": datetime.strptime(today_date, "%Y-%m-%d"),
                "$lt": datetime.strptime(today_date, "%Y-%m-%d") + timedelta(days=1)
            }
        })

        if existing_todo:
            print(f"DEBUG: To-Do entry already exists for user {user_id} on {today_date}.")
            return {"message": "To-Do entry already exists", "exists": True}

        # Since 'date' is undefined, we'll just use today_date as the target_date.
        target_date = datetime.strptime(today_date, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        todo_collection.insert_one({
            "user_id": str(user_id),
            "date": target_date,
            "todo": []
        })

        print(f"DEBUG: New To-Do entry created for user {user_id} on {today_date}.")
        return {"message": "New To-Do entry created", "created": True}

    except Exception as e:  # Broad exception for unexpected errors
        print(f"ERROR: Failed to add or skip To-Do entry: {e}")
        return {"message": "An error occurred", "error": str(e)}


@app.route("/users/get/<user_id>", methods=["GET"])
def get_user(user_id):
    """Retrieve user information by ID."""
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404


@app.route("/users/create", methods=["POST"])
def create_user():
    """Create a new user account."""
    try:
        data = request.json
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({"message": "Username and password are required!"}), 400

        if users_collection.find_one({"username": username}):
            return jsonify({"message": "Username already exists!"}), 400

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        user_data = {"username": username, "password": hashed_password}

        user_id = users_collection.insert_one(user_data).inserted_id
        print(f"user id is : {str(user_id)}")
        return jsonify({"user_id": str(user_id)}), 200

    except Exception as e:  # Broad exception, internal server error
        print(f"Error creating user: {e}")
        return jsonify({"message": "Internal server error"}), 500


@app.route("/users/auth", methods=["POST"])
def authenticate_user():
    """Authenticate user login credentials."""
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = users_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        user["_id"] = str(user["_id"])
        add_or_skip_todo(user["_id"])
        return jsonify(user), 200
    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/todo/get/<string:user_id>", methods=["GET"])
def get_todo(user_id):
    """
    Get the user's To-Do data for today (compare by date only).
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        print(f"DEBUG: Today start: {today_start}, Today end: {today_end}")

        todo_data = todo_collection.find_one({
            "user_id": user_id,
            "date": {
                "$gte": today_start,
                "$lt": today_end
            }
        })

        if todo_data:
            print(f"INFO: Found To-Do data for user {user_id}: {todo_data}")

            todo_data = copy.deepcopy(todo_data)
            todo_data["_id"] = str(todo_data["_id"])
            for item in todo_data.get("todo", []):
                if "exercise_todo_id" in item:
                    item["exercise_todo_id"] = str(item["exercise_todo_id"])
                if "exercise_id" in item:
                    item["exercise_id"] = str(item["exercise_id"])
                if "time" in item and isinstance(item["time"], datetime):
                    item["time"] = item["time"].strftime("%Y-%m-%d")

            print(f"DEBUG: Final To-Do data for response: {todo_data}")
            return jsonify(todo_data), 200

        print(f"WARNING: No To-Do data found for user {user_id} on {today_start.date()}")
        return jsonify({"error": "Todo not found"}), 404

    except Exception as e:  # Broad exception for unexpected errors
        print(f"ERROR: Exception occurred while fetching To-Do data: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route("/todo/add", methods=["POST"])
def add_todo():
    """
    Add a new todo item to the user's list.
    If the record does not exist, create a new one.
    If it exists, update it.
    """
    data = request.json
    print(f"DEBUG: Received data: {data}")

    user_id = data.get("user_id")
    exercise_item = data.get("exercise_item")
    date_str = data.get("date")

    if not user_id or not exercise_item or not date_str:
        print("ERROR: Missing required fields - "
              f"user_id: {user_id}, exercise_item: {exercise_item}, "
              f"date: {date_str}")
        return jsonify({"error": "user_id, date, and exercise_item are required"}), 400

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        print(f"DEBUG: Parsed target_date: {target_date}")

        existing_todo = todo_collection.find_one({
            "user_id": user_id,
            "date": {
                "$gte": target_date,
                "$lt": target_date + timedelta(days=1)
            }
        })
        print(f"DEBUG: Existing todo record: {existing_todo}")

        if existing_todo:
            print(f"DEBUG: Updating existing todo for user_id: {user_id}, date: {target_date}")
            result = todo_collection.update_one(
                {"_id": existing_todo["_id"]},
                {"$push": {"todo": exercise_item}}
            )
            success = result.modified_count > 0
            message = ("New todo item added to existing entry"
                       if success else "Failed to add todo item")
            print(f"DEBUG: Update result - success: {success}, modified_count: {result.modified_count}")
        else:
            print(f"DEBUG: Creating new todo entry for user_id: {user_id}, date: {target_date}")
            new_todo = {
                "user_id": user_id,
                "date": target_date,
                "todo": [exercise_item]
            }
            result = todo_collection.insert_one(new_todo)
            success = result.inserted_id is not None
            message = ("New todo entry created"
                       if success else "Failed to create new todo entry")
            print(f"DEBUG: Insert result - success: {success}")

        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:  # Broad exception for unexpected errors
        print(f"ERROR: Failed to add todo item: {e}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500


@app.route("/todo/get_exercise_by_id", methods=["GET"])
def get_exercise_by_id():
    """
    Get a specific To-Do item for a user on a specific date.
    """
    user_id = request.args.get("user_id")
    date_str = request.args.get("date")
    exercise_todo_id = request.args.get("exercise_todo_id")

    if not user_id or not date_str or not exercise_todo_id:
        return jsonify({"error": "user_id, date, and exercise_todo_id are required"}), 400

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        todo_data = todo_collection.find_one({
            "user_id": user_id,
            "date": target_date,
            "todo.exercise_todo_id": exercise_todo_id
        })

        if todo_data:
            for item in todo_data.get("todo", []):
                if item.get("exercise_todo_id") == exercise_todo_id:
                    return jsonify(item), 200

        return jsonify({"error": "Exercise not found"}), 404

    except Exception as e:  # Broad exception for unexpected errors
        print(f"Error fetching exercise: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/todo/update_exercise", methods=["POST"])
def update_exercise():
    """
    Update fields for a user's specific To-Do item.
    """
    data = request.json
    user_id = data.get("user_id")
    date_str = data.get("date")
    exercise_todo_id = data.get("exercise_todo_id")
    update_fields = data.get("update_fields", {})

    if not user_id or not date_str or not exercise_todo_id or not update_fields:
        return jsonify({"error": "user_id, date, exercise_todo_id, and update_fields are required"}), 400

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = todo_collection.update_one(
            {
                "user_id": user_id,
                "date": target_date,
                "todo.exercise_todo_id": exercise_todo_id
            },
            {
                "$set": {f"todo.$.{key}": value for key, value in update_fields.items()}
            }
        )

        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Exercise updated successfully"}), 200
        return jsonify({"success": False, "message": "No matching exercise found"}), 404

    except Exception as e:  # Broad exception for unexpected errors
        print(f"Error updating exercise: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/todo/get-item/<user_id>/<int:exercise_todo_id>", methods=["GET"])
def get_todo_item(user_id, exercise_todo_id):
    """Get a specific todo item."""
    todo_data = todo_collection.find_one({"user_id": user_id})
    if todo_data:
        for item in todo_data.get("todo", []):
            if item.get("exercise_todo_id") == exercise_todo_id:
                return jsonify(item), 200
    return jsonify({"error": "Todo item not found"}), 404


@app.route("/exercises/search", methods=["POST"])
def search_exercises():
    """Search exercises based on query."""
    query = request.json.get("query", "")
    normalized_query = query.lower().replace(" ", "").replace("-", "")
    exercises = exercises_collection.find({
        "$expr": {
            "$regexMatch": {
                "input": {
                    "$toLower": {
                        "$replaceAll": {
                            "input": {
                                "$replaceAll": {
                                    "input": "$workout_name",
                                    "find": "-",
                                    "replacement": ""
                                }
                            },
                            "find": " ",
                            "replacement": ""
                        }
                    }
                },
                "regex": normalized_query,
                "options": "i"
            }
        }
    })
    # List comprehension line too long, break into multiple lines
    result_list = []
    for ex in exercises:
        ex["_id"] = str(ex["_id"])
        result_list.append(ex)
    return jsonify(result_list), 200


@app.route("/exercises/get/<exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    """Get exercise details by ID."""
    try:
        exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})
    except Exception as e:  # Broad exception if ObjectId conversion fails
        print(f"Error converting exercise_id to ObjectId: {e}")
        return jsonify({"error": "Exercise not found"}), 404

    if exercise:
        exercise["_id"] = str(exercise["_id"])
        return jsonify(exercise), 200
    return jsonify({"error": "Exercise not found"}), 404


@app.route("/search-history/add", methods=["POST"])
def add_search_history():
    """Add a search query to user's search history."""
    data = request.json
    user_id = data.get("user_id")
    content = data.get("content")

    if not user_id or not content:
        return jsonify({"error": "user_id and content are required"}), 400

    search_entry = {
        "user_id": user_id,
        "content": content,
        "time": datetime.utcnow()
    }
    result = search_history_collection.insert_one(search_entry)
    return jsonify({"success": bool(result.inserted_id)}), 200


@app.route("/search-history/get/<user_id>", methods=["GET"])
def get_search_history(user_id):
    """Retrieve user's search history."""
    history = search_history_collection.find({"user_id": user_id}).sort("time", -1)
    result_list = []
    for h in history:
        h["_id"] = str(h["_id"])
        result_list.append(h)
    return jsonify(result_list), 200


@app.route("/transcriptions/add", methods=["POST"])
def add_transcription():
    """Add a new transcription entry."""
    data = request.json
    user_id = data.get("user_id")
    content = data.get("content")

    if not user_id or not content:
        return jsonify({"error": "user_id and content are required"}), 400

    transcription_entry = {
        "user_id": user_id,
        "content": content,
        "time": datetime.utcnow()
    }
    result = edit_transcription_collection.insert_one(transcription_entry)
    if result.inserted_id:
        return jsonify({"id": str(result.inserted_id)}), 200
    return jsonify({"error": "Failed to save transcription"}), 500


@app.route("/users/update/<user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user information."""
    data = request.json
    try:
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": data}
        )
        return jsonify({"success": result.modified_count > 0}), 200
    except Exception as e:  # Broad exception for DB operation errors
        print(f"Error updating user: {e}")
        return jsonify({"error": "Failed to update user"}), 500


@app.route("/exercises/all", methods=["GET"])
def get_all_exercises():
    """Get all exercises."""
    exercises = list(exercises_collection.find({}, {"workout_name": 1, "_id": 1}))
    for exercise in exercises:
        exercise["_id"] = str(exercise["_id"])
    return jsonify(exercises), 200


@app.route("/todo/<user_id>", methods=["GET"])
def get_todos(user_id):
    """Return To-Do data for a specified user."""
    try:
        todos = list(todo_collection.find({"user_id": user_id}))
        for todo_data in todos:
            todo_data["_id"] = str(todo_data["_id"])
            if "todo" in todo_data:
                for item in todo_data["todo"]:
                    if "time" in item:
                        item["time"] = datetime.fromisoformat(
                            item["time"]
                        ).strftime("%Y-%m-%d")
        return jsonify(todos), 200
    except Exception as e:  # Broad exception for unexpected DB errors
        print(f"ERROR: Failed to retrieve todos for user {user_id}: {e}")
        return jsonify({"error": "Failed to retrieve todos"}), 500


@app.route("/todo/get_by_date/<string:user_id>", methods=["GET"])
def get_todo_by_date(user_id):
    """Get user's To-Do data within a specific date range."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        todos = list(todo_collection.find({
            "user_id": user_id,
            "date": {
                "$gte": start_date_dt,
                "$lt": end_date_dt + timedelta(days=1)
            }
        }))

        for todo_data in todos:
            todo_data["_id"] = str(todo_data["_id"])
            todo_data["date"] = todo_data["date"].strftime("%Y-%m-%d")

        return jsonify(todos), 200

    except Exception as e:  # Broad exception for unexpected errors
        print(f"ERROR: Failed to get todos by date for user {user_id}: {e}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500


@app.route('/plan/save', methods=['POST'])
def save_plan():
    """Save plan data to the database."""
    try:
        data = request.json
        user_id = data.get("user_id")
        plan_data = data.get("plan")

        if not user_id or not plan_data:
            return jsonify({"success": False, "message": "user_id and plan data are required"}), 400

        date_str = datetime.utcnow().strftime("%Y-%m-%d")

        plan_entry = {
            "user_id": user_id,
            "date": date_str,
            "plan": plan_data
        }
        plan_collection.insert_one(plan_entry)

        return jsonify({"success": True, "message": "Plan saved successfully"}), 201

    except Exception as e:  # Broad exception for DB insert errors
        print(f"Error saving plan: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/todo/delete_exercise', methods=['POST'])
def delete_exercise_from_date():
    """
    Delete the specified exercise_id from the database by user ID and date.
    """
    data = request.json
    user_id = data.get("user_id")
    date_str = data.get("date")
    exercise_id = data.get("exercise_id")

    if not user_id or not date_str or not exercise_id:
        print("DEBUG: Missing user_id, date, or exercise_id in request")
        return jsonify({"success": False,
                        "message": "user_id, date, and exercise_id are required"}), 400

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        print(f"DEBUG: Looking up todos for User ID: {user_id}, Date: {target_date}")
        user_todo = todo_collection.find_one({"user_id": user_id, "date": target_date})

        if not user_todo:
            print(f"DEBUG: No todos found for User ID: {user_id} on Date: {target_date}")
            return jsonify({"success": False,
                            "message": "No todos found for the specified date"}), 404

        print(f"DEBUG: Found todos: {user_todo['todo']}")
        result = todo_collection.update_one(
            {"user_id": user_id, "date": target_date},
            {"$pull": {"todo": {"exercise_todo_id": exercise_id}}}
        )

        if result.modified_count > 0:
            print(f"DEBUG: Successfully deleted exercise. "
                  f"User ID: {user_id}, Exercise ID: {exercise_id}")
            return jsonify({"success": True, "message": "Exercise deleted successfully"}), 200

        print("DEBUG: Exercise ID not found in user's todo list")
        return jsonify({"success": False, "message": "Exercise not found"}), 404

    except Exception as e:  # Broad exception for unexpected errors
        print(f"ERROR: Exception occurred while deleting exercise. Error: {str(e)}")
        return jsonify({"success": False,
                        "message": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5112, debug=True)
