from typing import TypedDict

class TranscriptEvent(TypedDict):
    chunk: str

class NewTopicEvent(TypedDict):
    type: str
    topic: str

class NewEntityEvent(TypedDict):
    type: str
    entity: str