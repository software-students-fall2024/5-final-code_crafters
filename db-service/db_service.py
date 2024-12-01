# db_service.py
from flask import Flask, request, jsonify
import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import certifi
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
db = client["fitness_db"]

todo_collection = db["todo"]
exercises_collection = db["exercises"]
users_collection = db["users"]
search_history_collection = db["search_history"]
edit_transcription_collection = db["edit_transcription"]


def add_or_skip_todo(user_id):
    """
    插入新的 To-Do 数据之前，检查是否已存在相同的 user_id 和日期记录。
    如果存在，不插入；如果不存在，插入新记录。
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
        
        todo_collection.insert_one({
            "user_id": str(user_id),
            "date": datetime.utcnow(),
            "todo": []
        })
        
        print(f"DEBUG: New To-Do entry created for user {user_id} on {today_date}.")
        return {"message": "New To-Do entry created", "created": True}
    
    except Exception as e:
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
        print(f"user id is :", str(user_id))
        return jsonify({"user_id": str(user_id)}), 200

    except Exception as e:
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
    todo_data = todo_collection.find_one({"user_id": user_id})
    if todo_data:
        todo_data["_id"] = str(todo_data["_id"])
        
        for item in todo_data.get("todo", []):
            item["exercise_todo_id"] = int(item["exercise_todo_id"])
            item["exercise_id"] = str(item["exercise_id"])
            if "time" in item and isinstance(item["time"], datetime):
                item["time"] = item["time"].strftime("%Y-%m-%d")

        return jsonify(todo_data), 200

    return jsonify({"error": "Todo not found"}), 404

@app.route("/todo/add", methods=["POST"])
def add_todo():
    """Add a new todo item to user's list."""
    data = request.json
    user_id = data.get("user_id")
    exercise_item = data.get("exercise_item")

    if not user_id or not exercise_item:
        return jsonify({"error": "user_id and exercise_item are required"}), 400

    result = todo_collection.update_one(
        {"user_id": user_id},
        {"$push": {"todo": exercise_item}},
        upsert=True
    )
    return jsonify({"success": result.modified_count > 0}), 200

@app.route("/todo/delete/<user_id>/<int:exercise_todo_id>", methods=["DELETE"])
def delete_todo(user_id, exercise_todo_id):
    """Delete a todo item from user's list."""
    result = todo_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}}
    )
    return jsonify({"success": result.modified_count > 0}), 200

@app.route("/todo/edit/<user_id>/<int:exercise_todo_id>", methods=["PUT"])
def edit_todo_item(user_id, exercise_todo_id):
    """Edit an existing todo item."""
    data = request.json
    update_fields = data.get("update_fields", {})
    if not update_fields:
        return jsonify({"error": "No fields to update"}), 400

    update_query = {f"todo.$.{k}": v for k, v in update_fields.items()}

    result = todo_collection.update_one(
        {"user_id": user_id, "todo.exercise_todo_id": exercise_todo_id},
        {"$set": update_query}
    )
    return jsonify({"success": result.modified_count > 0}), 200

@app.route("/todo/get-item/<user_id>/<int:exercise_todo_id>", methods=["GET"])
def get_todo_item(user_id, exercise_todo_id):
    """Get a specific todo item."""
    todo = todo_collection.find_one({"user_id": user_id})
    if todo:
        for item in todo.get("todo", []):
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
    return jsonify([{**ex, "_id": str(ex["_id"])} for ex in exercises]), 200

@app.route("/exercises/get/<exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    """Get exercise details by ID."""
    exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})
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
    history = search_history_collection.find(
        {"user_id": user_id}
    ).sort("time", -1)
    return jsonify([{**h, "_id": str(h["_id"])} for h in history]), 200

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
    data = request.json
    try:
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": data}
        )
        return jsonify({"success": result.modified_count > 0}), 200
    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({"error": "Failed to update user"}), 500
@app.route("/exercises/all", methods=["GET"])
def get_all_exercises():
    exercises = list(exercises_collection.find({}, {"workout_name": 1, "_id": 1}))
    for exercise in exercises:
        exercise["_id"] = str(exercise["_id"])
    return jsonify(exercises), 200

@app.route("/todo/<user_id>", methods=["GET"])
def get_todos(user_id):
    """
    返回指定用户的 To-Do 数据
    """
    try:
        todos = list(todo_collection.find({"user_id": user_id}))
        for todo in todos:
            todo["_id"] = str(todo["_id"])
            if "todo" in todo:
                for item in todo["todo"]:
                    if "time" in item:
                        item["time"] = datetime.fromisoformat(item["time"]).strftime("%Y-%m-%d")
        return jsonify(todos), 200
    except Exception as e:
        print(f"ERROR: Failed to retrieve todos for user {user_id}: {e}")
        return jsonify({"error": "Failed to retrieve todos"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5112, debug=True)