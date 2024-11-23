"""
This module implements a Flask web application for a fitness tracker, including user authentication,
exercise management, and integration with a speech-to-text service for voice commands.
"""

import os
import re
import subprocess
from datetime import datetime

from flask import Flask, request, redirect, url_for, render_template, jsonify, session
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from bson import ObjectId
import certifi
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
import requests

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")

app = Flask(__name__)
app.secret_key = os.urandom(13)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())

try:
    client.admin.command("ping")
    print("Successfully connected to MongoDB!")
except ConnectionFailure as e:
    print(f"Failed to connect to MongoDB: {e}")

db = client["fitness_db"]
todo_collection = db["todo"]
exercises_collection = db["exercises"]
users_collection = db["users"]
search_history_collection = db["search_history"]
edit_transcription_collection = db["edit_transcription"]

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    """User class for Flask-Login authentication."""

    def __init__(self, user_id, username, password):
        self.id = user_id
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        """Retrieve a User object from the database by user_id."""
        user_data = users_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(
                str(user_data["_id"]), user_data["username"], user_data["password"]
            )
        return None


def normalize_text(text: str) -> str:
    """
    Takes a string as input and removes all spaces and hyphens.
    Converts the result to lowercase for consistent matching and searching.
    """
    text = re.sub(r"[\s\-]", "", text)
    return text.lower()


def search_exercise(query: str):
    """
    Accepts a search query from the user.
    Searches the database for exercise names matching the query,
    ignoring case, spaces, and hyphens.
    """
    normalized_query = normalize_text(query)

    exercises = exercises_collection.find(
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
                    "regex": normalized_query,
                    "options": "i",
                }
            }
        }
    )

    exercises_list = list(exercises)
    return exercises_list


def search_exercise_rigid(query: str):
    """
    Accepts a strict search query from the user.
    Performs a rigid match for exercise names in the database,
    ignoring case, spaces, and hyphens.
    """
    normalized_query = normalize_text(query)

    exercises = exercises_collection.find(
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
                    normalized_query,
                ]
            }
        }
    )

    exercises_list = list(exercises)
    return exercises_list


def get_exercise(exercise_id: str):
    """
    Retrieves the exercise record from the database that corresponds
    to the provided exercise ID.
    """
    return exercises_collection.find_one({"_id": ObjectId(exercise_id)})


def get_todo():
    """
    Retrieves the current To-Do list for the logged-in user,
    including all pending exercise items.
    """
    todo_list = todo_collection.find_one({"user_id": current_user.id})
    if todo_list and "todo" in todo_list:
        return todo_list["todo"]
    return []


def delete_todo(exercise_todo_id: int):
    """
    Removes a specific exercise from the user's To-Do list by its ID.
    Returns True if successful, False otherwise.
    """
    result = todo_collection.update_one(
        {"user_id": current_user.id},
        {"$pull": {"todo": {"exercise_todo_id": exercise_todo_id}}},
    )
    return result.modified_count > 0


def add_todo(exercise_id: str, working_time=None, reps=None, weight=None):
    """
    Adds a new exercise to the user's To-Do list.
    Optional parameters include working time, repetitions, and weight.
    """
    exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})

    if exercise:
        user_todo = todo_collection.find_one({"user_id": current_user.id})

        if user_todo and "todo" in user_todo:
            next_exercise_todo_id = (
                max(
                    (item.get("exercise_todo_id", 999) for item in user_todo["todo"]),
                    default=999,
                )
                + 1
            )
        else:
            next_exercise_todo_id = 1000

        exercise_item = {
            "exercise_todo_id": next_exercise_todo_id,
            "exercise_id": exercise["_id"],
            "workout_name": exercise["workout_name"],
            "working_time": working_time,
            "reps": reps,
            "weight": weight,
        }

        if user_todo:
            result = todo_collection.update_one(
                {"user_id": current_user.id}, {"$push": {"todo": exercise_item}}
            )
            success = result.modified_count > 0
        else:
            result = todo_collection.insert_one(
                {"user_id": current_user.id, "todo": [exercise_item]}
            )
            success = result.inserted_id is not None

        return success
    return False


def edit_exercise(exercise_todo_id, working_time, weight, reps):
    """
    Updates a specific exercise in the user's To-Do list
    with new working time, weight, and repetitions.
    """
    exercise_todo_id = int(exercise_todo_id)
    update_fields = {}

    if working_time is not None:
        update_fields["todo.$.working_time"] = working_time
    if reps is not None:
        update_fields["todo.$.reps"] = reps
    if weight is not None:
        update_fields["todo.$.weight"] = weight

    if not update_fields:
        return False

    result = todo_collection.update_one(
        {"user_id": current_user.id, "todo.exercise_todo_id": exercise_todo_id},
        {"$set": update_fields},
    )

    return result.matched_count > 0


