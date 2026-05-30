"""SiteNarrator — Voice transcription via AWS Transcribe.

Handles transcription of Superintendent voice notes (.m4a, .wav, .mp3, .webm)
into text. The voice note is the primary structured data source — it carries
crew counts, equipment usage, delays, and inspection results that photos cannot show.
"""

from __future__ import annotations

import time
import uuid

import boto3

from src.config import get_settings
from src.tools.tracing import traced


@traced("transcribe.voice_note")
def transcribe_audio(file_uri: str, media_format: str = "mp4") -> str:
    """Transcribe a voice note using AWS Transcribe.

    Args:
        file_uri: S3 URI or accessible URL of the audio file.
                  For local files, upload to S3 first.
        media_format: Audio format — 'mp4' (.m4a), 'wav', 'mp3', 'webm'

    Returns:
        Transcribed text string.
    """
    settings = get_settings()
    client = boto3.client("transcribe", region_name=settings.aws_region)

    job_name = f"sitenarrator-{uuid.uuid4().hex[:12]}"

    # Map common extensions to Transcribe format names
    format_map = {
        "m4a": "mp4",
        "mp4": "mp4",
        "wav": "wav",
        "mp3": "mp3",
        "webm": "webm",
    }
    transcribe_format = format_map.get(media_format, media_format)

    client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": file_uri},
        MediaFormat=transcribe_format,
        LanguageCode="en-US",
        Settings={
            "ShowPunctuationFilter": True,
        },
    )

    # Poll for completion
    while True:
        response = client.get_transcription_job(TranscriptionJobName=job_name)
        status = response["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            transcript_uri = response["TranscriptionJob"]["Transcript"][
                "TranscriptFileUri"
            ]
            break
        elif status == "FAILED":
            failure_reason = response["TranscriptionJob"].get(
                "FailureReason", "Unknown error"
            )
            raise RuntimeError(
                f"Transcription failed: {failure_reason}"
            )

        time.sleep(2)

    # Fetch the transcript
    import requests

    transcript_response = requests.get(transcript_uri, timeout=30)
    transcript_response.raise_for_status()
    transcript_data = transcript_response.json()

    # Extract the full transcript text
    transcripts = transcript_data.get("results", {}).get("transcripts", [])
    if transcripts:
        return transcripts[0].get("transcript", "")

    return ""


@traced("transcribe.upload_to_s3")
def upload_audio_to_s3(
    file_path: str, project_id: str, date: str
) -> str:
    """Upload a local audio file to S3 for transcription.

    Returns the S3 URI for use with AWS Transcribe.
    """
    settings = get_settings()
    s3_client = boto3.client("s3", region_name=settings.aws_region)

    bucket = f"sitenarrator-{settings.aws_region}"
    key = f"voice-notes/{project_id}/{date}/{uuid.uuid4().hex[:8]}.m4a"

    s3_client.upload_file(file_path, bucket, key)

    return f"s3://{bucket}/{key}"
