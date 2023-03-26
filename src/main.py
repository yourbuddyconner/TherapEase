from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Callable
from deepgram import Deepgram
from dotenv import load_dotenv
import os
from src.llm import openaiGeneration
from src.events import NewTopicEvent, NewEntityEvent
from src.prompts import render_prompt, topic_change_prompt, entity_extraction_prompt
from src.database import db
import openai

load_dotenv()

app = FastAPI()

dg_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))
templates = Jinja2Templates(directory="templates")

async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']

            if transcript:
                # Accumulate transcript words
                if 'accumulated_transcript' not in db:
                    db['accumulated_transcript'] = ""

                # log state 

                db['accumulated_transcript'] += " " + transcript
                word_count = len(db['accumulated_transcript'].split())
                
                print(f"Transcript: {transcript}")
                print(f"Word count: {word_count}")
                print(f"Current topic: {db['current_topic']}")
                if word_count >= 50:
                    print("Generating new topic...")
                    print(f"Accumulated Transcript: {db['accumulated_transcript']}")
                    # topic list
                    topic_list = db["topics"].keys()
                    # Get the current topic
                    current_topic = db['current_topic']
                    # Get the running summary
                    try:
                        topic_summary = db["topics"][current_topic]["summary"]
                    except KeyError:
                        topic_summary = ""
                    # Get the new topic
                    topic_prompt = render_prompt(
                        topic_change_prompt,
                        topics=", ".join(list(topic_list)),
                        topic=current_topic,
                        summary=topic_summary,
                        transcript=db['accumulated_transcript']
                    )
                    next_topic = await openaiGeneration(topic_prompt, parse=True)
                    print(f"Next topic: {next_topic}")

                    if db["current_topic"] != next_topic['topic']:
                        db["current_topic"] = next_topic['topic']
                        if next_topic['topic'] not in db["topics"]:
                            db["topics"][next_topic['topic']] = {
                                "numOccurrences": 1,
                                "summary": next_topic['summary']
                            }
                        new_topic_event: NewTopicEvent = {'type': 'new_topic', 'topic': next_topic['topic']}
                        await fast_socket.send_json(new_topic_event)

                    # Reset the accumulated transcript
                    db['accumulated_transcript'] = ""

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket

async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        socket = await dg_client.transcription.live({'punctuate': True, 'interim_results': False})
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