def add_search_history(content):
    """
    Logs a search query made by the user into the search history database.
    Associates the search with the current user and records the timestamp.
    """
    search_entry = {
        "user_id": current_user.id,
        "content": content,
        "time": datetime.utcnow(),
    }
    search_history_collection.insert_one(search_entry)


def insert_transcription_entry(user_id, content):
    """
    Inserts a new transcription record into the edit_transcription_collection.
    """
    edit_transcription_entry = {
        "user_id": user_id,
        "content": content,
        "time": datetime.utcnow(),
    }
    result = edit_transcription_collection.insert_one(edit_transcription_entry)
    return result.inserted_id if result.inserted_id else None


def get_search_history():
    """
    Retrieves the search history of the currently logged-in user,
    sorted by the most recent searches.
    """
    results = search_history_collection.find(
        {"user_id": current_user.id}, {"_id": 0, "user_id": 1, "content": 1, "time": 1}
    ).sort("time", -1)

    history = list(results)
    return history


def get_exercise_in_todo(exercise_todo_id: int):
    """
    Finds a specific exercise in the user's To-Do list
    by its unique To-Do ID. Returns the exercise details if found.
    """
    todo_item = todo_collection.find_one({"user_id": current_user.id})

    if not todo_item:
        return None

    for item in todo_item.get("todo", []):
        if item.get("exercise_todo_id") == int(exercise_todo_id):
            return item

    return None


def get_instruction(exercise_id: str):
    """
    Retrieves the instruction and workout name for the exercise with the given ID.
    Returns a message if the exercise or instructions are not found.
    """
    exercise = exercises_collection.find_one(
        {"_id": ObjectId(exercise_id)}, {"instruction": 1, "workout_name": 1}
    )

    if exercise:
        return {
            "workout_name": exercise.get("workout_name", "Unknown Workout"),
            "instruction": exercise.get(
                "instruction", "No instructions for this exercise."
            ),
        }
    return {"error": f"Exercise with ID {exercise_id} not found."}


def get_matching_exercises_from_history():
    """
    Fetches matching exercises from the user's search history.
    Compares the history entries with rigid matches in the exercises collection.
    """
    history = get_search_history()
    content_names = [entry["content"] for entry in history]

    matching_exercises_list = []
    for name in content_names:
        matching_exercises = search_exercise_rigid(name)
        matching_exercises_list.extend(matching_exercises)

    return matching_exercises_list


@app.route("/")
def home():
    """
    Redirects the user to the To-Do page when accessing the root URL.
    """
    return redirect(url_for("todo"))


@login_manager.user_loader
def load_user(user_id):
    """
    Loads the user information from the database by their user ID.
    Returns a User object or None if the user is not found.
    """
    return User.get(user_id)


@app.route("/register", methods=["POST"])
def register():
    """
    Handles user registration. Accepts username and password, checks for duplicates,
    and stores the hashed password and initial To-Do list in the database.
    """
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password are required!"}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({"message": "Username already exists!"}), 400

    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

    user_id = users_collection.insert_one(
        {"username": username, "password": hashed_password}
    ).inserted_id

    todo_collection.insert_one(
        {"user_id": str(user_id), "date": datetime.utcnow(), "todo": []}
    )

    return (
        jsonify(
            {"message": "Registration successful! Please log in.", "success": True}
        ),
        200,
    )


@app.route("/login", methods=["GET"])
def login_page():
    """
    Displays the login page for the user to enter credentials.
    """
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def signup_page():
    """
    Displays the registration page for new users to sign up.
    """
    return render_template("signup.html")


@app.route("/login", methods=["POST"])
def login():
    """
    Authenticates the user by verifying the username and password.
    Logs in the user and starts a session if the credentials are valid.
    """
    username = request.form.get("username")
    password = request.form.get("password")

    user_data = users_collection.find_one({"username": username})

    if user_data and check_password_hash(user_data["password"], password):
        user = User(str(user_data["_id"]), user_data["username"], user_data["password"])
        login_user(user)
        return jsonify({"message": "Login successful!", "success": True}), 200
    return jsonify({"message": "Invalid username or password!", "success": False}), 401


@app.route("/logout")
@login_required
def logout():
    """
    Logs out the currently authenticated user and redirects them to the login page.
    """
    logout_user()
    return redirect(url_for("login"))


@app.route("/search", methods=["POST", "GET"])
@login_required
def search():
    """
    Provides search functionality for the user to find exercises.
    Supports both new search queries and suggestions from search history.
    """
    if request.method == "POST":
        query = request.form.get("query")
        if not query:
            return jsonify({"message": "Search content cannot be empty."}), 400
        results = search_exercise(query)
        if len(results) == 0:
            return jsonify({"message": "Exercise was not found."}), 404

        for result in results:
            result["_id"] = str(result["_id"])
        session["results"] = results
        add_search_history(query)
        return redirect(url_for("add"))

    exercises = get_matching_exercises_from_history()

    return render_template("search.html", exercises=exercises)


