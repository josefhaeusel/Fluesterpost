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
import simpleaudio as sa
from TTS.api import TTS

ssl._create_default_https_context = ssl._create_unverified_context

DIR_PATH = pathlib.Path(__file__).parent.resolve()
recordings_dir = os.path.join(f'{DIR_PATH}/recordings/', '*')
recordings_dir_os = f'{DIR_PATH}/recordings/'
samples_dir = f'{DIR_PATH}/samples'



def delete_old_recordings():
    while True:
        files = os.listdir(recordings_dir_os)
        files = [os.path.join(recordings_dir_os, file) for file in files]
        files = sorted(files, key=os.path.getctime)
        old_files = files[:len(files)-5]
        if len(files) >= 10:
            for file_to_delete in old_files:
                try:
                    os.remove(file_to_delete)
                    print(f"Deleted: {file_to_delete}")
                except OSError as e:
                    print(f"Error deleting {file_to_delete}: {e}")
        time.sleep(60)
        
        

def record_audio():
    freq = 44100
    duration = 3

    while True:
        ts = datetime.datetime.now()
        filename = ts.strftime("%Y-%m-%d %H:%M:%S")
        recording = sd.rec(int(duration * freq), samplerate=freq, channels=1)
        sd.wait()
        wv.write(f"{DIR_PATH}/recordings/{filename}.wav", recording, freq, sampwidth=2)

def speech_to_text():
    transcription_done = False
    model = whisper.load_model("base")
    transcribed = []
    sample_ids = [0,1,2,3,4]
    rdm.shuffle(sample_ids)
    zero_time = time.time()

    while not transcription_done:
        current_time = time.time()
        elapsed_time = current_time - zero_time
        print("Transcribing...")
        files = sorted(glob.iglob(recordings_dir), key=os.path.getctime, reverse=True)
        latest_recording = files[0]

        #Trigger "I can't hear you sample" (and similar) after 8 seconds
        if elapsed_time >= 10:
            if sample_ids:
                sample_id = sample_ids[0]
                sample = f"{samples_dir}/no_answer_sample{sample_id}.wav"
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
            options = whisper.DecodingOptions(language='en', fp16=False, temperature=0.5, sample_len = 15, suppress_blank=True )

            result = whisper.decode(model, mel, options)

            if result.no_speech_prob < 0.75:

                with open(f"{DIR_PATH}/transcriptions/transcript.txt", 'a') as f:
                    f.write(result.text)

                transcribed.append(latest_recording)
                transcription_done = True
        
    print("\n\nTRANSCRIPTION DONE:", result.text, "\n\n")
    return result.text

def remove_non_letters(string):
    if string:
        last_character = string[len(string)-1]
        if last_character.isalpha():
            return string
        else:
            string = string[:len(string)-1]
            print(f"Removed {last_character}")
            return string
    return string

def add_period(string):
    last_character = string[len(string)-1]
    #Bug fix for infinite TTS generation, if there is no period at end of transcription
    if last_character.isalpha():
        print("Added .")
        return string + '.'
    else:
        return string  

def text_to_speech(text):
    text = add_period(text)
    tts_model = "tts_models/en/ljspeech/glow-tts"
    tts = TTS(tts_model)

    wav = tts.tts(text)
    sd.play(wav, samplerate=22050)
    sd.wait()

def narrative(tts_callback_function, stt_callback_function):

    ## Send Text to TTS Callback Function
    text = "Tell me your name, tell me your name."
    tts_callback_function(text)

    for i in range(4):
        ## Call speech-to-text(), remove_non_letters right away
        name1 = remove_non_letters(stt_callback_function())
        text = f"Alright, {name1}. what did you eat for breakfast, {name1}?"
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

        weather = remove_non_letters(stt_callback_function())
        text = f"You must be mocking us! It is impossible for weather to be {weather}. My day is ruined, {name1}."
        tts_callback_function(text)


if __name__ == "__main__":

    recorder_process = multiprocessing.Process(target=record_audio)
    narrative_process = multiprocessing.Process(target=narrative, args=(text_to_speech, speech_to_text, ))
    clear_cache_process = multiprocessing.Process(target=delete_old_recordings)
    
    recorder_process.start()
    narrative_process.start()
    clear_cache_process.start()
    
    recorder_process.join()
    narrative_process.join()
    clear_cache_process.join()
