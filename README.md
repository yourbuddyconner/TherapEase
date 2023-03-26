# TherapEase - tools to make therapy better

We built an app called TherapEase using a Python backend and HTML/JavaScript frontend.
The Python backend is built with the FastAPI framework.
The backend calls out to several AI models including:
- Deepgram for streaming audio transcription and speaker diarization
- OpenAI’s GPT-3.5-turbo for entity and topic modeling, summarization, and extraction
Deepgram streams back audio transcriptions in chunks. The backend accumulates the chunks and sends them in batches to GPT-3.5-turbo.
The backend streams results from the transcription and language model back to the client using an event-stream.
The client renders the results in the user interface.

To run this project create a virtual environment by running the below commands. You can learn more about setting up a virtual environment in this [article](https://developers.deepgram.com/blog/2022/02/python-virtual-environments/). 

```
mkdir [% NAME_OF_YOUR_DIRECTORY %]
cd [% NAME_OF_YOUR_DIRECTORY %]
python3 -m venv venv
source venv/bin/activate
```

Make sure your virtual environment is activated and install the dependencies in the requirements.txt file inside. 

```
pip install -r requirements.txt
```

Make sure you're in the directory with the **main.py** file and run the project in the development server.

```
uvicorn src.main:app --reload
```

Pull up a browser and go to your localhost, http://127.0.0.1:8000/.

Allow access to your microphone and start speaking. A transcript of your audio will appear in the browser. 

