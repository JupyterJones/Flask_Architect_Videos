import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
from sys import argv
def transcribe_audio(path):
    r = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = r.record(source)  # read the entire audio file

        try:
            # recognize speech using Google Speech Recognition
            text = r.recognize_google(audio)
            print("Transcription: " + text)
            return text
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return None

def split_and_transcribe(path):
    sound = AudioSegment.from_mp3(path)

    # split on silence
    chunks = split_on_silence(sound, 
        # experiment with this value for your target audio file
        min_silence_len=500,  # in milliseconds
        # adjust this per requirement
        silence_thresh=sound.dBFS-14, 
        # keep the silence for 1 second, adjustable as well
        keep_silence=500
    )

    whole_text = ""
    for i, chunk in enumerate(chunks):
        chunk_filename = f"chunk{i}.wav"
        chunk.export(chunk_filename, format="wav")
        text = transcribe_audio(chunk_filename)
        if text:
            whole_text += text + " "

    return whole_text

if __name__ == "__main__":
    mp3_file = argv[1]  # Replace with your MP3 file path
    transcribed_text = split_and_transcribe(mp3_file)
    if transcribed_text:
        print("\nCombined Transcription:")
        print(transcribed_text)