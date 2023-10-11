from TTS.api import TTS

import re

model_name = "tts_models/en/ljspeech/glow-tts"
tts = TTS(model_name)
index = 0

txt = "pascal"
print(txt)
sentence = txt.split()
name = sentence[-1]

extended_name = name.replace("a", "aa")
print(extended_name)


"""while True:
    _text = input("input:")
    index += 1
    tts.tts_to_file(text = _text, file_path = "test"+str(index)+".wav")
    """

tts.tts_to_file(text = f"Ah, you are.. hmm.. {name} ... {extended_name} . . . no, I haven't heard of anyone called {name}", file_path="my name is stuttering.wav")
