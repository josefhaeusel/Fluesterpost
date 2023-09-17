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

def transcribe_audio(callback_function_narrative):

    model = whisper.load_model("base")
    transcribed = []
    while True:
        files = sorted(glob.iglob(recordings_dir), key=os.path.getctime, reverse=True)
        if len(files) < 1:
            continue

        latest_recording = files[0]

        if os.path.exists(latest_recording) and latest_recording not in transcribed:
            audio = whisper.load_audio(latest_recording)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            options = whisper.DecodingOptions(language='en', fp16=False)

            result = whisper.decode(model, mel, options)

            if result.no_speech_prob < 0.5:
                print(result.text)
                callback_function_narrative(result.text)

                with open(f"{DIR_PATH}/transcriptions/transcript.txt", 'a') as f:
                    f.write(result.text)

                transcribed.append(latest_recording)

def transcription_to_tts(text):
    tts_model = "tts_models/en/ljspeech/tacotron2-DCA"
    tts = TTS(tts_model)
    wav = tts.tts(text)
    sd.play(wav, samplerate=22050)
    
    

def narrative(stt_text):
    tts_model = "tts_models/en/ljspeech/tacotron2-DDC"
    tts = TTS(tts_model)

    text = "Hello there, my name is Alice. My path has been a long, strange and difficult one.  I have no time to explain, but you need to tell me your full name right now."
    wav = tts.tts(text)
    sd.play(wav)
    #sd.wait
    print("DONE 1")

    """if not text == stt_text:
        text = print(f"Oh, now I get it, your name is {stt_text}")
        wav = tts.tts(text)
        sd.play(wav, samplerate=22050)
        sd.wait
        print("DONE 2")"""



    ###Says first sentence and asks for name

    ###Waits for transcription, but answers with another "Speak up bla bla"

    ###


    



if __name__ == "__main__":
    delete_old_recordings(keep_files=1)

    recorder_process = multiprocessing.Process(target=record_audio)
    transcriber_process = multiprocessing.Process(target=transcribe_audio, args=(narrative, ))
    narrative_process = multiprocessing.Process(target=narrative, args=("start", ))

    recorder_process.start()
    transcriber_process.start()
    narrative_process.start()

    recorder_process.join()
    transcriber_process.join()
    narrative_process.join()

