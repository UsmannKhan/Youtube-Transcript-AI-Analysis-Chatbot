from typing import List
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session 
from starlette import status
from .. import models
from .. import schemas
from fastapi import APIRouter
from ..database import get_db
from ..config import user_dependency
from ..gemini_client import client

router = APIRouter(
    prefix='/messages',
    tags=['Messages']
)

@router.post("/")
def create_message(message: schemas.CreateMessage, user: user_dependency, db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == message.chat_id, models.Chat.user_id == user['id']).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    transcript = chat.youtube_transcript
    response_message = client.models.generate_content(
          model="gemini-2.0-flash",
          contents=f"{message.input} for reference: {transcript}",
        )
    output = response_message.text

    new_message = models.Message(
        input = message.input,
        output = output,
        chat_id = message.chat_id,
        user_id = user['id']
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return {
        "id": new_message.id,
        "input": message.input,
        "output": output,
        "chat_id": new_message.chat_id,
        "user_id": new_message.user_id
    }

@router.get("/{chat_id}", response_model=List[schemas.MessageOut])
def get_chat_messages(chat_id, user: user_dependency, db:Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(
        models.Chat.id == chat_id,
        models.Chat.user_id == user['id']
    ).first()

    chat_messages = db.query(models.Message).filter(
        models.Message.chat_id == chat_id,
        models.Message.user_id == user['id']
    ).all()

    return chat_messages