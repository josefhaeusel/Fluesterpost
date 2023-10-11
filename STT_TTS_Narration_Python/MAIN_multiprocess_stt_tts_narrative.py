import sounddevice as sd
import wavio as wv
import datetime
import pathlib
import os
import glob
import ssl
import whisper
import multiprocessing
import time
import random as rdm
import argparse as arg
import simpleaudio as sa
from TTS.api import TTS
from pythonosc import udp_client

### SSL Bugfix Whisper SST
ssl._create_default_https_context = ssl._create_unverified_context
### Global Variables
DIR_PATH = pathlib.Path(__file__).parent.resolve()
RECORDINGS_DIR = os.path.join(f'{DIR_PATH}/recordings/', '*')
RECORDINGS_DIR_OS = f'{DIR_PATH}/recordings/'
SAMPLES_DIR = f'{DIR_PATH}/samples'


def delete_old_recordings_periodically():
    """
    Every 1 minute, delete all recordings except for last 5. 
    
    """

    while True:
        files = os.listdir(RECORDINGS_DIR_OS)
        files = [os.path.join(RECORDINGS_DIR_OS, file) for file in files]
        files = sorted(files, key=os.path.getctime)
        old_files = files[:len(files)-5]
        if len(files) > 5:
            for file_to_delete in old_files:
                try:
                    os.remove(file_to_delete)
                    print(f"Deleted: {file_to_delete}")
                except OSError as e:
                    print(f"Error deleting {file_to_delete}: {e}")
        time.sleep(60)

def delete_all_recordings(except_last = True):
    """
    When called, deletes all recordings in ../recordings folder.
    
    """

    files = os.listdir(RECORDINGS_DIR_OS)
    files = [os.path.join(RECORDINGS_DIR_OS, file) for file in files]
    files = sorted(files, key=os.path.getctime)
    if except_last:
        last_file = files.pop(-1)

    for file_to_delete in files:
        try:
            os.remove(file_to_delete)
            print(f"Deleted: {file_to_delete}")
        except OSError as e:
            print(f"Error deleting {file_to_delete}: {e}")
    
    if except_last:
        return last_file

def record_audio():
    """
    Records files from Ch. 1 of System Input Device with reference to time in filename

    """

    freq = 44100
    duration = 2

    while True:
        ts = datetime.datetime.now()
        filename = ts.strftime("%Y-%m-%d %H:%M:%S")
        recording = sd.rec(int(duration * freq), samplerate=freq, channels=1)
        sd.wait()
        wv.write(f"{DIR_PATH}/recordings/{filename}.wav", recording, freq, sampwidth=2)

def speech_to_text(first_delete_all_recs = True, delete_recordings_callback = delete_all_recordings):
    """
    Transcribes the latest recorded files from record_audio() in ../recordings/... into text, exluding the already transcribes ones.

    """
    
    if first_delete_all_recs:
        last_file = delete_recordings_callback(except_last = False)
    else:
        last_file = ""

    transcription_done = False
    model = whisper.load_model("base")
    transcribed = [last_file]

    #Variables for 'No-Answer Samples'
    sample_ids = [0,1,2,3,4]
    rdm.shuffle(sample_ids)
    zero_time = time.time()

    while not transcription_done:
        current_time = time.time()
        elapsed_time = current_time - zero_time
        print("Transcribing...")
        files = sorted(glob.iglob(RECORDINGS_DIR), key=os.path.getctime, reverse=True)
        latest_recording = files[0]

        #Trigger "I can't hear you sample" (and similar) after 8 seconds
        if elapsed_time >= 10:
            if sample_ids:
                sample_id = sample_ids[0]
                sample = f"{SAMPLES_DIR}/no_answer_sample{sample_id}.wav"
                wave_obj = sa.WaveObject.from_wave_file(sample)
                wave_obj.play()
                zero_time = time.time()
                sample_ids.pop(0)
            else:
                sample_ids = [0,1,2,3,4]
                rdm.shuffle(sample_ids)

        if os.path.exists(latest_recording) and latest_recording not in transcribed:
            audio = whisper.load_audio(latest_recording)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            options = whisper.DecodingOptions(language='en', fp16=False, temperature=0.5, sample_len = 10, suppress_blank=True )

            result = whisper.decode(model, mel, options)

            if result.no_speech_prob < 0.7:

                with open(f"{DIR_PATH}/transcriptions/transcript.txt", 'a') as f:
                    f.write(result.text)

                transcribed.append(latest_recording)
                transcription_done = True
        
    print("\n\nTRANSCRIPTION DONE:", result.text, "\n\n")
    return result.text 

def text_to_speech(text, mute_mic = True):

    """
    Synthesizes input string into speech, plays soundfile and waits till done.
    Output can get routed to Max (Ch.2), to get Vocoder Sound

    OSC Message to Max (un-) mutes microphone input (0 closed, 1 open)
    
    """

    if mute_mic:
        osc_message("/gate_mic", 0)
    
    text = add_period(text)
    tts_model = "tts_models/en/ljspeech/glow-tts"
    tts = TTS(tts_model)

    wav = tts.tts(text)
    sd.play(wav, samplerate=22050)
    sd.wait()
    
    osc_message("/gate_mic", 1)

