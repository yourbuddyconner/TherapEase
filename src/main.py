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
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import textwrap
from io import BytesIO

load_dotenv()

app = FastAPI()

dg_client = Deepgram(os.getenv('DEEPGRAM_API_KEY'))
templates = Jinja2Templates(directory="templates")

async def extract_topic(fast_socket: WebSocket, accumulated_transcript: str):
    db['accumulated_transcript'] = ""
    print("Discovering new topics...")
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
        transcript=accumulated_transcript  # Use the parameter instead of the in-memory database
    )
    print(topic_user_prompt)
    next_topic = await openaiChatGeneration(topic_change_system_prompt, topic_user_prompt, parse=True)
    print(f"Next topic: {next_topic}")

    summary_updated = False

    if db["current_topic"] != next_topic['topic']:
        db["current_topic"] = next_topic['topic']
        if next_topic['topic'] not in db["topics"]:
            db["topics"][next_topic['topic']] = {
                "numOccurrences": 1,
                "summary": next_topic['summary']
            }
            summary_updated = True
            print(f"Summary: {next_topic['topic']}")
        else:
            db["topics"][next_topic['topic']]['numOccurrences'] += 1

            # Check if the summary has changed
            if db["topics"][next_topic['topic']]['summary'] != next_topic['summary']:
                db["topics"][next_topic['topic']]['summary'] = next_topic['summary']
                summary_updated = True
                print(f"Updated summary: {next_topic['summary']}")

    if summary_updated:
        print(f"Sending new_topic event: {next_topic['topic']}, summary: {next_topic['summary']}")
        new_topic_event: NewTopicEvent = {
            'type': 'new_topic', 
            'topic': next_topic['topic'],
            'summary': next_topic['summary']
        }
        await fast_socket.send_json(new_topic_event)


async def extract_entities(fast_socket: WebSocket, accumulated_transcript: str):
    db['accumulated_transcript'] = ""
    print("Discovering new entities...")
    # Extract entities from accumulated transcript
    entity_user_prompt = render_prompt(
        entity_extraction_user_prompt,
        entities=", ".join(list(db["entities"].keys())),
        transcript=accumulated_transcript  # Use the parameter instead of the in-memory database
    )
    # this should be a list of dictionaries
    next_entities = await openaiChatGeneration(entity_extraction_system_prompt, entity_user_prompt, parse=True)
    print(f"Next entities: {next_entities}")

    for entity in next_entities:
        summary_updated = False

        if entity['name'] not in db["entities"]:
            db["entities"][entity['name']] = {
                "numOccurrences": 1,
                "summary": entity['summary']
            }
            summary_updated = True
            print(f"Summary: {entity['summary']}")
        else:
            db["entities"][entity['name']]['numOccurrences'] += 1

            # Check if the summary has changed
            if db["entities"][entity['name']]['summary'] != entity.get('summary', ''):
                db["entities"][entity['name']]['summary'] = entity.get('summary', '')
                summary_updated = True
                print(f"Updated summary: {entity['summary']}")

        if summary_updated:
            # Create a new dictionary for the new_entity_event
            new_entity_event: NewEntityEvent = {
                'type': 'new_entity', 
                'entity': entity['name'], 
                'summary': db["entities"][entity['name']]['summary'],
                'numOccurrences': db['entities'][entity['name']]['numOccurrences']
            }
            print(f"Sending new_entity event: {entity['name']}, numOccurrences: {db['entities'][entity['name']]['numOccurrences']}, summary: {db['entities'][entity['name']]['summary']}")

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
                            print(f"Sending transcript chunk: {transcript_chunk.strip()}, speaker: {speaker}")
                            await fast_socket.send_json({
                                "type": "transcript",
                                "chunk": transcript_chunk.strip(),
                                "speaker": speaker
                            })
                            db['accumulated_transcript'] += " " + transcript_chunk.strip()
                            db['complete_transcript'] += f"\n Speaker {speaker}: {transcript_chunk.strip()} "
                        speaker = word['speaker']
                        transcript_chunk = ""
                    transcript_chunk += " " + word['word']

                # Handle the last chunk
                if transcript_chunk:
                    print(f"Sending transcript chunk: {transcript_chunk.strip()}, speaker: {speaker}")
                    await fast_socket.send_json({
                        "type": "transcript",
                        "chunk": transcript_chunk.strip(),
                        "speaker": speaker
                    })
                    db['accumulated_transcript'] += " " + transcript_chunk.strip()
                    db['complete_transcript'] += f"\n Speaker {speaker}: {transcript_chunk.strip()} "

                word_count = len(db['accumulated_transcript'].split())

                print(f"Word count: {word_count}")
                print(f"Current topic: {db['current_topic']}")


                if word_count >= 25:
                    topic_task = asyncio.create_task(
                        extract_topic(fast_socket, db['accumulated_transcript'])
                    )
                    entity_task = asyncio.create_task(
                        extract_entities(fast_socket, db['accumulated_transcript'])
                    )
                    await asyncio.gather(topic_task, entity_task)


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

