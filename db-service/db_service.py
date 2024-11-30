from flask import Flask, request, jsonify
import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import certifi
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
db = client["fitness_db"]

# Collections
todo_collection = db["todo"]
exercises_collection = db["exercises"]
users_collection = db["users"]
search_history_collection = db["search_history"]
edit_transcription_collection = db["edit_transcription"]

# User Endpoints

@app.route("/users/get/<user_id>", methods=["GET"])
def get_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404

@app.route("/users/create", methods=["POST"])
def create_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required!"}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({"error": "Username already exists!"}), 400

    user_id = users_collection.insert_one(data).inserted_id
    todo_collection.insert_one(
        {"user_id": str(user_id), "date": datetime.utcnow(), "todo": []}
    )
    return jsonify({"user_id": str(user_id)}), 200

@app.route("/users/auth", methods=["POST"])
def authenticate_user():
    data = request.json
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    user = users_collection.find_one({"username": username})
    if user:
        user["_id"] = str(user["_id"])
        return jsonify(user), 200
    return jsonify({"error": "User not found"}), 404

# To-Do List Endpoints

@app.route("/todo/get/<user_id>", methods=["GET"])
def get_todo(user_id):
    todo = todo_collection.find_one({"user_id": user_id})
    if todo:
        todo["_id"] = str(todo["_id"])
        return jsonify(todo), 200
    return jsonify({"error": "Todo not found"}), 404

@app.route("/todo/add", methods=["POST"])
def add_todo():
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
    result = todo_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}}
    )
    return jsonify({"success": result.modified_count > 0}), 200

@app.route("/todo/edit/<user_id>/<int:exercise_todo_id>", methods=["PUT"])
def edit_todo_item(user_id, exercise_todo_id):
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
    todo = todo_collection.find_one({"user_id": user_id})
    if todo:
        for item in todo.get("todo", []):
            if item.get("exercise_todo_id") == exercise_todo_id:
                return jsonify(item), 200
    return jsonify({"error": "Todo item not found"}), 404

# Exercise Endpoints

@app.route("/exercises/search", methods=["POST"])
def search_exercises():
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
    exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})
    if exercise:
        exercise["_id"] = str(exercise["_id"])
        return jsonify(exercise), 200
    return jsonify({"error": "Exercise not found"}), 404

# Search History Endpoints

@app.route("/search-history/add", methods=["POST"])
def add_search_history():
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
    history = search_history_collection.find(
        {"user_id": user_id}
    ).sort("time", -1)
    return jsonify([{**h, "_id": str(h["_id"])} for h in history]), 200

# Transcription Endpoints

@app.route("/transcriptions/add", methods=["POST"])
def add_transcription():
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5112)
