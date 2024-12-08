from speech_to_text import transcribe_file, get_google_cloud_credentials
from llm import plan_generation
from flask import Flask, request, jsonify


app = Flask(__name__)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Communicate between web app and ml client.
    Keyword arguments:
    argument -- None
    Return: Transcription of the audio file.
    """
    data = request.json
    audio_file = data.get("audio_file")
    print(f"Received audio file path: {audio_file}")

    if not audio_file:
        return jsonify({"error": "Audio file path is required"}), 400

    credentials = get_google_cloud_credentials()
    result = transcribe_file(audio_file, credentials)

    if result is None:
        return jsonify({"error": "Transcription failed"}), 500

    return jsonify({"transcript": result.transcript, "confidence": result.confidence})


@app.route("/plan", methods=["POST"])
def plan():
    user_info = request.json

    if not user_info:
        return jsonify({"error": "User information is required"}), 400

    result = plan_generation(user_info)

    if result is "Error generating plan":
        return jsonify({"error": "Plan generation failed"}), 500

    return result


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