# def generate_pdf_report() -> BytesIO:
#     topics_data = db['topics']
#     entities_data = db['entities']
#     transcript = db['accumulated_transcript']

#     # Prepare HTML template
#     html_template = templates.get_template("report_template.html")
#     html_content = html_template.render(topics=topics_data, entities=entities_data, transcript=transcript)

#     # Generate the PDF
#     pdf_buffer = BytesIO()
#     HTML(string=html_content).write_pdf(pdf_buffer)
#     pdf_buffer.seek(0)
#     return pdf_buffer

def check_space_and_add_page_break(c, y, space_needed):
    page_height = letter[1]
    bottom_margin = 50
    if y - space_needed < bottom_margin:
        c.showPage()
        return page_height - 50
    return y

def wrap_text(text, width):
    return textwrap.wrap(text, width)

def draw_wrapped_text(c, x, y, text, width, font, size):
    wrapped_text = wrap_text(text, width)
    c.setFont(font, size)
    for line in wrapped_text:
        c.drawString(x, y, line)
        y -= size + 2
    return y

def generate_pdf_report() -> BytesIO:
    topics_data = db['topics']
    entities_data = db['entities']
    transcript = db['complete_transcript']

    # Generate the PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer)
    y = 750

    # Add the report title
    y = check_space_and_add_page_break(c, y, 30)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, y, "Report")
    y -= 30

    # Add the topics section
    y = check_space_and_add_page_break(c, y, 20)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y, "Topics")
    y -= 20
    for topic, data in topics_data.items():
        y = check_space_and_add_page_break(c, y, 40)
        c.setFont("Helvetica", 12)
        c.drawString(120, y, topic)
        c.drawString(320, y, f"{data['numOccurrences']} occurrences")
        y -= 20
        y = draw_wrapped_text(c, 120, y, data['summary'], 60, "Helvetica", 12)
        y -= 20

    # Add the entities section
    y = check_space_and_add_page_break(c, y, 20)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y, "Entities")
    y -= 20
    for entity, data in entities_data.items():
        y = check_space_and_add_page_break(c, y, 40)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(120, y, entity)
        y -= 14
        c.setFont("Helvetica", 12)
        c.drawString(300, y, f"{data['numOccurrences']} occurrences")
        y -= 6
        y = draw_wrapped_text(c, 120, y - 10, data['summary'], 60, "Helvetica", 12)
        y -= 20

    # Add the transcript section
    y = check_space_and_add_page_break(c, y, 20)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y, "Transcript")
    y -= 20
    y = draw_wrapped_text(c, 100, y, transcript, 80, "Helvetica", 12)

    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer


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

# @app.get("/download_report", response_class=FileResponse)
# async def download_report():
#     pdf_buffer = generate_pdf_report()
#     return FileResponse(
#         pdf_buffer,
#         media_type="application/pdf",
#         headers={"Content-Disposition": "attachment; filename=report.pdf"},
#     )

@app.get("/download_report", response_class=StreamingResponse)
async def download_report():
    pdf_buffer = generate_pdf_report()
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=report.pdf"},
    )