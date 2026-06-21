from pydantic import BaseModel

class CompareRequest(BaseModel):
    object_a: str
    object_b: str

class LearnRequest(BaseModel):
    target_object: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    selected_label: str
    messages: list[ChatMessage]
