# db_service.py
from flask import Flask, request, jsonify
import os
from datetime import datetime, timedelta
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
plan_collection = db["plans"]

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
        
        time = datetime.utcnow()
        target_date = datetime.strptime(date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        todo_collection.insert_one({
            "user_id": str(user_id),
            "date": target_date,
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
    """
    获取用户当天的 To-Do 数据 (仅比较年月日)
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        print(f"DEBUG: Today start: {today_start}, Today end: {today_end}")

        # 查询用户当天的 To-Do 数据
        todo_data = todo_collection.find_one({
            "user_id": user_id,
            "date": {
                "$gte": today_start,
                "$lt": today_end
            }
        })

        if todo_data:
            print(f"INFO: Found To-Do data for user {user_id}: {todo_data}")

            import copy
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

    except Exception as e:
        print(f"ERROR: Exception occurred while fetching To-Do data: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/todo/add", methods=["POST"])
def add_todo():
    """
    Add a new todo item to the user's list.
    如果记录不存在，直接创建新记录；如果存在，直接更新。
    """
    data = request.json
    #print(f"DEBUG: Received data: {data}")  

    user_id = data.get("user_id")
    exercise_item = data.get("exercise_item")
    date = data.get("date")  

    if not user_id or not exercise_item or not date:
        #print(f"ERROR: Missing required fields - user_id: {user_id}, exercise_item: {exercise_item}, date: {date}")
        return jsonify({"error": "user_id, date, and exercise_item are required"}), 400

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        #print(f"DEBUG: Parsed target_date: {target_date}")

        existing_todo = todo_collection.find_one({
            "user_id": user_id,
            "date": {
                "$gte": target_date,
                "$lt": target_date + timedelta(days=1)
            }
        })
        print(f"DEBUG: Existing todo record: {existing_todo}")

        if existing_todo:
            # 如果记录存在，更新 todo 列表
            print(f"DEBUG: Updating existing todo for user_id: {user_id}, date: {target_date}")
            result = todo_collection.update_one(
                {"_id": existing_todo["_id"]},
                {"$push": {"todo": exercise_item}}
            )
            success = result.modified_count > 0
            message = "New todo item added to existing entry" if success else "Failed to add todo item"
            print(f"DEBUG: Update result - success: {success}, modified_count: {result.modified_count}")
        else:
            # 如果记录不存在，创建新记录
            print(f"DEBUG: Creating new todo entry for user_id: {user_id}, date: {target_date}")
            new_todo = {
                "user_id": user_id,
                "date": target_date,
                "todo": [exercise_item]
            }
            result = todo_collection.insert_one(new_todo)
            success = result.inserted_id is not None
            message = "New todo entry created" if success else "Failed to create new todo entry"
            print(f"DEBUG: Insert result - success: {success}, inserted_id: {result.inserted_id if success else None}")

        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:
        print(f"ERROR: Failed to add todo item: {e}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500

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

@app.route("/todo/get_by_date/<string:user_id>", methods=["GET"])
def get_todo_by_date(user_id):
    """
    获取用户在特定日期范围内的 To-Do 数据。
    """
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)

        todos = list(todo_collection.find({
            "user_id": user_id,
            "date": {
                "$gte": start_date_dt,
                "$lt": end_date_dt + timedelta(days=1)
            }
        }))

        for todo in todos:
            todo["_id"] = str(todo["_id"])
            todo["date"] = todo["date"].strftime("%Y-%m-%d")

        return jsonify(todos), 200

    except Exception as e:
        print(f"ERROR: Failed to get todos by date for user {user_id}: {e}")
        return jsonify({"error": "An error occurred", "message": str(e)}), 500

@app.route('/plan/save', methods=['POST'])
def save_plan():
    """
    保存计划到数据库
    """
    try:
        data = request.json
        user_id = data.get("user_id")
        plan_data = data.get("plan")

        if not user_id or not plan_data:
            return jsonify({"success": False, "message": "user_id and plan data are required"}), 400

        date = datetime.utcnow().strftime("%Y-%m-%d")

        plan_entry = {
            "user_id": user_id,
            "date": date,  
            "plan": plan_data
        }
        plan_collection.insert_one(plan_entry)

        return jsonify({"success": True, "message": "Plan saved successfully"}), 201

    except Exception as e:
        print(f"Error saving plan: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/todo/delete_exercise', methods=['POST'])
def delete_exercise_from_date():
    """
    根据用户 ID 和日期从数据库中删除指定的 exercise_id
    """
    data = request.json
    user_id = data.get("user_id")  # 用户 ID
    date = data.get("date")  # 日期
    exercise_id = data.get("exercise_id")  # 待删除的 exercise_id

    # 检查必要参数
    if not user_id or not date or not exercise_id:
        print("DEBUG: Missing user_id, date, or exercise_id in request")
        return jsonify({"success": False, "message": "user_id, date, and exercise_id are required"}), 400

    try:
        # 转换日期格式为标准 UTC 日期
        target_date = datetime.strptime(date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)

        # 调试输出：尝试查找用户的 To-Do 项目
        print(f"DEBUG: Looking up todos for User ID: {user_id}, Date: {target_date}")

        # 查询数据库以获取指定日期的 To-Do 列表
        user_todo = todo_collection.find_one({"user_id": user_id, "date": target_date})

        if not user_todo:
            print(f"DEBUG: No todos found for User ID: {user_id} on Date: {target_date}")
            return jsonify({"success": False, "message": "No todos found for the specified date"}), 404

        # 调试输出：打印完整的 To-Do 列表
        print(f"DEBUG: Found todos: {user_todo['todo']}")

        # 删除匹配的 exercise_id
        result = todo_collection.update_one(
            {"user_id": user_id, "date": target_date},
            {"$pull": {"todo": {"exercise_todo_id": exercise_id}}}
        )

        # 检查是否删除成功
        if result.modified_count > 0:
            print(f"DEBUG: Successfully deleted exercise. User ID: {user_id}, Exercise ID: {exercise_id}")
            return jsonify({"success": True, "message": "Exercise deleted successfully"}), 200

        print(f"DEBUG: Exercise ID: {exercise_id} not found in User ID: {user_id}'s todo list for Date: {target_date}")
        return jsonify({"success": False, "message": "Exercise not found"}), 404

    except Exception as e:
        print(f"ERROR: Exception occurred while deleting exercise. Error: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5112, debug=True)