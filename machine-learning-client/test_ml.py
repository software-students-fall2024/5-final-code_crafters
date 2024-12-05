"""test machine learning client"""

from unittest.mock import patch, MagicMock
import os
import pytest
from speech_to_text import get_google_cloud_credentials, transcribe_file
from communication import app
from llm import input_generate, make_plan_request, plan_generation

def test_missing_service_account_json():
    """test get credendtial function"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(
            EnvironmentError,
            match="Service account JSON not found in environment variables",
        ):
            get_google_cloud_credentials()


@pytest.fixture
def mock_credentials():
    """test transcribe function"""
    return MagicMock()


@pytest.fixture
def mock_response():
    """mock a response for testing"""
    alternative = MagicMock()
    alternative.transcript = "This is a test transcription."
    result = MagicMock()
    result.alternatives = [alternative]
    mock_res = MagicMock()
    mock_res.results = [result]
    return mock_res


@patch("speech_to_text.speech.SpeechClient")
def test_transcribe_file_success(
    mock_speech_client, mock_credentials, mock_response
):  # pylint: disable=redefined-outer-name
    """test transcribe file, should be successful"""
    mock_client_instance = mock_speech_client.return_value
    mock_client_instance.recognize.return_value = mock_response

    audio_file = "test_audio.wav"
    with open(audio_file, "wb") as f:
        f.write(b"fake audio content")

    result = transcribe_file(audio_file, mock_credentials)

    assert result.transcript == "This is a test transcription."
    mock_speech_client.assert_called_once_with(credentials=mock_credentials)
    mock_client_instance.recognize.assert_called_once()
    os.remove(audio_file)


@patch("speech_to_text.speech.SpeechClient")
def test_transcribe_file_value_error(mock_speech_client):
    """Test wrong value for transcribe_file"""
    mock_client_instance = MagicMock()
    mock_speech_client.return_value = mock_client_instance
    mock_client_instance.recognize.side_effect = ValueError("Invalid config or audio")

    result = transcribe_file("valid_audio.wav", None)
    assert result is None
    

@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    with app.test_client() as client:
        yield client


@patch("speech_to_text.os.getenv")
def test_get_google_cloud_credentials_missing_env(mock_getenv):
    mock_getenv.return_value = None
    with pytest.raises(EnvironmentError):
        get_google_cloud_credentials()


@patch("communication.transcribe_file")
@patch("communication.get_google_cloud_credentials")
def test_transcribe_success(mock_get_credentials, mock_transcribe, client):
    """Test transcribe function"""
    mock_get_credentials.return_value = "mock_credentials"
    
    mock_result = MagicMock()
    mock_result.transcript = "Hello, World!"
    mock_result.confidence = 0.95
    mock_transcribe.return_value = mock_result
    
    response = client.post("/transcribe", json={"audio_file": "valid_audio_path"})
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert "transcript" in json_data
    assert json_data["transcript"] == "Hello, World!"
    assert json_data["confidence"] == 0.95


@patch("communication.plan_generation")
def test_plan_generation_success(mock_plan_generation, client):
    """Test plan_generation"""
    mock_plan_generation.return_value = {"plan": "Generated plan for test"}
    
    response = client.post("/plan", json={"name": "test"})
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["plan"] == "Generated plan for test"


def test_plan_missing_user_info(client):
    """Test exception handling for plan"""
    response = client.post("/plan", json={})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data == {"error": "User information is required"}


def test_plan_wrong_user_info(client):
    """Test wrong_user_info exception handling for plan"""
    response = client.post("/plan", json={"age": "5"})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data == {"error": "User information is not complete"}


def test_transcribe_missing_audio_file(client):
    """Test missing_audio_file exception handling for transcribe"""
    response = client.post("/transcribe", json={})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data == {"error": "Audio file path is required"}


def test_input_generate():
    """Test input_generate function."""
    mock_info = {
        "name": "a",
        "weight": "60",
    }
    prompt = "Hi: "
    res = input_generate(prompt, mock_info)
    assert res == "Hi: {'name': 'a', 'weight': '60'}"


class MockSchema:
    def __init__(self, type, enum=None, required=None, properties=None, items=None):
        self.type = type
        self.enum = enum
        self.required = required or []
        self.properties = properties or {}
        self.items = items

class MockType:
    OBJECT = "object"
    ARRAY = "array"
    STRING = "string"

class MockGenerativeModel:
    def __init__(self, model_name, generation_config):
        self.model_name = model_name
        self.generation_config = generation_config
    
    def start_chat(self, history):
        return MockChatSession()

class MockChatSession:
    def send_message(self, input):
        return {"response": "Generated plan for the week."}

@patch("llm.genai.GenerativeModel", MockGenerativeModel)
@patch("llm.content.Schema", MockSchema)
@patch("llm.content.Type", MockType)
def test_make_plan_request():
    """Test make_plan_request function"""
    input_data = "Generate a weekly plan for study and rest."
    response = make_plan_request(input_data)
    assert "response" in response
    assert response["response"] == "Generated plan for the week."


@patch('llm.make_plan_request')
@patch('llm.input_generate')
def test_plan_generation_error(mock_make_plan_request, mock_input_generate):
    """Test plan_generation's error"""
    mock_input_generate.side_effect = TimeoutError
    user_info = {"name": "John", "age": 30}
    result = plan_generation(user_info)
    assert result == "The request timed out while generating the plan"



if __name__ == "__main__":
    pytest.main()
