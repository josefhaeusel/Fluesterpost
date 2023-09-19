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

DIR_PATH = pathlib.Path(__file__).parent.resolve()
recordings_dir = os.path.join(f'{DIR_PATH}/recordings/', '*')



def delete_old_recordings(keep_files):
    #Delete old files in recordings directory
    files = sorted(glob.iglob(recordings_dir), key=os.path.getctime)
    old_files = files[:len(files)-keep_files]

    for file_to_delete in old_files:
        try:
            os.remove(file_to_delete)
            print(f"Deleted: {file_to_delete}")
        except OSError as e:
            print(f"Error deleting {file_to_delete}: {e}")

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
    while not transcription_done:
        print("Transcribing...")
        files = sorted(glob.iglob(recordings_dir), key=os.path.getctime, reverse=True)

        latest_recording = files[0]

        if os.path.exists(latest_recording) and latest_recording not in transcribed:
            audio = whisper.load_audio(latest_recording)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            options = whisper.DecodingOptions(language='en', fp16=False)

            result = whisper.decode(model, mel, options)

            if result.no_speech_prob < 0.9:

                with open(f"{DIR_PATH}/transcriptions/transcript.txt", 'a') as f:
                    f.write(result.text)
    
                transcribed.append(latest_recording)
                transcription_done = True
        
    print("\n\nTRANSCRIPTION DONE:", result.text, "\n\n")
    return result.text

def remove_non_letters(string):
    last_character = string[len(string)-1]
    if last_character.isalpha():
        return string
    else:
        string = string[:len(string)-1]
        print(f"Removed {last_character}")
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
        text = f"{name1}. {name1}, {name1}. what did you eat for breakfast?"
        tts_callback_function(text)
        
        bf = remove_non_letters(stt_callback_function())
        text = f"{bf}, {bf}, {bf}. For breakfast? What is your birthday?"
        tts_callback_function(text)

        bd = remove_non_letters(stt_callback_function())
        text = f"{bd}. I never met anyone, who hat birth day on the {bd}. Have you?"
        tts_callback_function(text)

        name2 = remove_non_letters(stt_callback_function())
        text = f"Are you full of wine? I am speaking to you {name2}, {name2} {name2}? Tell me where you were born!"
        tts_callback_function(text)

        place = remove_non_letters(stt_callback_function())
        text = f"Are you full of wine? There is no place like {place}, {place}, {place}."
        tts_callback_function(text)


    



if __name__ == "__main__":
    delete_old_recordings(keep_files=1)

    recorder_process = multiprocessing.Process(target=record_audio)
    #speech_to_text_process = multiprocessing.Process(target=speech_to_text, args=(text_to_speech,))
    narrative_process = multiprocessing.Process(target=narrative, args=(text_to_speech, speech_to_text, ))

    recorder_process.start()
    #speech_to_text_process.start()
    narrative_process.start()

    recorder_process.join()
    #speech_to_text_process.join()
    narrative_process.join()
