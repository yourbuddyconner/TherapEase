from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Callable
from deepgram import Deepgram
from dotenv import load_dotenv
import os
from src.llm import openaiGeneration, openaiChatGeneration
from src.events import NewTopicEvent, NewEntityEvent
from src.prompts import render_prompt, topic_change_prompt, topic_change_system_prompt, topic_change_user_prompt
from src.prompts import entity_extraction_system_prompt, entity_extraction_user_prompt
from src.prompts import entity_summary_combination_system_prompt, entity_summary_combination_user_prompt
from src.database import db
import asyncio

load_dotenv()

app = FastAPI()

dg_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))
templates = Jinja2Templates(directory="templates")

async def extract_topic(fast_socket: WebSocket, accumulated_transcript: str):
    print("Generating new topic...")
    print(f"Accumulated Transcript: {db['accumulated_transcript']}")
    topic_list = db["topics"].keys()
    current_topic = db['current_topic']
    try:
        topic_summary = db["topics"][current_topic]["summary"]
    except KeyError:
        topic_summary = ""

    # Extract topics from accumulated transcript
    topic_user_prompt = render_prompt(
        topic_change_user_prompt,
        topics=", ".join(list(topic_list)),
        topic=current_topic,
        summary=topic_summary,
        transcript=db['accumulated_transcript']
    )
    next_topic = await openaiChatGeneration(topic_change_system_prompt, topic_user_prompt, parse=True)
    print(f"Next topic: {next_topic}")

    if db["current_topic"] != next_topic['topic']:
        db["current_topic"] = next_topic['topic']
        if next_topic['topic'] not in db["topics"]:
            db["topics"][next_topic['topic']] = {
                "numOccurrences": 1,
                "summary": next_topic['summary']
            }
            print(f"Summary: {next_topic['topic']}")
        else:
            db["topics"][next_topic['topic']]['numOccurrences'] += 1
            db["topics"][next_topic['topic']]['summary'] = next_topic['summary']
        new_topic_event: NewTopicEvent = {
            'type': 'new_topic', 
            'topic': next_topic['topic'],
            'summary': next_topic['summary']
        }
        await fast_socket.send_json(new_topic_event)

async def extract_entities(fast_socket: WebSocket, accumulated_transcript: str):
    # Extract entities from accumulated transcript
    entity_user_prompt = render_prompt(
        entity_extraction_user_prompt,
        entities=", ".join(list(db["entities"].keys())),
        transcript=db['accumulated_transcript']
    )
    # this should be a list of dictionaries
    next_entities = await openaiChatGeneration(entity_extraction_system_prompt, entity_user_prompt, parse=True)
    print(f"Next entities: {next_entities}")

    for entity in next_entities:
        if entity['name'] not in db["entities"]:
            db["entities"][entity['name']] = {
                "numOccurrences": 1,
                "summary": entity['summary']
            }
            print(f"Summary: {entity['summary']}")
        else:
            db["entities"][entity['name']]['numOccurrences'] += 1
            # combine summaries
            # entity_summary_combination_user_prompt = render_prompt(
            #     entity_summary_combination_system_prompt,
            #     summary1=db["entities"][entity['name']]['summary'],
            #     summary2=entity['summary']
            # )
            # combined_summary = await openaiGeneration(entity_summary_combination_user_prompt)
            # db["entities"][entity['name']]['summary'] = combined_summary
            # print(f"Combined summary: {combined_summary}")
        
        new_entity_event: NewEntityEvent = {
            'type': 'new_entity', 
            'entity': entity['name'], 
            'summary': db["entities"][entity['name']]['summary'],
            'numOccurrences': db["entities"][entity['name']]['numOccurrences']
        }
        await fast_socket.send_json(new_entity_event)

async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            words = data['channel']['alternatives'][0]['words']
            if words:
                speaker = None
                transcript_chunk = ""
                for word in words:
                    if speaker is None or speaker != word['speaker']:
                        if transcript_chunk:
                            await fast_socket.send_json({
                                "type": "transcript",
                                "chunk": transcript_chunk.strip(),
                                "speaker": speaker
                            })
                            db['accumulated_transcript'] += " " + transcript_chunk.strip()
                        speaker = word['speaker']
                        transcript_chunk = ""
                    transcript_chunk += " " + word['word']

                # Handle the last chunk
                if transcript_chunk:
                    await fast_socket.send_json({
                        "type": "transcript",
                        "chunk": transcript_chunk.strip(),
                        "speaker": speaker
                    })
                    db['accumulated_transcript'] += " " + transcript_chunk.strip()

                word_count = len(db['accumulated_transcript'].split())

                print(f"Word count: {word_count}")
                print(f"Current topic: {db['current_topic']}")


                if word_count >= 10:
                    topic_task = asyncio.create_task(
                        extract_topic(fast_socket, db['accumulated_transcript'])
                    )
                    entity_task = asyncio.create_task(
                        extract_entities(fast_socket, db['accumulated_transcript'])
                    )
                    await asyncio.gather(topic_task, entity_task)

                    db['accumulated_transcript'] = ""

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket

async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False, 'diarize': True})
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')

@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        deepgram_socket = await process_audio(websocket)

        while True:
            data = await websocket.receive_bytes()
            deepgram_socket.send(data)
    except Exception as e:
        raise Exception(f'Could not process audio: {e}')
    finally:
        await websocket.close()
