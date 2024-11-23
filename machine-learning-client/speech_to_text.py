"""
This module provides functions for speech-to-text transcription using Google Cloud Speech API.
"""

import os
import json
from dotenv import load_dotenv
from google.cloud import speech
from google.oauth2 import service_account
from flask import Flask, request, jsonify

load_dotenv()
app = Flask(__name__)


def get_google_cloud_credentials():
    """Create a credential.
    Keyword arguments:
    argument -- None
    Return: credentials
    """
    service_account_json = os.getenv("GOOGLE_CLOUD_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        raise EnvironmentError(
            "Service account JSON not found in environment variables"
        )

    credentials_dict = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict
    )
    return credentials


def transcribe_file(audio_file: str, credentials) -> speech.RecognizeResponse:
    """Transcribe the audio to the text.
    Keyword arguments:
    argument -- adress of the audio file, credential.
    Return: Transcription of the audio file.
    """
    try:
        client = speech.SpeechClient(credentials=credentials)
        # print(f"Reading audio file: {audio_file}")
        with open(audio_file, "rb") as f:
            audio_content = f.read()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )

        # print("Sending recognition request...")
        response = client.recognize(config=config, audio=audio)

        if not response.results:
            print("No transcription results found.")

        return response.results[0].alternatives[0]

    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except ValueError as e:
        print(f"Value error: {e}")

    return None


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


if __name__ == "__main__":
    # credentials = get_google_cloud_credentials()
    # res = transcribe_file("./machine-learning-client/recording.wav", credentials)
    # print(res)
    app.run(host="0.0.0.0", port=8080)
