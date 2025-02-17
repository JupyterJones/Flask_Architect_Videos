import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from moviepy.editor import (
    AudioFileClip,
    VideoFileClip,
    concatenate_audioclips,
    AudioClip,
    ImageClip,
    CompositeVideoClip
)
import moviepy.video.fx.all as vfx
from icecream import ic

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key in production

# Define directories for uploads and output video
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'static'
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

@app.route('/')
def index():
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
            return redirect(request.url)
        
        video_file = request.files['video']
        audio_file = request.files['audio']
        
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
            return redirect(url_for('index'))
        
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
        ic("Video processing completed successfully.")
        
        # Optionally, remove uploaded files if no longer needed:
        # os.remove(video_path)
        # os.remove(audio_path)
        
        flash("Video processed successfully!")
        return redirect(url_for('index'))
    
    except Exception as e:
        ic("An error occurred during processing.", exc_info=True)
        flash("An error occurred during processing. Please check the logs for more details.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5200)