@app.route("/todo")
@login_required
def todo():
    """
    Displays the user's To-Do list with all the exercises and their details.
    """
    exercises = get_todo()
    return render_template("todo.html", exercises=exercises)


@app.route("/delete_exercise")
@login_required
def delete_exercise():
    """
    Renders a page to allow the user to select and delete exercises from the To-Do list.
    """
    exercises = get_todo()
    return render_template("delete.html", exercises=exercises)


@app.route("/delete_exercise/<int:exercise_todo_id>", methods=["DELETE"])
def delete_exercise_id(exercise_todo_id):
    """
    Deletes a specific exercise from the user's To-Do list using its ID.
    Returns success or error messages.
    """
    success = delete_todo(exercise_todo_id)
    if success:
        return jsonify({"message": "Deleted successfully"}), 204
    return jsonify({"message": "Failed to delete"}), 404


@app.route("/add")
@login_required
def add():
    """
    Displays a page where the user can add exercises to the To-Do list from search results.
    """
    exercises = session.get("results", [])
    return render_template(
        "add.html", exercises=exercises, exercises_length=len(exercises)
    )


@app.route("/add_exercise", methods=["POST"])
@login_required
def add_exercise():
    """
    Adds a new exercise to the user's To-Do list based on its unique ID provided in the request.
    """
    exercise_id = request.args.get("exercise_id")

    if not exercise_id:
        print("No exercise ID provided")
        return jsonify({"message": "Exercise ID is required"}), 400

    success = add_todo(exercise_id)

    if success:
        print(f"Successfully added exercise with ID: {exercise_id}")
        return jsonify({"message": "Added successfully"}), 200
    print(f"Failed to add exercise with ID: {exercise_id}")
    return jsonify({"message": "Failed to add"}), 400


@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    """
    Enables the user to edit an exercise's details in the To-Do list, such as time, reps, or weight.
    """
    exercise_todo_id = request.args.get("exercise_todo_id")
    exercise_in_todo = get_exercise_in_todo(exercise_todo_id)

    if request.method == "POST":
        working_time = request.form.get("working_time")
        weight = request.form.get("weight")
        reps = request.form.get("reps")
        success = edit_exercise(exercise_todo_id, working_time, weight, reps)
        if success:
            return jsonify({"message": "Edited successfully"}), 200
        return jsonify({"message": "Failed to edit"}), 400

    return render_template(
        "edit.html", exercise_todo_id=exercise_todo_id, exercise=exercise_in_todo
    )


@app.route("/instructions", methods=["GET"])
def instructions():
    """
    Fetches and displays detailed instructions for a specific exercise chosen by the user.
    """
    exercise_id = request.args.get("exercise_id")
    exercise = get_exercise(exercise_id)

    return render_template("instructions.html", exercise=exercise)


@app.route("/upload-audio", methods=["POST"])
def upload_audio():
    """
    Handles audio uploads. Converts the file to WAV format, sends it for transcription,
    and returns the transcribed text to the client.
    """
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
    """
    Sends the uploaded audio file to a remote speech-to-text service for transcription.
    Returns the transcription or an error message if the service fails.
    """
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


def parse_voice_command(transcription):
    """
    Parses the transcription to extract time, group count, and weight parameters.
    Returns a dictionary with these extracted values.
    """

    time_match = re.search(r"\b(\d+)\s*minutes?\b", transcription, re.IGNORECASE)
    time_params = int(time_match.group(1)) if time_match else None

    group_match = re.search(r"\b(\d+)\s*groups?\b", transcription, re.IGNORECASE)
    groups = int(group_match.group(1)) if group_match else None

    weight_match = re.search(
        r"\b(\d+)\s*(kg|kgs|kilogram|kilograms)?\b", transcription, re.IGNORECASE
    )
    weight = int(weight_match.group(1)) if weight_match else None

    return {"time": time_params, "groups": groups, "weight": weight}


@app.route("/process-audio", methods=["POST"])
@login_required
def process_audio():
    # pylint: disable=too-many-return-statements
    """
    Processes uploaded audio to extract time, groups, and weight.
    Updates the specific exercise in the To-Do list with the extracted parameters.
    """
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

    success = edit_exercise(exercise_todo_id, working_time, weight, groups)
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
def upload_transcription():
    # pylint: disable=too-many-return-statements
    """
    Processes uploaded transcription data and saves it to MongoDB.
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type. JSON expected"}), 400

        data = request.get_json()
        transcription_content = data.get("content")

        if not transcription_content:
            return jsonify({"error": "Content is required"}), 400

        if not current_user.is_authenticated:
            return (
                jsonify({"error": "User must be logged in to save transcription"}),
                401,
            )

        inserted_id = insert_transcription_entry(current_user.id, transcription_content)

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
    except PyMongoError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
