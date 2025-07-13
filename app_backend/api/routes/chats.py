from typing import List
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session 
from starlette import status
from .. import models
from .. import schemas
from fastapi import APIRouter
from ..database import get_db
from ..config import user_dependency
from youtube_transcript_api import YouTubeTranscriptApi
from ..gemini_client import client
import json

router = APIRouter(
    prefix='/chats',
    tags=['Chats']
)

def get_videoid(url):
      if '=' in url:
        parts = url.split('=')
        if len(parts) > 1:  # Check if there are parts after the first '='
          video_id = parts[1]
          if '&' in video_id:  # Check for additional parameters after video ID
            video_id = video_id.split('&')[0]  # Extract only video ID
          return video_id
      return ""

@router.post("/")
def create_chat(chat: schemas.CreateChat, user: user_dependency, db: Session = Depends(get_db)):
    video_id = get_videoid(chat.youtube_link)
    transcript_data = YouTubeTranscriptApi.get_transcript(video_id)

    transcript = " ".join(segment['text'] for segment in transcript_data)

    response = client.models.generate_content(
      model="gemini-2.0-flash",
      contents=f"Please provide notes and analysis on the following Youtube transcript: {transcript}",
    )
    notes = response.text
    response2 = client.models.generate_content(
      model="gemini-2.0-flash",
      contents=f"Please provide a short descriptive title for the following notes. Give the answer directly: {notes}",
    )
    session_name = response2.text


    new_chat = models.Chat(
        youtube_id = video_id,
        youtube_transcript = transcript,
        prompt = "Please provide notes and analysis on the following Youtube transcript",
        notes = notes,
        user_id = user['id'],
        session_name = session_name
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return {
        "id": new_chat.id,
        "video_id": video_id,
        "notes": notes,
        "transcript": transcript,
        "session_name": session_name
    }

@router.get("/", response_model=List[schemas.ChatOut])
def get_user_chats(user: user_dependency, db:Session = Depends(get_db)):
  chats = db.query(models.Chat).filter(models.Chat.user_id == user['id']).all()

  return chats

@router.delete("/{chat_id}")
def delete_user_chat(chat_id: int, user: user_dependency, db:Session = Depends(get_db)):
  chat = db.query(models.Chat).filter(
    models.Chat.id == chat_id,
    models.Chat.user_id == user['id']
  ).first()
  if chat:
    db.delete(chat)
    db.commit()
  return chat