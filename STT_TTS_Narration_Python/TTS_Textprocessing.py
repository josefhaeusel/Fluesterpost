import sounddevice as sd
from TTS.api import TTS


def text_to_speech(text):

    """
    Synthesizes input string into speech, plays soundfile and waits till done.
    Output can get routed to Max (Ch.2), to get Vocoder Sound

    """

    tts_model = "tts_models/en/ljspeech/glow-tts"
    tts = TTS(tts_model)

    wav = tts.tts(text)
    sd.play(wav, samplerate=22050)
    sd.wait()


"""
SECTION I       //////////////      //////////////      //////////////      //////////////

    Functions to amalgamate input string for TTS to get desired effects, based on established vocabulary.


"""


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




"""
SECTION II      //////////////      //////////////      //////////////      //////////////

    Vocabulary of interesting, faulty, gitchy sound-manupulations for glow-tts model

    Structure for each category:
    -Vocabulary
    -Example Sentences for demonstration    //    Extracts and Prototyping from and for Narrative

"""

#####  0 - Name of Narrator "jjjjjjj"
## Name of Narrator
text_to_speech("j. jj. jjj. jjjj. jjjjj. jjjjjj. jjjjjjj. jjjjjjjj. jjjjjjjjj. jjjjjjjjjj. jjjjjjjjjjj. jjjjjjjjjj. jjjjjjjjjjjjjjjjjjj")
## Vowel Effects
##TODO Fill in Pascals test sounds

#####  1 - Breathing Sounds
##  Vocabulary
text_to_speech("ghhh.")
text_to_speech("hhh.")              #Breathing
text_to_speech("khk. kkk")
text_to_speech("vvvv. vvvvvvvvv.")  #Error Feel
text_to_speech("ccć.")
text_to_speech("äüöäöäöäüäöüöäöüäö!")
##  Example Sentences
text_to_speech("Hello, hhh, my name is jjjjjjjjjjjjj. hhhh I mean, jjjjj. ghhh. jjjjjj. jjjjjjjjjj. ffff! j. jj. j. jjj. jjjjjj")


#####  2 - Biological / Pre-lingual / Animalic
##  Vocabulary
text_to_speech("kkkkkl")            #Hiccup
text_to_speech("rhrhrhr")           #Gurgle
text_to_speech("lklkklklkllkl")     #Cough, Swallow Fail (very variable)

text_to_speech("scscscscsscsc")     #Insect Sound
text_to_speech("ztztztzt")          #Synth Sound / Insect
text_to_speech("wgwwwg")            #Uhuu



#####   3 - Glitches / Synth-Sounds / Electronic
##  Vocabulary
text_to_speech("shshsshs")          #Laser Effecgt
text_to_speech("pfpfpfpf")          #Synth Sound
text_to_speech("ztztztzt")          #Synth Sound / Insect


#####   4 - Emotional / Humorous / Expressive
##  Vocabulary
text_to_speech("qqqqqqq. qqqqqq. ttttttt. hahahaha. qqqq. qqqqq.")        #Laughing
text_to_speech("tttttttt")          #Laughing
text_to_speech("wwwwwwww.")         #Whirrel
text_to_speech("yyyyyyyyyyyy.")     #Eyeyeyeyeyey
text_to_speech("wgwgggwwwwwwg")     #Confusion






