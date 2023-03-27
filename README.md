#### License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) License. For more information, please visit https://creativecommons.org/licenses/by-nc-sa/4.0/.


# TherapEase - Making Therapy Easier.

Introducing **TherapEase**: Revolutionizing Therapy for Therapists and Marginalized Communities

Envision a world where therapists and professionals working with marginalized communities can provide exceptional care while managing volume and quality with ease. Therapease is here to turn that vision into reality.

**TherapEase** is a cutting-edge tool that empowers you to monitor live therapy sessions, whether virtual or in-person. Our innovative system listens to your session in real-time, transcribes conversations, and takes comprehensive notes. With the real-time dashboard, you'll gain valuable insights into relevant topics and entities discussed during the session, allowing you to focus on what truly matters - your clients.

As conversations evolve and subject matters shift, Therapease dynamically highlights key topics and entities, ensuring you never miss crucial information. After the session, download a tailored summary of session notes and the complete transcript, streamlining your documentation process and allowing you to provide targeted support for your clients.

**TherapEase** is powered by a Python backend and a sleek HTML/JavaScript frontend. The robust Python backend is crafted with the FastAPI framework and integrates with several AI models, including:

- **Deepgram**: for streaming audio transcription and speaker diarization
- **OpenAI’s GPT-3.5-turbo**: for entity and topic modeling, summarization, and extraction
- Deepgram streams back audio transcriptions in manageable chunks, while the backend accumulates and sends them to GPT-3.5-turbo in batches. The backend then streams the results from both the transcription and language model back to the client using an event-stream, seamlessly rendering the results in the user interface.

Transform your therapeutic practice and elevate the quality of care for marginalized communities with Therapease. Join the revolution and enhance your therapy sessions today.
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

License