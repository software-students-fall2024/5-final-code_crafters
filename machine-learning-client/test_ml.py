"""test machine learning client"""

from unittest.mock import patch, MagicMock
import os
import pytest
from speech_to_text import get_google_cloud_credentials
from speech_to_text import transcribe_file
from speech_to_text import app


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


@pytest.fixture
def client():
    """test communication function"""
    with app.test_client() as client:  # pylint: disable=redefined-outer-name
        yield client


@patch("speech_to_text.get_google_cloud_credentials")
@patch("speech_to_text.transcribe_file")
def test_transcribe_success(
    mock_transcribe_file, mock_get_google_cloud_credentials, client
):  # pylint: disable=redefined-outer-name
    """test transcribe file function with interaction with web app, should be successful"""
    mock_get_google_cloud_credentials.return_value = MagicMock()

    mock_result = MagicMock()
    mock_result.transcript = "hello may I ask what's your name"
    mock_result.confidence = 0.9
    mock_transcribe_file.return_value = mock_result

    response = client.post("/transcribe", json={"audio_file": "path/to/test_audio.wav"})

    assert response.status_code == 200
    assert response.get_json() == {
        "transcript": "hello may I ask what's your name",
        "confidence": 0.9,
    }


if __name__ == "__main__":
    pytest.main()
