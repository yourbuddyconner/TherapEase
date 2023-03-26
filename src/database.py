from typing import TypedDict

class TopicType(TypedDict):
    numOccurrences: int
    summary: str

class EntityType(TypedDict):
    numOccurrences: int
    summary: str

class DbType(TypedDict):
    accumulated_transcript: str
    running_summary: str
    current_topic: str
    topics: dict[str, TopicType]
    entities: dict[str, EntityType]

db: DbType = {
    "accumulated_transcript": "",
    "running_summary": "",
    "current_topic": "",
    "topics": {},
    "entities": {},
}