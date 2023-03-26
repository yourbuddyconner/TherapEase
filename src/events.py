from typing import TypedDict

class TranscriptEvent(TypedDict):
    chunk: str

class NewTopicEvent(TypedDict):
    type: str
    topic: str
    summary: str

class NewEntityEvent(TypedDict):
    type: str
    entity: str
    summary: str
    numOccurrences: int