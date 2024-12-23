import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fish_audio_sdk import Session, TTSRequest
from dotenv import load_dotenv
from pydub import AudioSegment
import asyncio
import os
import uuid
import json
import boto3

app = FastAPI()

# 환경 변수 로드
load_dotenv(dotenv_path=".env")
API_KEY = os.getenv("Fish_API_KEY")
KR_MODEL_ID = os.getenv("KR_MODEL_ID")
EN_MODEL_ID = os.getenv("EN_MODEL_ID")
AUDIO_FORMAT = "mp3"
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET = os.getenv("AWS_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")

# S3 클라이언트 생성
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

# 세션 초기화
session = Session(API_KEY)

class TTSRequestData(BaseModel):
    file_name: str
    language: str
    text: str
    folder: str

def get_model_id(language: str) -> str:
    """언어 코드에 따라 모델 ID 반환"""
    if language.upper() == "KR":
        return KR_MODEL_ID
    elif language.upper() == "EN":
        return EN_MODEL_ID
    else:
        raise ValueError("지원되지 않는 언어")

def split_into_sentences(text: str):
    """텍스트를 문장 단위로 분리"""
    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    return [sentence for sentence in sentences if sentence]

async def process_line_tts(index: int, line: str, model_id: str) -> dict:
    """단일 문장에 대해 TTS 생성 (동기 작업 비동기로 처리)"""
    if not line.strip():
        return {"index": index, "start": 0, "temp_file": None}

    temp_file = f"{uuid.uuid4()}.mp3"

    # 동기 TTS 생성 작업을 비동기로 실행
    def sync_tts():
        with open(temp_file, "wb") as f:
            for chunk in session.tts(TTSRequest(reference_id=model_id, text=line, format=AUDIO_FORMAT)):
                f.write(chunk)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_tts)

    # 오디오 파일 로드
    audio = AudioSegment.from_file(temp_file, format=AUDIO_FORMAT)
    duration = audio.duration_seconds

    return {"index": index, "start": duration, "temp_file": temp_file}

async def generate_tts_and_timeline(folder: str, file_name: str, model_id: str, text: str):
    """TTS 생성 및 타임라인 반환 (비동기, 4개씩 처리)"""
    sentences = split_into_sentences(text)
    combined_audio = AudioSegment.silent(duration=0)
    timeline = []
    temp_files = []

    # 요청한 폴더 생성 (없으면 생성)
    if not os.path.exists(folder):
        os.makedirs(folder)

    # 동시 작업 제한 설정 (한 번에 최대 4개의 작업 실행)
    semaphore = asyncio.Semaphore(4)

    async def limited_process_line_tts(index, line):
        async with semaphore:  # 세마포어 사용
            result = await process_line_tts(index, line, model_id)
            return result

    # 비동기 작업 실행
    tasks = [
        limited_process_line_tts(index, line)
        for index, line in enumerate(sentences)
    ]
    results = await asyncio.gather(*tasks)

    # 타임스탬프 및 오디오 병합
    start_time = 0.0
    for result in results:
        if result["temp_file"]:
            temp_files.append(result["temp_file"])
            line_audio = AudioSegment.from_file(result["temp_file"], format=AUDIO_FORMAT)

            # 타임스탬프 추가
            timeline.append(round(start_time, 2))
            combined_audio += line_audio + AudioSegment.silent(duration=300)
            start_time += result["start"] + 0.3

    # MP3 파일 저장
    mp3_file = f"{folder}/{file_name}.mp3"
    combined_audio.export(mp3_file, format="mp3")

    # 임시 파일 삭제
    for temp_file in temp_files:
        os.remove(temp_file)

    return mp3_file, timeline

def upload_to_s3(file_path: str, bucket: str, object_name: str) -> str:
    """S3에 파일 업로드 및 URL 반환"""
    s3_client.upload_file(
        file_path,
        bucket,
        object_name,
        ExtraArgs={
            "ContentType": "audio/mpeg",  # MP3 파일의 Content-Type 설정
            "ContentDisposition": "inline"  # 브라우저에서 바로 재생 가능하도록 설정
        },
    )
    os.remove(file_path)  # 로컬 파일 삭제
    s3_url = f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{object_name}"
    return s3_url

@app.post("/generate-tts")
async def generate_tts_api(request_data: TTSRequestData):
    """TTS 생성 API"""
    try:
        folder = request_data.folder.strip()
        file_name = request_data.file_name.strip()
        language = request_data.language.strip()
        text = request_data.text.strip()

        if not folder or not file_name or not text or not language:
            raise HTTPException(status_code=400, detail="folder, file_name, language 또는 text가 제공되지 않았습니다.")

        # 언어에 따라 모델 ID 가져오기
        model_id = get_model_id(language)

        # TTS 및 타임라인 생성
        mp3_file, timeline = await generate_tts_and_timeline(folder, file_name, model_id, text)

        # S3에 MP3 파일 업로드
        s3_url = upload_to_s3(mp3_file, AWS_BUCKET, f"{folder}/{file_name}.mp3")

        # S3 URL 및 타임스탬프 반환
        return {"ttsUrl": s3_url, "timestamps": timeline}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)