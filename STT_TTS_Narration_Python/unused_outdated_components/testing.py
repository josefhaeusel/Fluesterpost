import sounddevice as sd
import wavio as wv
import datetime
import pathlib
import os
import glob
import ssl
import whisper
import multiprocessing
from TTS.api import TTS

ssl._create_default_https_context = ssl._create_unverified_context

def transcription_to_tts(text):
    tts_model = "tts_models/en/ljspeech/tacotron2-DCA"
    tts = TTS(tts_model)
    wav = tts.tts("Hello World")
    sd.play(wav, samplerate=22050)

transcription_to_tts("HEllo world")