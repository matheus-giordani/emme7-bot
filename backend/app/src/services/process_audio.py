"""Handling audio."""

import requests
from typing import Optional
from io import BytesIO
from pydub import AudioSegment  # type: ignore
from openai import OpenAI


class ProcessAudio:
    """Class that downloads audio and transcribes it."""

    def __init__(self, openai_key: str) -> None:
        """Initialize the class."""
        self.openai_key = openai_key
        self.client_openai = OpenAI(api_key=self.openai_key)

    def audio_request(self, url: str) -> Optional[requests.models.Response]:
        """Request audio from url."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return None
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            return None
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            return None

    def fetch_audio(self, url: str) -> Optional[BytesIO]:
        """Download the audio."""
        response = self.audio_request(url)

        # Checks if the request was successful
        if response is not None and response.status_code == 200:

            # Read the file in BytesIO.
            ogg_audio = BytesIO(response.content)

            # Converting OGG audio to MP3.
            audio_segment = AudioSegment.from_ogg(ogg_audio)
            mp3_audio = BytesIO()
            audio_segment.export(mp3_audio, format="mp3")

            # Ensure the BytesIO object is set to the start
            mp3_audio.seek(0)
            mp3_audio.name = "audio.mp3"
            return mp3_audio
        else:
            return None

    def audio_transcription(self, url: str) -> str:
        """Audio to text."""
        try:
            mp3_audio = self.fetch_audio(url)
            if mp3_audio is None:
                return "Mensagem de áudio vazia."

            transcription = self.client_openai.audio.transcriptions.create(
                model="whisper-1", file=mp3_audio
            )
            return str(transcription.text)
        except Exception as err:
            print("Não foi possível transcrever o áudio.")
            print(str(err))
            return "Mensagem de áudio."
