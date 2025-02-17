from flask import Flask, request, send_file, render_template, redirect, jsonify, url_for, send_from_directory,flash
import os
import numpy as np
import wave
from balacoon_tts import TTS
from pydub import AudioSegment
import glob
import shutil
from icecream import ic
from moviepy.editor import (
    ImageClip,
    VideoClip,
    clips_array,
    concatenate_videoclips,
    CompositeVideoClip,
    AudioClip,   
    ColorClip,
    VideoFileClip,
    AudioFileClip,
    concatenate_audioclips,
    TextClip, 
    ImageSequenceClip
)
import moviepy.editor as mpy
import cv2
import moviepy.video.fx.all as vfx
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import random
import uuid
import json
import subprocess
from datetime import datetime
from pydub import AudioSegment
import datetime
import time
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flashing messages
# Initialize Balacoon TTS with the predetermined model and voice
tts = TTS("en_us_hifi_jets_cpu.addon")
OUTPUT_DIR = 'static/text2audio'
# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
# Define directories for uploads and output video
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/projects'
ALLOWED_AUDIO_EXTENSIONS = {'mp3'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4'}
# Ensure necessary directories exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    ic(f"Created upload folder: {UPLOAD_FOLDER}")
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    ic(f"Created output folder: {OUTPUT_FOLDER}")

def allowed_file(filename, allowed_set):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

# Select the first available speaker
PREDETERMINED_SPEAKER = tts.get_speakers()[0]

@app.route('/')
def index():
    videos = get_videos()
    return render_template('index.html', videos=videos)

@app.route('/view_videos')
def view_videos():
    videos = get_videos()
    return render_template('view_videos.html', videos=videos)

# Route to process a large text file
@app.route('/convert_large_text', methods=['POST', 'GET'])
def convert_large_text():
    if request.method == 'GET':
        # Render a simple form to upload the file
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Upload Text File</title>
        </head>
        <body>
            <h1>Upload Text File</h1>
            <a href="/list_audio_files">list existing files</a>
            <form action="/convert_large_text" method="post" enctype="multipart/form-data">
                <input type="file" name="text_file" accept=".txt">
                <button type="submit">Convert</button>
            </form>
        </body>
        </html>
        '''
    elif request.method == 'POST':
        if 'text_file' not in request.files:
            return "No file part", 400

        text_file = request.files['text_file']
        if text_file.filename == '':
            return "No selected file", 400

        # Read and process the text file
        text_content = text_file.read().decode('utf-8')
        paragraphs = text_content.split("\n\n")  # Split on double newlines

        audio_files = []
        for idx, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue  # Skip empty paragraphs

            # Generate TTS samples
            samples = tts.synthesize(paragraph, PREDETERMINED_SPEAKER)
            sampling_rate = tts.get_sampling_rate()

            # Create unique filenames for the audio
            wav_filename = f"paragraph_{idx+1}.wav"
            wav_file_path = os.path.join(OUTPUT_DIR, wav_filename)

            # Save the audio as a WAV file
            with wave.open(wav_file_path, "w") as wav_file:
                wav_file.setparams((1, 2, sampling_rate, len(samples), "NONE", "NONE"))
                wav_file.writeframes(samples)

            # Convert to MP3 with volume boost
            audio = AudioSegment.from_wav(wav_file_path)
            louder_audio = audio + 6  # Increase volume by 6 dB
            mp3_filename = f"paragraph_{idx+1}.mp3"
            mp3_file_path = os.path.join(OUTPUT_DIR, mp3_filename)
            louder_audio.export(mp3_file_path, format="mp3")

            audio_files.append(mp3_filename)

        return render_template('audio_files.html', audio_files=audio_files)

@app.route('/list_audio_files')
def list_audio_files():
    audio_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.mp3')]
    audio_files = sorted(audio_files, key=lambda f: os.path.getctime(os.path.join(OUTPUT_DIR, f)))
    return render_template('list_audio_files.html', audio_files=audio_files)

@app.route('/download_audio/<filename>')
def download_audio(filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, mimetype='audio/mpeg')
    return "File not found", 404
OUTPUT_DIR = "static/text2audio"

@app.route('/balacoon', methods=['GET', 'POST'])  
def balacoon():  
    audio_files = []  
    supported_speakers = tts.get_speakers()  # Retrieve supported speakers  

    if request.method == 'POST':  
        balacoon_speaker = request.form.get('bal_speaker', str(supported_speakers))  # Default to the last speaker  
        text = request.form['text']  
        lines = text.split("\n")  

        for line in lines:  
            if line.strip():  # Ignore empty lines  
                speaker = balacoon_speaker  # Get speaker from form input  
                samples = tts.synthesize(line, speaker)  

                # Create a unique filename keep only last 25 characters of line
                line = line[-25:]
                filename = line.replace(" ", "_").replace(".", "").replace(",", "").replace("!", "") +speaker + ".wav"
                output_file_path = os.path.join(OUTPUT_DIR, filename)  

                # Save the synthesized audio to a WAV file  
                with wave.open(output_file_path, "w") as fp:  
                    fp.setparams((1, 2, tts.get_sampling_rate(), len(samples), "NONE", "NONE"))  
                    fp.writeframes(samples)  

                # Load the WAV file and increase the volume  
                audio = AudioSegment.from_wav(output_file_path)  
                louder_audio = audio + 6  # Increase volume by 6 dB  
                # Save the louder audio as an MP3 file  
                mp3_filename = "louder_" + filename.replace('.wav', '.mp3')  
                louder_audio.export(os.path.join(OUTPUT_DIR, mp3_filename), format="mp3")  
                #copy the results to static/ouput
                shutil.copy(os.path.join(OUTPUT_DIR, mp3_filename), os.path.join('static/projects', mp3_filename)) 
                #shutil.copy(os.path.join(OUTPUT_DIR, mp3_filename), os.path.join('static/text2audio', mp3_filename)) 
                audio_files.append(mp3_filename)  
        # Retrieve the supported speakers (you may want to keep this in the app's context)  
        supported_speakers = tts.get_speakers()  
        return render_template('balacoon.html', audio_files=get_balacoon_audio_files(), supported_speakers=supported_speakers,image_files=get_balacoon_image_files())  
    # Retrieve the supported speakers (you may want to keep this in the app's context)  
    supported_speakers = tts.get_speakers()  
    return render_template('balacoon.html', audio_files=get_balacoon_audio_files(), supported_speakers=supported_speakers,image_files=get_balacoon_image_files())

def get_balacoon_audio_files():  
    audio_files = glob.glob('static/text2audio/*.mp3')
    # sort by creation date in descending order
    audio_files.sort(key=os.path.getmtime, reverse=True)
    return audio_files  

def get_balacoon_image_files():
    #image_files=glob.glob("static/novel_images/*.jpg")
    image_files=glob.glob("static/square/*.jpg")+glob.glob("static/square/*.png")
    # sort by creation date in descending order
    image_files.sort(key=os.path.getmtime, reverse=True)
    return image_files

def get_videos():
    video_files = glob.glob("static/projects/*.mp4")
    video_files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(file) for file in video_files]


@app.route('/balacoon_download/<filename>')  
def balacoon_download_file(filename):  
    return send_file(os.path.join(OUTPUT_DIR, filename), as_attachment=True)  


@app.route('/combine_b', methods=['POST'])
def combine_b():
    image_path = request.form.get('image_path')
    audio_path = request.form.get('audio_path')

    if not image_path or not audio_path:
        return jsonify({"success": False, "error": "Missing image or audio file."})

    # Extract filenames
    image_filename = os.path.basename(image_path)
    audio_filename = os.path.basename(audio_path)

    # Define full paths
    image_full_path = os.path.join("static/square", image_filename)
    audio_full_path = os.path.join("static/text2audio", audio_filename)
    output_video_path = os.path.join("static/projects", "output_video.mp4")

    # ------------------ Get Exact Audio Duration (Including Silence) ------------------
    try:
        audio_clip = AudioFileClip(audio_full_path)
        audio_duration = audio_clip.duration + 0.5  # Add 0.25s before & after
        audio_clip.close()
    except Exception as e:
        return jsonify({"success": False, "error": f"MoviePy error: {e}"})

    # ------------------ FFmpeg Command ------------------
    ffmpeg_command = [
        "ffmpeg",
        "-loop", "1",
        "-i", image_full_path,
        "-i", audio_full_path,
        "-i", "static/assets/staacor.png",

        # Filter complex for padding silence and overlaying image
        "-filter_complex",
        "[1:a] asetpts=PTS-STARTPTS [orig_audio];"
        "aevalsrc=0:d=0.25 [silence_pre];"
        "aevalsrc=0:d=0.25 [silence_post];"
        "[silence_pre][orig_audio][silence_post] concat=n=3:v=0:a=1 [padded_audio];"
        "[0:v][2:v] overlay=0:0 [v]",  # Overlay the border

        "-map", "[v]",  # Video output
        "-map", "[padded_audio]",  # Padded audio output
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",

        # Set video duration to match exact audio length
        "-t", str(audio_duration),
        "-movflags", "+faststart",
        "-y",
        output_video_path
    ]

    # ------------------ Run FFmpeg ------------------
    try:
        subprocess.run(ffmpeg_command, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "error": f"FFmpeg error: {e}"})

    # ------------------ Copy Output Video to Different Locations ------------------
    uid = uuid.uuid4().hex
    shutil.copy(output_video_path, f"static/projects/{uid}.mp4")
    shutil.copy(output_video_path, f"static/videos/{uid}.mp4")

    return jsonify({"success": True, "output_video": url_for('static', filename=f'projects/{uid}.mp4')})



def add_sound_to_image(image_path, audio_path):
    try:
        # Ensure absolute paths
        image_path = os.path.abspath(image_path)
        audio_path = os.path.abspath(audio_path)

        # Set output path in the correct folder
        output_filename = f"{os.path.basename(image_path).rsplit('.', 1)[0]}_audio.mp4"
        output_path = os.path.join(os.getcwd(), "static/projects", output_filename)

        ic(f"Absolute Image Path: {image_path}")
        ic(f"Absolute Audio Path: {audio_path}")
        ic(f"Output Video Path: {output_path}")

        # Check if both files exist
        if not os.path.exists(image_path) or not os.path.exists(audio_path):
            ic("Error: One or both files do not exist!")
            return None

        # Load image and audio
        image_clip = ImageClip(image_path)
        audio_clip = AudioFileClip(audio_path)

        # Ensure the image has a size
        if image_clip.size is None:
            ic("Error: Image does not have a valid size")
            return None

        # Match the duration of the image to the audio
        image_clip = image_clip.set_duration(audio_clip.duration)

        # Set FPS to avoid codec issues
        video_clip = image_clip.set_audio(audio_clip).set_fps(24)

        # Ensure the output folder exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Export video
        video_clip.write_videofile(output_path, codec="libx264", fps=24)

        return output_path
    except Exception as e:
        ic(f"Error creating video: {str(e)}")
        return None

VIDEO_FOLDER = "static/projects"

@app.route("/delete", methods=["GET", "POST"])
def delete_videos():
    VIDEO_FOLDER = os.path.join(app.static_folder, "projects")
    video_files = [f for f in os.listdir(VIDEO_FOLDER) if f.endswith(".mp4")]

    if request.method == "POST":
        selected_videos = request.form.getlist("videos_to_delete")

        if not selected_videos:
            flash("No videos selected for deletion.", "warning")
            return redirect(url_for("delete_videos"))

        for video in selected_videos:
            video_path = os.path.join(VIDEO_FOLDER, video)
            if os.path.exists(video_path):
                os.remove(video_path)
                flash(f"Deleted: {video}", "success")

        return redirect(url_for("delete_videos"))

    return render_template("delete.html", videos=video_files)
# Directory paths
#VIDEO_DIRS = 'static/videos/'
VIDEO_DIRS = 'static/projects/'
PROJECTS_DIR = 'static/projects/'
VIDEO_SOURCE = 'static/videos/'
@app.route('/video_selection', methods=['GET', 'POST'])
def video_selection():
    # Get list of MP4 files in the videos directory, sorted by creation time (newest first)
    video_files = sorted(
        [f for f in os.listdir(VIDEO_DIRS) if f.endswith('.mp4')],
        key=lambda f: os.path.getctime(os.path.join(VIDEO_DIRS, f)),
        reverse=True
    )

    if request.method == 'POST':
        # Get selected video filenames from the form
        selected_videos = [
            request.form.get('video1'),
            request.form.get('video2'),
            request.form.get('video3'),
            request.form.get('video4')
        ]

        # Filter out None or empty selections
        selected_videos = [v for v in selected_videos if v]
        if not selected_videos:
            return "No videos selected", 400

        clips = []
        target_size = (512, 768)  # Uniform size for all videos

        for video in selected_videos:
            clip = VideoFileClip(os.path.join(VIDEO_DIRS, video))

            # Resize the clip to ensure uniform dimensions
            resized_clip = clip.resize(newsize=target_size)

            # Ensure audio exists and matches duration
            if resized_clip.audio:
                adjusted_audio = resized_clip.audio.set_duration(resized_clip.duration)
                resized_clip = resized_clip.set_audio(adjusted_audio)

            clips.append(resized_clip)

            # Create a 0.25s silent audio clip
            silence_duration = 0.25
            fps = 44100  # Standard audio sampling rate
            silent_audio = AudioClip(lambda t: np.zeros((1,)), duration=silence_duration, fps=fps)

            # Create a black silent video clip
            silent_clip = VideoFileClip(os.path.join(VIDEO_DIRS, video)).subclip(0, 0.25).without_audio()
            silent_clip = silent_clip.set_audio(silent_audio)

            clips.append(silent_clip)

        # Concatenate the clips with small pauses
        final_clip = concatenate_videoclips(clips, method="compose")

        # Save the concatenated video
        output_path = os.path.join(PROJECTS_DIR, 'joined_mp4.mp4')
        final_clip.write_videofile(output_path, codec='libx264', fps=24, audio_codec='aac')

        # Close all clips to free resources
        for clip in clips:
            clip.close()

        # Save a UUID-named copy of the concatenated video
        uid = str(uuid.uuid4())
        shutil.copy(output_path, os.path.join(PROJECTS_DIR, f'{uid}.mp4'))

        # Redirect to the projects page or display success message
        return redirect(url_for('video_selection'))

    # Render the selection page with available videos
    return render_template('selections.html', video_files=video_files)



# Ensure the recordings directory exists
RECORDINGS_DIR = "static/recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)

@app.route('/record')
def record():
    # Get list of saved audio files
    audio_files = sorted(glob.glob(os.path.join(RECORDINGS_DIR, "*.mp3")), reverse=True)
    audio_files = [os.path.basename(file) for file in audio_files]
    return render_template('record.html', audio_files=audio_files)



    return render_template('record.html')

@app.route('/save_audio', methods=['POST'])
def save_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file found"}), 400

    audio_file = request.files['audio']
    
    # Generate a unique filename
    filename = f"recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    file_path = os.path.join(RECORDINGS_DIR, filename)

    # Convert WebM/OGG to MP3 if needed
    temp_path = file_path.replace('.mp3', '.wav')
    audio_file.save(temp_path)
    sound = AudioSegment.from_file(temp_path)
    sound.export(file_path, format="mp3")

    # Remove temp file
    os.remove(temp_path)

    # Get only filenames instead of full paths
    audio_files = [os.path.basename(f) for f in glob.glob(os.path.join(RECORDINGS_DIR, '*.mp3'))]

    return render_template('record.html', audio_files=audio_files)
@app.route('/adjusted_index')
def adjusted_index():
    """Render the index page with the upload form and preview elements."""
    return render_template('adjusted_index.html')

@app.route('/adjusted_process', methods=['POST'])
def adjusted_process():
    """Process the uploaded video and audio files to generate a new video with a transparent frame overlay."""
    try:
        # Validate the file upload parts
        if 'video' not in request.files or 'audio' not in request.files:
            flash('Missing video or audio file in the request.')
            ic("No file part in the request.")
            ic(request.files)
            return redirect(request.url)
        
        video_file = request.files['video']
        audio_file = request.files['audio']
        ic(f"video_file: , {video_file}")
        ic(f"audio_file: , {audio_file}")    
        if video_file.filename == '' or audio_file.filename == '':
            flash('No file selected for one of the fields.')
            ic("No selected file.")
            return redirect(request.url)
        
        # Check allowed file types
        if not (allowed_file(video_file.filename, ALLOWED_VIDEO_EXTENSIONS) and 
                allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS)):
            flash('Invalid file type. Please upload an MP4 video and an MP3 audio file.')
            ic("Invalid file type.")
            return redirect(request.url)
        
        # Save the uploaded files securely
        video_filename = secure_filename(video_file.filename)
        audio_filename = secure_filename(audio_file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        audio_path = os.path.join(UPLOAD_FOLDER, audio_filename)
        ic(f"Saving video file to {video_path}")
        ic(f"Saving audio file to {audio_path}")
        video_file.save(video_path)
        audio_file.save(audio_path)
        ic(f"Saved video file to {video_path}")
        ic(f"Saved audio file to {audio_path}")
        
        # ---------------------------
        # AUDIO PROCESSING
        # ---------------------------
        ic("Loading audio file.")
        audio_clip = AudioFileClip(audio_path)
        original_audio_duration = audio_clip.duration
        ic(f"Original audio duration: {original_audio_duration:.2f} seconds")
        
        # Define the duration for silence at start and tail
        silence_duration = 0.25
        
        # Create a 0.25-second silent audio clip using a lambda that returns zero amplitude
        ic("Creating a 0.25-second silent audio clip.")
        def make_silence(t):
            return 0
        
        silent_clip = AudioClip(make_silence, duration=silence_duration)
        silent_clip.fps = audio_clip.fps  # Match the frame rate
        
        # Extract the last 0.25 second of the original audio. If the audio is shorter than 0.25 sec, use the entire clip.
        if original_audio_duration < silence_duration:
            ic("Audio is shorter than 0.25 seconds. Using the full audio as tail.")
            tail_clip = audio_clip
        else:
            ic("Extracting the last 0.25 second of the audio.")
            tail_clip = audio_clip.subclip(original_audio_duration - silence_duration, original_audio_duration)
        
        # Concatenate: 0.25-sec silence + original audio + 0.25-sec tail of the original audio
        ic("Concatenating silent clip, original audio, and tail clip.")
        processed_audio = concatenate_audioclips([silent_clip, audio_clip, tail_clip])
        processed_audio_duration = processed_audio.duration
        ic(f"Processed audio duration: {processed_audio_duration:.2f} seconds")
        
        # ---------------------------
        # VIDEO PROCESSING
        # ---------------------------
        ic("Loading video file.")
        video_clip = VideoFileClip(video_path)
        original_video_duration = video_clip.duration
        ic(f"Original video duration: {original_video_duration:.2f} seconds")
        
        # Calculate the speed factor needed to match video duration with the processed audio duration.
        speed_factor = original_video_duration / processed_audio_duration
        ic(f"Calculated speed factor: {speed_factor:.4f}")
        
        # Adjust the video speed using the calculated factor.
        ic("Adjusting video speed.")
        video_clip_adjusted = video_clip.fx(vfx.speedx, factor=speed_factor)
        
        # Overlay the processed audio on the video.
        ic("Setting the processed audio as the video's audio.")
        video_clip_adjusted = video_clip_adjusted.set_audio(processed_audio)
        
        # ---------------------------
        # OVERLAY TRANSPARENT PNG FRAME
        # ---------------------------
        frame_path = os.path.join("static", "assets", "staacor.png")
        if not os.path.exists(frame_path):
            ic(f"Frame file not found at {frame_path}")
            flash("Transparent frame file not found. Please check the file path.")
            return redirect(url_for('adjusted_index'))
        
        ic("Loading transparent PNG frame.")
        frame_clip = ImageClip(frame_path)
        # Set the duration and resize to match the video dimensions
        frame_clip = frame_clip.set_duration(video_clip_adjusted.duration)
        frame_clip = frame_clip.resize(video_clip_adjusted.size)
        
        ic("Compositing the video with the transparent frame overlay.")
        final_video = CompositeVideoClip([video_clip_adjusted, frame_clip.set_position("center")])
        
        # ---------------------------
        # OUTPUT THE FINAL VIDEO
        # ---------------------------
        output_video_path = os.path.join(OUTPUT_FOLDER, 'adjustedspeed.mp4')
        ic(f"Writing output video to {output_video_path}")
        final_video.write_videofile(output_video_path, codec='libx264', audio_codec='aac')
        # shuti copy to OUTPUT_FOLDER with a uuid
        uuid = str(uuid.uuid4())
        output_video_path = os.path.join(OUTPUT_FOLDER, f"{uuid}adjustedspeed.mp4")
        ic(f"Writing output video to {output_video_path}")
        shutil.copyfile(output_video_path, output_video_path)
        ic("Video processing completed successfully.")
        
        # Optionally, remove uploaded files if no longer needed:
        # os.remove(video_path)
        # os.remove(audio_path)
        
        flash("Video processed successfully!")
        return redirect(url_for('adjusted_index'))
    
    except Exception as e:
        ic("An error occurred during processing.")
        flash("An error occurred during processing. Please check the logs for more details.")
        return redirect(url_for('adjusted_index'))
#------------------------
def add_title_image(video_path, hex_color = "#A52A2A"):
    hex_color=random.choice(["#A52A2A","#ad1f1f","#16765c","#7a4111","#9b1050","#8e215d","#2656ca"])
    # Define the directory path
    directory_path = "temp"
    # Check if the directory exists
    if not os.path.exists(directory_path):
        # If not, create it
        os.makedirs(directory_path)
        print(f"Directory '{directory_path}' created.")
    else:
        print(f"Directory '{directory_path}' already exists.") 
    # Load the video file and title image
    video_clip = VideoFileClip(video_path)
    print(video_clip.size)
    # how do i get the width and height of the video
    width, height = video_clip.size
    get_duration = video_clip.duration
    print(get_duration, width, height)
    # Load the title image
    title_image_path = random.choice(glob.glob("static/assets/staacor.png"))
    #title_image_path = "static/assets/port-hole.png"
    # Set the desired size of the padded video (e.g., video width + padding, video height + padding)
    padded_size = (width + 50, height + 50)

    # Calculate the position for centering the video within the larger frame
    x_position = (padded_size[0] - video_clip.size[0]) / 2
    y_position = (padded_size[1] - video_clip.size[1]) / 2
    #hex_color = "#09723c"
    # Remove the '#' and split the hex code into R, G, and B components
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)

    # Create an RGB tuple
    rgb_tuple = (r, g, b)

    # Create a blue ColorClip as the background
    blue_background = ColorClip(padded_size, color=rgb_tuple)

    # Add the video clip on top of the red background
    padded_video_clip = CompositeVideoClip([blue_background, video_clip.set_position((x_position, y_position))])
    padded_video_clip = padded_video_clip.set_duration(video_clip.duration)
    #title_image_path = "/home/jack/Desktop/EXPER/static/assets/Title_Image02.png"
    # Load the title image
    title_image = ImageClip(title_image_path)

    # Set the duration of the title image
    title_duration = video_clip.duration
    title_image = title_image.set_duration(title_duration)

    print(video_clip.size)
    # Position the title image at the center and resize it to fit the video dimensions
    #title_image = title_image.set_position(("left", "top"))
    title_image = title_image.set_position((0, -5))
    #video_clip.size = (620,620)
    title_image = title_image.resize(padded_video_clip.size)

    # Position the title image at the center and resize it to fit the video dimensions
    #title_image = title_image.set_position(("center", "center")).resize(video_clip.size)

    # Create a composite video clip with the title image overlay
    composite_clip = CompositeVideoClip([padded_video_clip, title_image])
    # Limit the length to video duration
    composite_clip = composite_clip.set_duration(video_clip.duration)
    # Load a random background music
    mp3_files = glob.glob("static/music/*.mp3")
    random.shuffle(mp3_files)

    # Now choose a random MP3 file from the shuffled list
    mp_music = random.choice(mp3_files)
    get_duration = AudioFileClip(mp_music).duration
    # Load the background music without setting duration
    music_clip = AudioFileClip(mp_music)
    # Fade in and out the background music
    #music duration is same as video
    music_clip = music_clip.set_duration(video_clip.duration)
    # Fade in and out the background music
    fade_duration = 1.0
    music_clip = music_clip.audio_fadein(fade_duration).audio_fadeout(fade_duration)
    # Set the audio of the composite clip to the background music
    composite_clip = composite_clip.set_audio(music_clip)
    uid = str(uuid.uuid4()) 
    output_path = f'static/videos/final_output3{uid}.mp4'
    # Export the final video with the background music
    composite_clip.write_videofile(output_path)
    mp4_file =  f"static/vids/Ready_Post_{uid}.mp4"
    shutil.copyfile(output_path, mp4_file) 
    temp_vid="static/videos/temp.mp4"
    shutil.copyfile(output_path, temp_vid)    
    print(mp4_file)
    VIDEO = output_path
    return VIDEO

# Function to generate the pixel sorting transition
def generate_pixel_sorting(image1_path, image2_path, output_path, duration=5, fps=30):
    img1 = cv2.imread(image1_path)
    img2 = cv2.imread(image2_path)
    h, w = img1.shape[:2]

    frames = []
    total_frames = int(duration * fps)

    for i in range(total_frames):
        # Create a copy of the first image
        frame = img1.copy()

        # Sort pixels horizontally based on brightness
        progress = i / total_frames
        sorted_rows = int(h * progress)
        for row in range(sorted_rows):
            frame[row] = frame[row][frame[row][:, 0].argsort()]

        # Blend with the second image
        alpha = progress
        blended_frame = cv2.addWeighted(frame, 1 - alpha, img2, alpha, 0)
        frames.append(blended_frame)

    frames_rgb = [cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in frames]
    clip = ImageSequenceClip(frames_rgb, fps=fps)
    clip.write_videofile(output_path, codec="libx264")



@app.route("/zoom_effect", methods=["GET", "POST"])
def zoom_effect():
    video_path = None
    if request.method == "POST":
        # Ensure both images are provided
        if "image1" not in request.files or "image2" not in request.files:
            return "Both image1 and image2 must be provided", 400
        
        # Save uploaded images
        image1 = request.files["image1"]
        image2 = request.files["image2"]
        image1_path = os.path.join(UPLOAD_FOLDER, secure_filename(image1.filename))
        image2_path = os.path.join(UPLOAD_FOLDER, secure_filename(image2.filename))
        image1.save(image1_path)
        image2.save(image2_path)

        # Get parameters from the form
        transition_style = request.form.get("transition_style")
        duration = int(request.form.get("duration", 5))
        fps = int(request.form.get("fps", 30))

        # Generate the video
        output_path = os.path.join(OUTPUT_FOLDER, "output.mp4")
        if transition_style == "infinite_zoom":
            generate_infinite_zoom(image1_path, image2_path, output_path, duration=duration, fps=fps)
            #save a copy using uuid
            shutil.copy(output_path, os.path.join(OUTPUT_FOLDER, str(uuid.uuid4()) + "_output.mp4"))
        elif transition_style == "pixel_sorting":
            generate_pixel_sorting(image1_path, image2_path, output_path, duration=duration, fps=fps)
            #save a copy using uuid
            shutil.copy(output_path, os.path.join(OUTPUT_FOLDER, str(uuid.uuid4()) + "_output.mp4"))
        # Add a title frame to the video
        
        titled_video_path=add_title_image(video_path=output_path, hex_color="#A52A2A")
        #titled_video_path = os.path.join(OUTPUT_FOLDER, "titled_output.mp4")
        # Save copies of the last two generations
        shutil.copy(output_path, os.path.join(OUTPUT_FOLDER, "last_generation_no_title.mp4"))
        shutil.copy(titled_video_path, os.path.join(OUTPUT_FOLDER, "last_generation_with_title.mp4"))
        shutil.copy(titled_video_path, os.path.join(OUTPUT_FOLDER, "last_generation_with_title.mp4"))
    # Render the template with the video paths
    return render_template(
        "zoom_effect.html",
        video=video_path,
        last_no_title=os.path.join(OUTPUT_FOLDER, "last_generation_no_title.mp4"),
        last_with_title=os.path.join(OUTPUT_FOLDER, "last_generation_with_title.mp4")
    )
# Route to work with text
@app.route('/index_zoom')
def index_zoom():
    return render_template('index_zoom.html')    

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    file = request.files['image']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return jsonify({'filepath': filepath})

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    image_path = data['image_path']
    points = data['points']
    zoom_level = float(data['zoom'])  # Convert zoom_level to float
    
    output_video = os.path.join(VIDEO_FOLDER, 'zoom_animation.mp4')
    create_zoom_video(image_path, points, zoom_level, output_video)
    # save copy in the same folder with the same name and uuid
    uid = str(uuid.uuid4())
    output_videon = f'static/videos/final_output{uid}.mp4'
    shutil.copyfile(output_video, output_videon)
    video_path = output_video
    output_v = add_title_image(video_path, hex_color = "#A52A2A")
    shutil.copyfile(output_v, f'static/projects/final_output2{uid}.mp4')
    return jsonify({'video_path': output_v})

# Function to create zoom effect on a single point



def generate_frames(image_path, points, zoom_level, num_frames):
    """
    Generator function to yield frames one at a time.
    This avoids storing all frames in memory at once.
    """
    img = cv2.imread(image_path)
    h, w, _ = img.shape
    point = points[0]
    cx, cy = int(point[0] * w), int(point[1] * h)

    # Define the sharpening kernel
    sharpening_kernel = np.array([[0, -1, 0],
                                  [-1, 5, -1],
                                  [0, -1, 0]])

    for i in range(num_frames):
        alpha = (i / num_frames) ** 2  # Slow zoom at start, faster at end
        zoom_factor = 1 + alpha * zoom_level

        # Define the cropping region
        x1 = max(cx - int(w / (2 * zoom_factor)), 0)
        y1 = max(cy - int(h / (2 * zoom_factor)), 0)
        x2 = min(cx + int(w / (2 * zoom_factor)), w)
        y2 = min(cy + int(h / (2 * zoom_factor)), h)

        cropped = img[y1:y2, x1:x2]
        resized = cv2.resize(cropped, (w, h))

        # Apply sharpening to every 5th frame
        if i % 5 == 0:
            resized = cv2.filter2D(resized, -1, sharpening_kernel)

        # Yield the frame
        yield resized

        # Clean up intermediate variables
        del cropped, resized

        # Trigger garbage collection periodically
        if i % 50 == 0:
            gc.collect()

@app.route('/create_zoom_video', methods=['POST'])
def create_zoom_video_route():
    """
    Flask route to handle video creation requests.
    """
    try:
        # Parse input data
        data = request.json
        image_path = data.get('image_path')
        points = data.get('points')  # List of points (e.g., [[0.5, 0.5]])
        zoom_level = data.get('zoom_level', 2.0)  # Default zoom level
        output_video = data.get('output_video', 'output.mp4')

        # Validate inputs
        if not image_path or not points:
            return jsonify({"error": "Missing required parameters"}), 400

        # Number of frames for the video
        num_frames = 500

        # Generate frames using the generator
        frames_generator = generate_frames(image_path, points, zoom_level, num_frames)

        # Create video from frames
        process = psutil.Process()  # For memory profiling
        video = ImageSequenceClip(
            [cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames_generator], fps=30
        )
        video.write_videofile(output_video, codec='libx264')

        # Log memory usage after video creation
        memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB
        print(f"Memory usage after video creation: {memory_usage:.2f} MB")

        # Final garbage collection
        gc.collect()

        return jsonify({"message": "Video created successfully", "output_video": output_video}), 200

    except Exception as e:
        # Handle errors gracefully
        return jsonify({"error": str(e)}), 500

def create_zoom_video(image_path, points, zoom_level, output_video):
    img = cv2.imread(image_path)
    h, w, _ = img.shape
    frames = []
    num_frames = 500
    
    # Only using the first point
    point = points[0]
    cx, cy = int(point[0] * w), int(point[1] * h)
    
    # Define the sharpening kernel
    sharpening_kernel = np.array([[0, -1, 0],
                                  [-1, 5,-1],
                                  [0, -1, 0]])

    for i in range(num_frames):
        #alpha = i / num_frames
        alpha = (i / num_frames) ** 2  # This makes the zoom slower at the start and faster at the end

        zoom_factor = 1 + alpha * zoom_level
        
        # Define the cropping region
        x1 = max(cx - int(w / (2 * zoom_factor)), 0)
        y1 = max(cy - int(h / (2 * zoom_factor)), 0)
        x2 = min(cx + int(w / (2 * zoom_factor)), w)
        y2 = min(cy + int(h / (2 * zoom_factor)), h)
        cropped = img[y1:y2, x1:x2]
        resized = cv2.resize(cropped, (w, h))
        
        # Apply sharpening to every 5th frame
        if i % 5 == 0:  # Sharpen every 5th frame (adjust as needed)
            resized = cv2.filter2D(resized, -1, sharpening_kernel)
        
        frames.append(resized)
    
    # Save as video
    video = ImageSequenceClip([cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in frames], fps=30)
    video.write_videofile(output_video, codec='libx264')
    add_title_image(video_path=output_video)


@app.route('/video/<filename>')
def video(filename):
    return send_from_directory(VIDEO_FOLDER, filename)
#-------------------------

# Path to the uploads and output folders
UPLOAD_FOLDER = 'static/uploads/'
OUTPUT_FOLDER = 'static/uploads/'
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5100)
