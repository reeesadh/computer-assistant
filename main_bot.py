import re
import whisper # open AI speech to text
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import pvporcupine # wake word engine
from pvrecorder import PvRecorder
import struct
import sys
import warnings
import time
import subprocess
import tempfile
from googlesearch import search
import webbrowser
from googleapiclient.discovery import build
import pprint
from dotenv import load_dotenv
import os
from gtts import gTTS

load_dotenv()


PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_KEY")
KEYWORD_FILE_PATH = "Hey-Assistant_en_mac_v4_0_0_WAKE_WORD.ppn"
google_api_key = os.getenv("GOOGLE_KEY")
search_id = "c1f132599771f440b"

wake_word_engine = pvporcupine.create(
    access_key = PORCUPINE_ACCESS_KEY,
    keyword_paths=[KEYWORD_FILE_PATH]
)

model = whisper.load_model("base") #AI speech to text

COMMANDS = ["google", "open notepad", "open calculator"]
SAMPLE_RATE = 16000

recording_buffer = []
is_recording = False
record_duration_seconds = 3
samples_to_record = SAMPLE_RATE * record_duration_seconds
wake_word_detected = False
note_num = 0



def removePunctuation(sentence):
    return re.sub(r"[^\w\s]", "", sentence)

def narrate(text, lang='en'):
    tts = gTTS(text=text, lang=lang, slow=False)
    filename = "output.mp3"
    tts.save(filename)
    os.system(f"afplay {filename}")

def cutOff(text, mark): # returns text after first instance of a certain marker word
    finalCut = ""
    ind = -1
    w = mark

    for word in text:
        words = text.split()
    
    for i in range(len(words)):
        if words[i] == w:
            ind = i
            break
    
    for i in range(len(words)):
        if i>ind:
            finalCut += words[i] + " "
    
    #print("FINALCUT: " + finalCut)
    return finalCut

def google(text):
    toGoogle = cutOff(text, "google")
    print(toGoogle)
    webbrowser.open(f"https://www.google.com/search?q={toGoogle}")
    narrate("google tab opened")

def openApp(text):
    app = removePunctuation(cutOff(text, "open"))[:-1]

    command = ["open", "-a", app]

    try:
        subprocess.run(command, check=True)
        narrate("opened " + app)
    except subprocess.CalledProcessError as e:
        print(f"open failed {app}: {e}")
        narrate("failed to open " + app)
    except FileNotFoundError:
        print(f"app '{app}' not found")
        narrate("could not find app " + app)

def writeNote(text):
    global note_num

    filename="assistant_new_note" + str(note_num) + ".txt"
    note_content = cutOff(text, "note")

    with open(filename, 'a') as f:
        f.write(note_content)

    print("NEW NOTE ADDED: " + note_content + " TO FILE " + filename)

    # open file for various OS
    if sys.platform.startswith('win'): #windows
        os.startfile(filename)
    elif sys.platform.startswith('darwin'): #macOS
        subprocess.Popen(['open', filename])
    elif sys.platform.startswith('linux'): #linux
        subprocess.Popen(['xdg-open', filename])
    else:
        print("Sorry, your OS is not compatible")
    
    
    note_num += 1

def detect_command(audio_data):
    #print("audio length: " + str(len(audio_data)/SAMPLE_RATE))
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        wav.write(f.name, SAMPLE_RATE, (audio_data * 32768).astype(np.int16)) # numpy to wav conversion
        result = model.transcribe(f.name, fp16=False) # transcribe audio as text using whisper model
    
    text = result['text'].lower()
    print("transcribed: " + text)

    if "open" in text:
        #print("opening app")
        openApp(text)
    if "google" in text:
        #print("googling")
        google(text)
    if "note" in text:
        writeNote(text)


    return None

silence_time = 0
def audio_callback(indata, frames, time_info, status):
    global is_recording, recording_buffer, wake_word_detected, silence_time

    if status:
        print(status)
    
    volume = 0
    silence_volume = 500
    silence_time_max = 3
    
    pcm = indata.flatten()
    result = wake_word_engine.process(pcm) # use porcupine to check if wake word detected

    if result >= 0 and not is_recording and speaking == False:
        #print("WAKE WORD DETECTED")
        narrate("hello")
        is_recording = True
        recording_buffer = []
        wake_word_detected = True
        silence_time = 0

    if is_recording:
        recording_buffer.append(pcm) # add chunks of recording

        volume = np.sqrt(np.mean(pcm.astype(np.float32)**2)) # calculate speaking volume

        if volume < silence_volume:
            silence_time += frames/SAMPLE_RATE # record for how long user is silent
        else:
            silence_time = 0
        
        # if user is silent for too long stop recording
        if silence_time > silence_time_max:
            #print("recording stopping")
            narrate("ok")
            is_recording = False

            # store audio recorded
            audio_data = np.concatenate(recording_buffer).astype(np.float32) / 32768.0
            detect_command(audio_data)

speaking = True
with sd.InputStream(
    samplerate=SAMPLE_RATE,
    blocksize=wake_word_engine.frame_length,
    dtype='int16',
    channels=1,
    callback=audio_callback):

    #print("LISTENING...")
    narrate("To use this assistant, say hey assistant.")
    print("\n-----------------FEATURES-----------------\nTo google something: say 'google' then your query\nTo open an app: say 'open' then the app name\nTo note something down: say 'note' then what you want to note down")
    speaking = False
    while True:
        time.sleep(0.1)

