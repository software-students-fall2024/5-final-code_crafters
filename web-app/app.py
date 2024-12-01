# app.py - Main Flask Application
from flask import Flask, request, redirect, url_for, render_template, jsonify, session
from datetime import datetime, timedelta
import os
import re
import subprocess
import requests
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import BadRequest
from dotenv import load_dotenv
from zoneinfo import ZoneInfo


load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(13)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# URL of your db-service
#DB_SERVICE_URL = "http://db-service:5112/"
DB_SERVICE_URL = "http://localhost:5112/"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    """User class for Flask-Login authentication."""

    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

    @staticmethod
    def get(user_id):
        """Retrieve a User object from the db-service by user_id."""
        try:
            response = requests.get(f"{DB_SERVICE_URL}/users/get/{user_id}")
            if response.status_code == 200:
                user_data = response.json()
                return User(user_data["_id"], user_data["username"])
            return None
        except requests.RequestException as e:
            print(f"Error fetching user: {e}")
            return None

def get_user_by_id(user_id):
    """Retrieve user information via API."""
    try:
        response = requests.get(f"{DB_SERVICE_URL}/users/get/{user_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        print(f"Error retrieving user: {e}")
        return None

def update_user_by_id(user_id, update_fields):
    """Update user data via the db-service."""
    try:
        response = requests.put(
            f"{DB_SERVICE_URL}/users/update/{user_id}",
            json=update_fields
        )
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Error updating user: {e}")
        return False

def normalize_text(text: str) -> str:
    """Normalize text for search queries."""
    text = re.sub(r"[\s\-]", "", text)
    return text.lower()

def search_exercise(query: str):
    """Search for exercises using the db-service API."""
    try:
        response = requests.post(
            f"{DB_SERVICE_URL}/exercises/search",
            json={"query": query}
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException as e:
        print(f"Error searching exercises: {e}")
        return []

def get_exercise(exercise_id: str):
    """Retrieve exercise details from the db-service."""
    try:
        response = requests.get(f"{DB_SERVICE_URL}/exercises/get/{exercise_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException as e:
        print(f"Error getting exercise: {e}")
        return None

def get_all_exercises():
    """Retrieves all exercise names from the database via API."""
    try:
        response = requests.get(f"{DB_SERVICE_URL}/exercises/all")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error retrieving exercises: {e}")
        return []

def get_todo():
    """Retrieve the user's to-do list from the db-service."""
    try:
        response = requests.get(f"{DB_SERVICE_URL}/todo/get/{current_user.id}")
        print(f"DEBUG: Response status: {response.status_code}, Body: {response.text}")
        if response.status_code == 200:
            todo_data = response.json()
            return todo_data.get("todo", [])
        print(f"Error fetching todo: {response.status_code}, {response.text}")
        return [] 
    except requests.RequestException as e:
        print(f"Error getting todo: {e}")
        return []  

def get_today_todo():
    """Retrieves today's To-Do list for the logged-in user."""
    try:
        response = requests.get(f"{DB_SERVICE_URL}/todo/get/{current_user.id}")
        if response.status_code != 200:
            print(f"Error fetching todo: {response.status_code}, {response.text}")
            return []

        todo_list = response.json()
        if not todo_list or "todo" not in todo_list:
            return []
        
        eastern_time = datetime.now(ZoneInfo("America/New_York"))
        utc_time = eastern_time.astimezone(ZoneInfo("UTC"))
        today = utc_time.date()
        today_todo = []
        for item in todo_list["todo"]:
            if "time" in item:
                item_date = datetime.strptime(item["time"], "%Y-%m-%d").date()
                if item_date == today:
                    today_todo.append(item)
        return today_todo

    except Exception as e:
        print(f"Error retrieving today's To-Do list: {e}")
        return []

def delete_todo_api(exercise_todo_id: int):
    """Delete a to-do item via the db-service API."""
    try:
        response = requests.delete(
            f"{DB_SERVICE_URL}/todo/delete/{current_user.id}/{exercise_todo_id}"
        )
        return response.json().get("success", False)
    except requests.RequestException as e:
        print(f"Error deleting todo item: {e}")
        return False


def add_todo_api(exercise_id: str, working_time=None, reps=None, weight=None):
    """Add a to-do item via the db-service API."""
    exercise = get_exercise(exercise_id)
    if not exercise:
        return False
    
    eastern_time = datetime.now(ZoneInfo("America/New_York"))
    utc_time = eastern_time.astimezone(ZoneInfo("UTC"))
    
    exercise_item = {
        "exercise_todo_id": int(datetime.now().timestamp()),  # Unique ID
        "exercise_id": exercise_id,
        "workout_name": exercise["workout_name"],
        "working_time": working_time,
        "reps": reps,
        "weight": weight,
        "time": utc_time.isoformat()
    }
    data = {
        "user_id": current_user.id,
        "exercise_item": exercise_item
    }
    try:
        response = requests.post(f"{DB_SERVICE_URL}/todo/add", json=data)
        return response.json().get("success", False)
    except requests.RequestException as e:
        print(f"Error adding todo item: {e}")
        return False

def edit_exercise_api(exercise_todo_id, working_time, weight, reps):
    """Edit a to-do item via the db-service API."""
    update_fields = {}
    if working_time is not None:
        update_fields["working_time"] = working_time
    if weight is not None:
        update_fields["weight"] = weight
    if reps is not None:
        update_fields["reps"] = reps

    if not update_fields:
        return False

    data = {
        "update_fields": update_fields
    }
    try:
        response = requests.put(
            f"{DB_SERVICE_URL}/todo/edit/{current_user.id}/{exercise_todo_id}",
            json=data
        )
        return response.json().get("success", False)
    except requests.RequestException as e:
        print(f"Error editing todo item: {e}")
        return False

def add_search_history_api(content):
    """Add a search query to the search history via the db-service API."""
    data = {
        "user_id": current_user.id,
        "content": content
    }
    try:
        response = requests.post(f"{DB_SERVICE_URL}/search-history/add", json=data)
        return response.json().get("success", False)
    except requests.RequestException as e:
        print(f"Error adding search history: {e}")
        return False

def get_search_history():
    """Retrieve the user's search history via the db-service API."""
    try:
        response = requests.get(f"{DB_SERVICE_URL}/search-history/get/{current_user.id}")
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException as e:
        print(f"Error getting search history: {e}")
        return []

def get_exercise_in_todo(exercise_todo_id: int):
    """Retrieve a specific exercise from the user's to-do list."""
    exercises = get_todo()
    for item in exercises:
        if item.get("exercise_todo_id") == int(exercise_todo_id):
            return item
    return None

def get_instruction(exercise_id: str):
    """Retrieve exercise instructions from the db-service."""
    exercise = get_exercise(exercise_id)
    if exercise:
        return {
            "workout_name": exercise.get("workout_name", "Unknown Workout"),
            "instruction": exercise.get("instruction", "No instructions for this exercise."),
        }
    return {"error": f"Exercise with ID {exercise_id} not found."}

def parse_voice_command(transcription):
    """Parse voice command transcription to extract parameters."""
    time_match = re.search(r"\b(\d+)\s*minutes?\b", transcription, re.IGNORECASE)
    time_params = int(time_match.group(1)) if time_match else None

    group_match = re.search(r"\b(\d+)\s*groups?\b", transcription, re.IGNORECASE)
    groups = int(group_match.group(1)) if group_match else None

    weight_match = re.search(
        r"\b(\d+)\s*(kg|kgs|kilogram|kilograms)?\b", transcription, re.IGNORECASE
    )
    weight = int(weight_match.group(1)) if weight_match else None

    return {"time": time_params, "groups": groups, "weight": weight}

def insert_transcription_entry_api(content):
    """Insert a transcription entry via the db-service API."""
    data = {
        "user_id": current_user.id,
        "content": content
    }
    try:
        response = requests.post(f"{DB_SERVICE_URL}/transcriptions/add", json=data)
        if response.status_code == 200:
            return response.json().get("id", None)
        return None
    except requests.RequestException as e:
        print(f"Error inserting transcription entry: {e}")
        return None

@login_manager.user_loader
def load_user(user_id):
    """Loads the user information from the db-service by their user ID."""
    return User.get(user_id)

@app.route("/")
def home():
    """Redirects the user to the To-Do page when accessing the root URL."""
    return redirect(url_for("todo"))

@app.route("/register", methods=["GET"])
def signup_page():
    """Displays the registration page for new users to sign up."""
    return render_template("signup.html")

@app.route("/login", methods=["GET"])
def login_page():
    """Displays the login page for the user to enter credentials."""
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    """Handles user registration and logs in the user upon success."""
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required!"}), 400

    try:
        response = requests.post(
            f"{DB_SERVICE_URL}/users/create",
            json={"username": username, "password": password}
        )

        if response.status_code == 200:
            user_data = response.json()
            if "user_id" in user_data:
                user = User(
                    user_id=user_data["user_id"],
                    username=username
                )
                login_user(user)  

                return jsonify({"success": True, "message": "Register successful! Please Login now.", "redirect_url": "/todo"}), 200

        return jsonify({"success": False, "message": response.json().get("message", "Registration failed!")}), 400

    except requests.RequestException as e:
        print(f"Error communicating with database service: {e}")
        return jsonify({"success": False, "message": "Error communicating with database service"}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        username = request.form.get("username")
        password = request.form.get("password")
        print(f"DEBUG: Received username={username}, password={password}")

        response = requests.post(
            f"{DB_SERVICE_URL}/users/auth",
            json={"username": username, "password": password}
        )
        print(f"DEBUG: db-service response: {response.status_code}, {response.json()}")

        if response.status_code == 200:
            user_data = response.json()
            user = User(
                user_id=user_data["_id"], 
                username=user_data["username"]
            )
            login_user(user)
            return jsonify({"message": "Login successful!", "success": True}), 200
        else:
            print("DEBUG: db-service returned non-200 status code")
            return jsonify({"message": "Invalid username or password!", "success": False}), 401

    except Exception as e:
        import traceback
        print(f"DEBUG: Exception occurred: {e}")
        print(traceback.format_exc())  
        return jsonify({"message": "Login failed due to internal error!"}), 500

@app.route("/logout")
@login_required
def logout():
    """Logs out the currently authenticated user and redirects them to the login page."""
    logout_user()
    return redirect(url_for("login"))

@app.route("/todo")
@login_required
def todo():
    """Displays the user's To-Do list with all the exercises and their details."""
    exercises = get_todo()
    return render_template("todo.html", exercises=exercises)

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Provides search functionality for the user to find exercises."""
    if request.method == "POST":
        query = request.form.get("query")
        if not query:
            return jsonify({"message": "Search content cannot be empty."}), 400
        results = search_exercise(query)
        if len(results) == 0:
            return jsonify({"message": "Exercise was not found."}), 404

        session["results"] = results
        add_search_history_api(query)
        return redirect(url_for("add"))

    # For GET request, show previous searches or suggestions
    history = get_search_history()
    exercises = []
    for entry in history:
        exercises.extend(search_exercise(entry['content']))
    return render_template("search.html", exercises=exercises)

@app.route("/add")
@login_required
def add():
    """Displays a page where the user can add exercises to the To-Do list from search results."""
    exercises = session.get("results", [])
    return render_template("add.html", exercises=exercises, exercises_length=len(exercises))

@app.route("/add_exercise", methods=["POST"])
@login_required
def add_exercise():
    """Adds a new exercise to the user's To-Do list based on its unique ID provided in the request."""
    exercise_id = request.args.get("exercise_id")

    if not exercise_id:
        print("No exercise ID provided")
        return jsonify({"message": "Exercise ID is required"}), 400

    success = add_todo_api(exercise_id)

    if success:
        print(f"Successfully added exercise with ID: {exercise_id}")
        return jsonify({"message": "Added successfully"}), 200
    print(f"Failed to add exercise with ID: {exercise_id}")
    return jsonify({"message": "Failed to add"}), 400

@app.route("/delete_exercise")
@login_required
def delete_exercise():
    """Renders a page to allow the user to select and delete exercises from the To-Do list."""
    exercises = get_todo()
    return render_template("delete.html", exercises=exercises)

@app.route("/delete_exercise/<int:exercise_todo_id>", methods=["DELETE"])
@login_required
def delete_exercise_id(exercise_todo_id):
    """Deletes a specific exercise from the user's To-Do list using its ID."""
    success = delete_todo_api(exercise_todo_id)
    if success:
        return jsonify({"message": "Deleted successfully"}), 204
    return jsonify({"message": "Failed to delete"}), 404

@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    """Enables the user to edit an exercise's details in the To-Do list."""
    exercise_todo_id = request.args.get("exercise_todo_id")
    exercise_in_todo = get_exercise_in_todo(exercise_todo_id)

    if not exercise_in_todo:
        return jsonify({"message": "Exercise not found in your To-Do list"}), 404

    if request.method == "POST":
        working_time = request.form.get("working_time")
        weight = request.form.get("weight")
        reps = request.form.get("reps")
        success = edit_exercise_api(exercise_todo_id, working_time, weight, reps)
        if success:
            return jsonify({"message": "Edited successfully"}), 200
        return jsonify({"message": "Failed to edit"}), 400

    return render_template(
        "edit.html", exercise_todo_id=exercise_todo_id, exercise=exercise_in_todo
    )

@app.route("/instructions", methods=["GET"])
def instructions():
    """Fetches and displays detailed instructions for a specific exercise."""
    exercise_id = request.args.get("exercise_id")
    exercise = get_instruction(exercise_id)

    if "error" in exercise:
        return jsonify({"message": exercise["error"]}), 404

    return render_template("instructions.html", exercise=exercise)

@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    """Handles audio uploads and returns the transcribed text."""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio = request.files["audio"]
    original_file_path = os.path.join(app.config["UPLOAD_FOLDER"], audio.filename)
    audio.save(original_file_path)

    wav_file_path = os.path.splitext(original_file_path)[0] + "_converted.wav"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                original_file_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_file_path,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error converting audio to WAV: {e}")
        return jsonify({"error": "Failed to convert audio file"}), 500

    transcription = call_speech_to_text_service(wav_file_path)
    if not transcription:
        return jsonify({"error": "Failed to transcribe audio"}), 500
    return jsonify({"transcription": transcription})

def call_speech_to_text_service(file_path):
    """Sends the uploaded audio file to a remote speech-to-text service for transcription."""
    url = "http://machine-learning-client:8080/transcribe"
    data = {"audio_file": file_path}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("transcript", "No transcription returned")
    except requests.RequestException as e:
        print(f"Error communicating with the Speech-to-Text service: {e}")
        return "Error during transcription"

@app.route("/process-audio", methods=["POST"])
@login_required
def process_audio():
    """Processes uploaded audio to extract parameters and updates the exercise."""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio = request.files["audio"]
    original_file_path = os.path.join(app.config["UPLOAD_FOLDER"], audio.filename)
    audio.save(original_file_path)

    wav_file_path = os.path.splitext(original_file_path)[0] + "_converted.wav"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                original_file_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                wav_file_path,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error converting audio to WAV: {e}")
        return jsonify({"error": "Failed to convert audio file"}), 500

    transcription = call_speech_to_text_service(wav_file_path)
    if not transcription:
        return jsonify({"error": "Failed to transcribe audio"}), 500

    parsed_data = parse_voice_command(transcription)
    if not parsed_data:
        return (
            jsonify(
                {
                    "error": "Failed to parse transcription",
                    "transcription": transcription,
                }
            ),
            400,
        )

    working_time = f"{parsed_data['time']}:00" if parsed_data["time"] else None
    groups = parsed_data.get("groups")
    weight = parsed_data.get("weight")

    exercise_todo_id = request.args.get("exercise_todo_id")
    if not exercise_todo_id:
        return jsonify({"error": "Exercise To-Do ID is required"}), 400

    success = edit_exercise_api(exercise_todo_id, working_time, weight, groups)
    if not success:
        return jsonify({"error": "Failed to update exercise"}), 500

    return (
        jsonify(
            {
                "message": "Exercise updated successfully",
                "time": parsed_data["time"],
                "groups": groups,
                "weight": weight,
            }
        ),
        200,
    )

@app.route("/upload-transcription", methods=["POST"])
@login_required
def upload_transcription():
    """Processes uploaded transcription data and saves it to the db-service."""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type. JSON expected"}), 400

        data = request.get_json()
        transcription_content = data.get("content")

        if not transcription_content:
            return jsonify({"error": "Content is required"}), 400

        inserted_id = insert_transcription_entry_api(transcription_content)

        if inserted_id:
            return (
                jsonify(
                    {
                        "message": "Transcription saved successfully!",
                        "id": str(inserted_id),
                    }
                ),
                200,
            )
        return jsonify({"error": "Failed to save transcription"}), 500
    except BadRequest as e:
        return jsonify({"error": str(e)}), 400


week_plan_data = [
    {"day": "Mon", "task": "Shoulder"},
    {"day": "Tue", "task": "Leg"},
    {"day": "Wed", "task": "Arm"},
    {"day": "Thu", "task": "Chest"},
    {"day": "Fri", "task": "Arm"},
    {"day": "Sat", "task": "Shoulder"},
    {"day": "Sun", "task": "Cardio"},
]

month_plan_data = [
    {"week": "1", "description": "Active Recovery"},
    {"week": "2", "description": "Upper Body Strength Training"},
    {"week": "3", "description": "Cardio + Core Strength Training"},
    {"week": "4", "description": "High-intensity Training"},
]


@app.route('/plan', methods=['GET'])
@login_required
def get_plan():
    """Render the main plan template."""
    current_date = datetime.now(ZoneInfo("America/New_York"))
    return render_template('plan.html', current_date=current_date)


@app.route('/plan/week', methods=['GET'])
@login_required
def get_week_plan():
    """Fetch week plan data."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required!"}), 400

    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Get user's todo list via API call
    response = requests.get(f"{DB_SERVICE_URL}/todo/get/{current_user.id}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to get todo list"}), 500

    user_todo = response.json()
    if not user_todo or "todo" not in user_todo:
        return jsonify({})

    todos = user_todo["todo"]

    week_plan_data = {}
    current_date = start_date_dt
    while current_date <= end_date_dt:
        day_tasks = [
            task["workout_name"]
            for task in todos
            if "time" in task and datetime.strptime(task["time"], "%Y-%m-%d") == current_date.date()
        ][:3]
        week_plan_data[current_date.strftime("%Y-%m-%d")] = day_tasks
        current_date += timedelta(days=1)

    return jsonify(week_plan_data)

@app.route('/plan/month', methods=['GET'])
@login_required
def get_month_plan():
    """Fetch month plan data."""
    month = request.args.get("month")

    if not month:
        return jsonify({"error": "month is required!"}), 400

    start_of_month = datetime.strptime(month + "-01", "%Y-%m-%d")
    next_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(days=1)

    response = requests.get(f"{DB_SERVICE_URL}/todo/get/{current_user.id}")
    if response.status_code != 200:
        return jsonify({"error": "Failed to get todo list"}), 500

    user_todo = response.json()
    if not user_todo or "todo" not in user_todo:
        return jsonify({})

    todos = user_todo["todo"]
    month_plan_data = {}
    for week_start in range(0, (end_of_month - start_of_month).days + 1, 7):
        week_start_date = start_of_month + timedelta(days=week_start)
        week_end_date = week_start_date + timedelta(days=6)

        week_tasks = [
            task["workout_name"]
            for task in todos
            if "time" in task and week_start_date.date() <= datetime.strptime(task["time"], "%Y-%m-%d").date() <= week_end_date.date()
        ]

        if week_tasks:
            most_frequent_workout = max(set(week_tasks), key=week_tasks.count)
            month_plan_data[week_start_date.strftime("%Y-%m-%d")] = most_frequent_workout
        else:
            month_plan_data[week_start_date.strftime("%Y-%m-%d")] = None

    return jsonify(month_plan_data)

@app.route('/user')
@login_required
def user_profile():
    """Displays the user's profile information."""
    response = requests.get(f"{DB_SERVICE_URL}/users/get/{current_user.id}")
    if response.status_code != 200:
        return jsonify({"error": "User not found"}), 404

    user_data = response.json()
    return render_template('user.html', user=user_data)


@app.route('/update', methods=["GET", "POST"])
@login_required
def update_profile():
    if request.method == "POST":
        # Handle profile update logic here
        return redirect(url_for('user_profile'))
    return render_template('update.html')

@app.route('/save-profile', methods=['POST'])
@login_required
def save_profile():
    """Update the current user's profile."""
    data = request.json

    if not data:
        return jsonify({"error": "Invalid input"}), 400

    user_id = current_user.id

    allowed_fields = [
        "name",
        "sex",
        "height",
        "weight",
        "goal_weight",
        "fat_rate",
        "goal_fat_rate",
        "additional_notes",
    ]
    update_fields = {key: value for key, value in data.items() if key in allowed_fields}

    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    success = update_user_by_id(user_id, update_fields)

    if not success:
        return jsonify({"error": "Failed to update profile"}), 500

    return jsonify({"message": "User profile updated successfully.", "updated_data": update_fields}), 200
@app.route('/api/generate-weekly-plan', methods=['POST'])
@login_required
def generate_weekly_plan():
    """Generate a weekly plan based on the current user's data."""
    try:
        user_id = current_user.id

        response = requests.get(f"{DB_SERVICE_URL}/users/get/{user_id}")
        if response.status_code != 200:
            return jsonify({"success": False, "message": "User not found"}), 404

        user = response.json()

        response = requests.get(f"{DB_SERVICE_URL}/exercises/all")
        if response.status_code != 200:
            return jsonify({"success": False, "message": "Failed to retrieve exercises"}), 500

        all_exercises = response.json()
        all_workouts = [exercise["workout_name"] for exercise in all_exercises if "workout_name" in exercise]

        user_info = {
            "workout": all_workouts,
            "user_id": str(user_id),
            "sex": user.get("sex"),
            "height": user.get("height"),
            "weight": user.get("weight"),
            "goal_weight": user.get("goal_weight"),
            "fat_rate": user.get("fat_rate"),
            "goal_fat_rate": user.get("goal_fat_rate"),
            "additional_note": user.get("additional_note", ""),
        }

        response = requests.post("http://machine-learning-client:8080/plan", json=user_info, timeout=10)

        if response.status_code == 200:
            ml_response = response.json()
            return jsonify({"success": True, "plan": ml_response}), 200
        else:
            return jsonify({"success": False, "message": "Failed to generate plan"}), 500

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with ML Client: {e}")
        return jsonify({"success": False, "message": "Error communicating with ML Client"}), 500

    except Exception as e:
        print(f"Error generating plan: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

@app.route("/api/workout-data", methods=["GET"])
@login_required
def get_workout_data():
    """
    获取用户的 To-Do 数据并按日期统计
    返回每一天的任务数量
    """
    try:
        user_id = current_user.id
        print(f"DEBUG: Current user ID: {user_id}")

        # 调用 db-service 获取用户 To-Do 数据
        response = requests.get(f"{DB_SERVICE_URL}/todo/{user_id}")
        if response.status_code != 200:
            print(f"ERROR: Failed to fetch todos, status: {response.status_code}")
            return jsonify({"error": "Failed to retrieve workout data"}), 500

        todos = response.json()
        print(f"DEBUG: Received todos from db-service: {todos}")

        # 统计每日任务数量
        workout_data = {}
        for todo in todos:
            for item in todo.get("todo", []):
                date = item.get("time")  # 使用转换后的 time 字段
                if date:
                    if date not in workout_data:
                        workout_data[date] = 0
                    workout_data[date] += 1

        print(f"DEBUG: Final workout data: {workout_data}")
        return jsonify(workout_data)

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Communication with db-service failed: {e}")
        return jsonify({"error": "Failed to retrieve workout data"}), 500
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return jsonify({"error": "Failed to retrieve workout data"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)