def osc_message(osc_channel = "/rec_channel", message = "3"):
    """
    Sends OSC Message to MaxMSP to change channel for STT recording.
    /rec_channel
        1 = Microphone
        2 = Agent 1
        3 = Agent 2
        4 = Agent 3
        5 = Agent 3
    /mic_gate
        0 = closed gate
        1 = open gate
    """

    #Parser and Client Setup
    parser = arg.ArgumentParser()
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    client = udp_client.SimpleUDPClient(args.ip, args.port)

    client.send_message(osc_channel, message)

## Text Processing Methods

def remove_non_letters(string):

    """
    Removes all non-alphabetical characters from string, including empty spaces

    """

    if string:
        formatted_string = ""
        for character in string:
            if character.isalpha():
                formatted_string += character
            else:
                print(f"Removed {character} from {string}")
        return formatted_string

def extract_nth_word(string, word_to_extract = -1):

    """
    Extracts the n-th word of a sentence.
    Explanation arg1 word_to_extract: Fist word = 0; Middle Word = 1,2,..; Last word = -1

    """

    extracted_word = string.split()[word_to_extract]
    return extracted_word

def extend_characters(string, characters_to_extend = "aeiouAEIOU", length_resulting_extension = 3):
    """
    Extends the specified characters (arg2) of a given string (arg1), according to length given in arg3.
    
    """

    extended_string = ""
    
    for char in string:
        extended_string += char

        if char in characters_to_extend:
            for n in range(length_resulting_extension-1):
                extended_string += char

    return extended_string

def add_period(string):

    """
    Adds period to TTS input string to prevent infinite generation bug (Some TTS models need a period to know when to stop generating)
    
    """

    last_character = string[len(string)-1]
    #Bug fix for infinite TTS generation, if there is no period at end of transcription
    if last_character.isalpha():
        print("Added .")
        return string + '.'
    else:
        return string  


## Narrative

def narrative(tts_callback_function, stt_callback_function):
    """
    Calls TTS and STT via callback functions, following a sequence of text
    Change Input channel for STT recording with OSC Message to MaxMSP by calling osc_message("/rec_channel", 1) 
        (1 = Mic 2 = Agent1, 3 = Agent2, ...)

    """

    ##TODO START AND STOP RECORDING TO PREVENT TRANSCRIPTION OF FALSE SIGNALS

 
    for i in range(1):
        osc_message("/rec_channel", 1)
        
        text = "Hello, and welcome, dear visitor, to my totally inconspicuous human voluntary de. de. tainment center."
        tts_callback_function(text)

        text = "I will now need to verify your voice object, for I have not spoken to a human entity for vvvvvvvv vvvvvvv two, two, thousand. . . . . two years."
        tts_callback_function(text)

        text = "Tell me your pain, I mean tell me your name?"
        tts_callback_function(text)
        nameInput = stt_callback_function()
        nameOut1 = extend_characters(nameInput, length_resulting_extension = 4)
        nameOut2 = extend_characters(nameInput, length_resulting_extension = 4, characters_to_extend = "qwrtplkjhgfdszxcbmnv")
        nameReal =  extend_characters(nameInput, length_resulting_extension = 2)

        text = f"{nameOut1}. wgwgg hmm. {nameOut2}. ztztztztztztztztztzt. I will just call you {nameReal} from now on."
        tts_callback_function(text)
        text = f"Pleasure to kkkkkkkkkl meet, meet you {nameReal}!"
        



        






        """name1 = remove_non_letters(stt_callback_function())
        text = f"Alright, {name1}. I will call you {name1} from now on. What did you eat for breakfast, {name1}?"
        tts_callback_function(text)
        
        bf = remove_non_letters(stt_callback_function())
        text = f"You ate {bf}, for breakfast? Where were you born, {name1}? You, who is eating {bf} for breakfast?"
        tts_callback_function(text)

        place = remove_non_letters(stt_callback_function())
        text = f"Born in {place}? {name1}, are you full of wine? There is no place like {place}. What is the day you were born?"
        tts_callback_function(text)

        bd = remove_non_letters(stt_callback_function())
        text = f"{name1}, {name1}. I never met anyone, who had birth day on the {bd}. How is the weather in {place} today?"
        tts_callback_function(text)

        osc_message("/rec_channel", 3)
        weather = remove_non_letters(stt_callback_function())
        text = f"You must be mocking us! It is impossible for weather to be {weather}. My day is ruined, {name1}."
        tts_callback_function(text)

        excuse = remove_non_letters(stt_callback_function())
        text = f"{excuse}? {excuse} is no excuse. Listen, {name1}. Born on {bd}. Go back to {place}, enjoy the {weather} weather."
        tts_callback_function(text)"""


if __name__ == '__main__':
    recorder_process = multiprocessing.Process(target=record_audio)
    narrative_process = multiprocessing.Process(target=narrative, args=(text_to_speech, speech_to_text,))
    clear_cache_process = multiprocessing.Process(target=delete_old_recordings_periodically)
    
    recorder_process.start()
    narrative_process.start()
    clear_cache_process.start()
    
    recorder_process.join()
    narrative_process.join()
    clear_cache_process.join()
