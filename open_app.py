import os

from gtts import gTTS


def narrate(text, lang='en'):
    tts = gTTS(text=text, lang=lang, slow=False)
    filename = "output.mp3"
    tts.save(filename)
    os.system(f"afplay {filename}")

narrate("testing text to speech")

narrate("1 2 3")

narrate ("a. b. c. d.")