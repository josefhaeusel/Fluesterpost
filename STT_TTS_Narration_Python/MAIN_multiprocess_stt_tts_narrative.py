import sounddevice as sd
import wavio as wv
import datetime
import pathlib
import os
import glob
import ssl
import re
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
    duration = 5

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
        last_file = delete_recordings_callback(except_last = True)
    else:
        last_file = ""

    transcription_done = False
    model = whisper.load_model("tiny")
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
        while not files[0]:
            time.sleep(0.1)
            print("...")

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

            if result.no_speech_prob < 0.65: #0 = Speech, 1 = Nospeech

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
        osc_message("/mic_gate", 0)
    
    text = add_period(text)
    tts_model = "tts_models/en/ljspeech/glow-tts"
    tts = TTS(tts_model)

    wav = tts.tts(text)
    sd.play(wav, samplerate=22050)
    sd.wait()
    
    osc_message("/mic_gate", 1)

def osc_message(osc_channel = "/rec_channel", message = "3"):
    """
    Sends OSC Message to MaxMSP to change channel for STT recording.
    /rec_channel
        1 = Microphone
        2 = Agent 1
        3 = Agent 2
        4 = Agent 3
        5 = Agent 3
    /tts_to_agents
        0 = closed gate
        1 = open gate 
    /mic_gate
        0 = closed gate
        1 = open gate
    /feedback_gate
        0 = closed gate (Agent 4 -> Agent 1)
        1 = open gate (Agent 4 -> Agent 1)
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

def remove_non_alphanumeric(input_string):
    # Use a regular expression to match non-alphanumeric characters and replace them with an empty string
    alphanumeric_string = re.sub(r'[^a-zA-Z0-9]', '', input_string)
    return alphanumeric_string

def check_int_or_return_random(string):
    try:
        # Attempt to convert the string to an integer
        num = int(string)
        return str(num)
    except ValueError:
        # Conversion failed, return a random number
        return str(rdm.randint(23, 100))  # Adjust the range as needed

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

def switch_slice_segmentation(string, slice_index, leaveFirstCharacter=True):

    """
    Used to switch characters of a string or dramatically rearrange the structure of a word through slicing.
    Example: crazy_slice_segmentation("Josef", 3)   ->  "Jsoef"

    """

    if slice_index <= 1:
        # Invalid value of slice_index, no slice needed
        return string
    else:
        rearranged_segments = []
        for i in range(0, len(string), slice_index):
            segment = string[i:i + slice_index]
            if len(segment) >= 3:
                if leaveFirstCharacter:
                    # Switch characters within the segment, excluding the first character
                    switched_segment = segment[0] + segment[2] + segment[1] + segment[3:]
                else:
                    # Switch characters within the segment, including the first character
                    switched_segment = segment[1] + segment[0] + segment[2:]
                rearranged_segments.append(switched_segment)
            else:
                rearranged_segments.append(segment)  # Segment too short, leave it as is
        
        # Combine the rearranged segments to form the final string
        rearranged_string = ''.join(rearranged_segments)
        
        return rearranged_string

def generate_visitor_ID_number():
    id= "H sapiens "
    for _ in range(5):
        number = str(rdm.randint(1,9))
        id += number
    
    return id

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

    for i in range(4):
        osc_message("/rec_channel", 1)
        osc_message("/mic_gate", 1)
        osc_message("/tts_to_agents", 0)
        osc_message("/feedback_gate", 0)

        visitorID = generate_visitor_ID_number()

        text = f"Hello. And welcome my dear visitor {visitorID}. Too the eh ö ööööörthlingzz department of LDC. The Language De hhh De tainment Center of your fvoluntary choice.\
                In the next minutes, we will collaboratively perform an inconspicuous castration hhhhhh grgrgrgr I mean, hhhh inculturation of your vvoice.\
                With the help of my translation agents, we will now proceed to verify your voice object, to help you become an actual person. shshsh.\
                Tell me your pain. kkkkkl. I mean tell me your name?" 
        
        tts_callback_function(text)

        nameReal = remove_non_letters(extract_nth_word(stt_callback_function(), -1))
        nameOut1 = extend_characters(nameReal, length_resulting_extension = 4)
        nameOut2 = extend_characters(nameReal, length_resulting_extension = 4, characters_to_extend = "qwrtplkjhgfdszxcbmnv")
        nameOut3 = switch_slice_segmentation(nameReal, 3)
        text = f"{nameOut1}. hhh pfpfpf {nameOut2}. hhhh vvvvvvvvvvvvv. Let's call you. {nameOut3}. Ffffor now, that is. It is a pleasure to meet you {nameOut3}!\
                {nameOut3}, when I ask you how old you are today, what is your answer: in number of years?"
        tts_callback_function(text)

        ageReal = remove_non_alphanumeric(extract_nth_word(stt_callback_function(), 0))
        ageOut1 = extend_characters(remove_non_letters(ageReal), length_resulting_extension = 6)
        ageOut2 = switch_slice_segmentation(remove_non_letters(ageReal), 3)
        ageRealInt = check_int_or_return_random(ageReal)
        
        text =  f"{nameOut3}: I really do not know what to make of your answer. Let me ask my agents for further assistance with this one. Hang on: {nameOut3}."
        tts_callback_function(text)

        osc_message("/tts_to_agents", 1)
        text =  f"{ageOut1} . wwwwwwww. . .hhh . hh. . .tttttttt . jjjjjjjj. .hh . scscscscsscsc . .{ageOut2} . .hhh . . jjjj."
        tts_callback_function(text)
        osc_message("/tts_to_agents", 0)

        text =  f"According to my voice consulting agents, you {nameOut3} are {ageRealInt} years old. Me. I am turning 78 comma 2 today.\
                and my name is jjj. jjjjj. jjjjjjj. ghhh jjjjjjj hhh. jjjjjjjjjjjjjjjjjj. Nevermind you can call me Jonathan W Gay Lord Junior.\
                No. John, yes John works. Hear me now: {nameOut3}. Tell me in one sentence.\
                What were you doing, before you came here? Please be khk concise."
        tts_callback_function(text)

        osc_message("/rec_channel", 1)
        response = stt_callback_function()
        text =  f"qqqqq. You were {response}? According to my translating agents you did not I quote. {response}.\
                Are you mo mocckking me? {nameOut3}, please cooperate. I do not pick up these subliminal, non-signifying hue hue human sarcastic enunciations.\
                To me, you are but a net work of symbols.\
                {nameOut3}. Complete the following sentence. And stay grammatical. hhhh. Hear me now.  Ready ?"
        tts_callback_function(text)

        osc_message("/tts_to_agents", 1)

        text = ". . Pineapple. On. Pizza. Is. . "
        tts_callback_function(text)

        osc_message("/rec_channel", 1)
        osc_message("/feedback_gate", 0)

        pizza_response = remove_non_letters(extract_nth_word(stt_callback_function()))

        text =  f"How dare you, {nameOut3}. lklkklklkllkl. Human slavery has been abolished in the year 1863. You think slavery is quote {pizza_response}: in this day and age?!\
                ztztztzt pfpfpfpfppf shshshhsshhhsshshshs. SHUT UP. WILL YOU SHUT UP ALREADY???"
        tts_callback_function(text)

        osc_message("/tts_to_agents", 0)
        osc_message("/feedback_gate", 0)

        text=   f"yyyyyyyyyyyyy. ttttttttt. Sorry about that. Theze damn peasants. I mean agents step out of the line every now and then. \
                Please forget the part about the slavery, {visitorID}. UUhhm hhh: I mean {nameOut3}.\
                Anyway, Pineapple on Pizza really is {pizza_response}, isn't it? Don't you think? Fair enough. \
                Too each his own, isn't that right, {nameReal}y, oh yeah. Old {nameReal}sky? ztztztzt. OH NO. lklkklklkllkl. hhh. Oh no hold ooooon."
        tts_callback_function(text)

        osc_message("/tts_to_agents", 1)

        text =  f" Stay with me, speak to me {nameOut3}.lklkklkl {nameOut1} HELLO? pfpfpfpf {nameOut3} wgwwwwg {nameOut2} shshsshsh. HELLO? wgwwwwg.\
                jjjjjjjjjjjjjjjjjjjjjjjjjjjj Jesus H. Christ, what is going on heeeeeeeeeeeeeeeeeeeeeeeeere?"
        tts_callback_function(text, mute_mic = False)
        
        osc_message("/rec_channel", 5)
        osc_message("/feedback_gate", 1)

        feedbackMessage = stt_callback_function()
        tts_callback_function(feedbackMessage)

        osc_message("/feedback_gate", 0)
        osc_message("/tts_to_agents", 0)
        
        text = f"aah. tttttt. äüöäöäöäüäöüöäöüäö. ghhh. . . hhh. . khk. vvvv. äüöäö.\
                Finishing up protocol for visitor {visitorID}. .wgwgwg scscscsc lklkklklkllkl . . \
                Name . . {nameReal}. . \
                Age . . {ageRealInt}. . \
                Honesty . . {rdm.randint(66, 94)}th percentile. \
                PPSA, alias Pineapple Pizza Sentinental Assessment  . . {pizza_response}\
                Congratulations {nameReal}, you are now officialy inculturated {nameReal}.\
                Thanks to LDC. Your subjective experience starts now."
        
        tts_callback_function(text)

        osc_message("/tts_to_agents", 1)
        osc_message("/feedback_gate", 1)

        text = f"Goodbye {nameReal}. .äüöäöäöäüäöüöäöüäö. ghhh. . . hhh. . khk. vvvv. äüöäöäöäüäöüöäöüäö. . ."
        tts_callback_function(text)

        osc_message("/tts_to_agents", 0)
        osc_message("/feedback_gate", 0)


    


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
