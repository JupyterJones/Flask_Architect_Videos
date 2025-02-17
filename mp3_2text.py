import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
from sys import argv
def transcribe_audio(path):
    r = sr.Recognizer()
    try:
        with sr.AudioFile(path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
    except Exception as e: # Catch any other exceptions
        print(f"An unexpected error occurred during transcription: {e}")
    return None

def split_and_transcribe(path, output_file="transcription.txt"):
    try:
        sound = AudioSegment.from_mp3(path)
    except Exception as e:
        print(f"Error loading MP3 file: {e}")
        return

    chunks = split_on_silence(sound,
        min_silence_len=500,
        silence_thresh=sound.dBFS-14,
        keep_silence=500
    )

    whole_text = ""
    for i, chunk in enumerate(chunks):
        chunk_filename = f"chunk{i}.wav"
        chunk.export(chunk_filename, format="wav")
        text = transcribe_audio(chunk_filename)
        if text:
            whole_text += text + " "

    if whole_text:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(whole_text)
            print(f"Transcription saved to {output_file}")
        except Exception as e:
            print(f"Error writing to file: {e}")
    else:
        print("No text transcribed.")


if __name__ == "__main__":
    mp3_file = argv[1] # Get file path from user
    output_filename = input("Enter the desired output filename (e.g., transcription2.txt): ") or "transcription.txt" # Get output filename, default to "transcription.txt"

    split_and_transcribe(mp3_file, output_filename)