"""
Stream Azure Text‑to‑Speech audio using the REST API
See https://learn.microsoft.com/azure/ai-services/speech-service/rest-text-to-speech?tabs=streaming
"""

import requests
import time
from pathlib import Path


# --------------------------------------------------------------------
# 1)  Get a short‑lived bearer token (valid for 10 minutes – renew ~9 min) 
# --------------------------------------------------------------------
def get_access_token(subscription_key: str, region: str) -> str:
    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    resp = requests.post(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.text


# --------------------------------------------------------------------
# 2)  Build the SSML you want the service to speak
# --------------------------------------------------------------------
def build_ssml(text: str, voice: str = "th-TH-PremwadeeNeural", lang: str = "th-TH") -> str:
    return (
        f"<speak version='1.0' xml:lang='{lang}'>"
        f"<voice name='{voice}'>{text}</voice>"
        f"</speak>"
    )


# --------------------------------------------------------------------
# 3)  Make the streaming request
# --------------------------------------------------------------------
def stream_tts(
    text: str,
    subscription_key: str,
    region: str,
    out_path: Path | str = "speech.mp3",
    voice: str = "th-TH-PremwadeeNeural",
    output_format: str = "audio-16khz-32kbitrate-mono-mp3",
):
    token = get_access_token(subscription_key, region)

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    ssml = build_ssml(text, voice)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": output_format,
        "User-Agent": "python-streaming-client"
    }

    with requests.post(url, headers=headers, data=ssml.encode(), stream=True) as resp:
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024):
                # print with timestamp with ms
                print(f"{time.strftime('%Y-%m-%d %H:%M:%S.%f')} - Received chunk of size: {len(chunk)} bytes")
                if chunk:                      # filter out keep‑alive chunks
                    f.write(chunk)
                    f.flush()                 # audio is usable as soon as it’s written
    print(f"Saved: {out_path}")


# --------------------------------------------------------------------
# 4)  Example usage
# --------------------------------------------------------------------
if __name__ == "__main__":
    SUB_KEY  = "05b453f8ae49457f9864806208139b0d"
    REGION   = "southeastasia"          # e.g. southeastasia, westeurope …
    TEXT     = "อยู่ที่ชั้น4 โซน Crystal Court ค่ะ"

    stream_tts(TEXT, SUB_KEY, REGION)