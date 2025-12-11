"""
- User registration and login system
- Host admin panel (Host_AJ / 12345)
- 10 Psychology quiz questions
- 7-category grading breakdown
- PDF export of results
- Quiz history tracking
- Custom LLM system prompts (host configurable)
- Anthropic API key via environment variable
"""

import os
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
import subprocess

# For audio extraction
try:
    from moviepy.editor import VideoFileClip
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy import VideoFileClip
        HAS_MOVIEPY = True
    except ImportError:
        HAS_MOVIEPY = False

# For speech-to-text
import whisper

# For HTTP requests to LLM
import requests

# For PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_FOLDER'] = 'data'
app.config['USERS_FILE'] = 'data/users.json'
app.config['SETTINGS_FILE'] = 'data/host_settings.json'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# Host credentials
HOST_USERNAME = "Host_AJ"
HOST_PASSWORD = "12345"

# Load Whisper model
print("Loading Whisper model... (this may take a moment)")
whisper_model = whisper.load_model("base")
print("Whisper model loaded!")


DEFAULT_GRADING_RUBRIC = """
You are an expert psychology instructor grading oral quiz responses. 
Grade the student's responses based on this detailed rubric:

GRADING CRITERIA (100 points total):

1. CONCEPTUAL UNDERSTANDING (20 points)
   - 20: Demonstrates deep understanding of psychological concepts
   - 15: Good understanding with minor gaps
   - 10: Basic understanding present
   - 5: Limited understanding
   - 0: No understanding demonstrated

2. APPLICATION OF THEORIES (15 points)
   - 15: Correctly applies psychological theories to examples
   - 12: Mostly correct application
   - 8: Some correct applications
   - 4: Rarely applies theories correctly
   - 0: No correct application

3. USE OF TERMINOLOGY (15 points)
   - 15: Accurate and consistent use of psychological terms
   - 12: Mostly accurate terminology
   - 8: Some correct terms used
   - 4: Rarely uses correct terminology
   - 0: No appropriate terminology

4. CRITICAL THINKING (15 points)
   - 15: Shows excellent analysis and evaluation
   - 12: Good analytical skills
   - 8: Some analysis present
   - 4: Limited critical thinking
   - 0: No critical thinking demonstrated

5. CLARITY OF EXPLANATION (15 points)
   - 15: Exceptionally clear and well-organized
   - 12: Clear with good organization
   - 8: Mostly clear
   - 4: Difficult to follow
   - 0: Incomprehensible

6. COMPLETENESS (10 points)
   - 10: All questions fully answered with depth
   - 8: Most questions answered completely
   - 5: Partial answers to most questions
   - 2: Many questions incomplete
   - 0: Most questions unanswered

7. EXAMPLES AND EVIDENCE (10 points)
   - 10: Provides relevant, specific examples
   - 8: Good examples given
   - 5: Some examples provided
   - 2: Few or weak examples
   - 0: No examples given

GRADING INSTRUCTIONS:
1. Evaluate each response against the questions asked
2. Assign points for each of the 7 categories
3. Provide specific feedback on strengths
4. Provide specific suggestions for improvement
5. Give overall comments summarizing performance

Format your response as JSON with these exact keys:
{
    "total_score": <number>,
    "category_scores": {
        "conceptual_understanding": <number out of 20>,
        "application_of_theories": <number out of 15>,
        "use_of_terminology": <number out of 15>,
        "critical_thinking": <number out of 15>,
        "clarity_of_explanation": <number out of 15>,
        "completeness": <number out of 10>,
        "examples_and_evidence": <number out of 10>
    },
    "grading_reasoning": "<detailed explanation of how you arrived at each score>",
    "strengths": ["strength 1", "strength 2", ...],
    "improvements": ["improvement 1", "improvement 2", ...],
    "overall_comments": "<summary feedback>"
}
"""

QUIZ_QUESTIONS = [
    {
        "id": 1,
        "question": "Explain the difference between classical conditioning and operant conditioning. Provide an example of each.",
        "points": 10
    },
    {
        "id": 2,
        "question": "What is cognitive dissonance? Describe a situation where someone might experience it and how they might resolve it.",
        "points": 10
    },
    {
        "id": 3,
        "question": "Describe Maslow's hierarchy of needs and explain why the order of the levels matters.",
        "points": 10
    },
    {
        "id": 4,
        "question": "What is the difference between short-term memory and long-term memory? How does information transfer between them?",
        "points": 10
    },
    {
        "id": 5,
        "question": "Explain the bystander effect and describe the psychological factors that contribute to it.",
        "points": 10
    },
    {
        "id": 6,
        "question": "What are the main differences between the psychoanalytic and humanistic approaches to psychology?",
        "points": 10
    },
    {
        "id": 7,
        "question": "Describe the stages of Erikson's psychosocial development theory. Focus on two stages and their key conflicts.",
        "points": 10
    },
    {
        "id": 8,
        "question": "What is confirmation bias and how does it affect decision-making in everyday life?",
        "points": 10
    },
    {
        "id": 9,
        "question": "Explain the difference between intrinsic and extrinsic motivation. Which is generally more effective for long-term behavior change and why?",
        "points": 10
    },
    {
        "id": 10,
        "question": "What is the role of the amygdala in emotional processing? How does it interact with the prefrontal cortex?",
        "points": 10
    }
]


# USER MANAGEMENT FUNCTIONS
def load_users():
    """Load users from JSON file"""
    if os.path.exists(app.config['USERS_FILE']):
        with open(app.config['USERS_FILE'], 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file"""
    with open(app.config['USERS_FILE'], 'w') as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_host_settings():
    """Load host settings including custom prompt"""
    if os.path.exists(app.config['SETTINGS_FILE']):
        with open(app.config['SETTINGS_FILE'], 'r') as f:
            return json.load(f)
    return {"custom_prompt": ""}

def save_host_settings(settings):
    """Save host settings"""
    with open(app.config['SETTINGS_FILE'], 'w') as f:
        json.dump(settings, f, indent=2)

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def host_required(f):
    """Decorator to require host login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_host'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User and host login page"""
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Check for host login
        if username == HOST_USERNAME and password == HOST_PASSWORD:
            session['user'] = HOST_USERNAME
            session['is_host'] = True
            return redirect(url_for('host_dashboard'))
        
        # Check for regular user login
        users = load_users()
        if username in users and users[username]['password'] == hash_password(password):
            session['user'] = username
            session['is_host'] = False
            return redirect(url_for('index'))
        
        error = "Invalid username or password"
    
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        
        if not username or not password:
            error = "Username and password are required"
        elif password != confirm:
            error = "Passwords do not match"
        elif username == HOST_USERNAME:
            error = "This username is reserved"
        else:
            users = load_users()
            if username in users:
                error = "Username already exists"
            else:
                users[username] = {
                    'password': hash_password(password),
                    'created': datetime.now().isoformat(),
                    'submissions': []
                }
                save_users(users)
                session['user'] = username
                session['is_host'] = False
                return redirect(url_for('index'))
    
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))


#Main stuff
@app.route('/')
@login_required
def index():
    """Main recording page"""
    if session.get('is_host'):
        return redirect(url_for('host_dashboard'))
    return render_template('index.html', questions=QUIZ_QUESTIONS, username=session['user'])

@app.route('/api/questions')
@login_required
def get_questions():
    """Return quiz questions as JSON"""
    return jsonify(QUIZ_QUESTIONS)

#Uploading prosessing:
@app.route('/upload', methods=['POST'])
@login_required
def upload_video():
    """Handle video upload and processing"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video_file = request.files['video']
    username = session['user']
    
    if video_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    submission_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    submission_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{submission_id}")
    os.makedirs(submission_dir, exist_ok=True)
    
    try:
        # Save video
        mp4_filename = f"recording_{submission_id}.webm"
        mp4_path = os.path.join(submission_dir, mp4_filename)
        video_file.save(mp4_path)
        print(f"Video saved: {mp4_path} ({os.path.getsize(mp4_path)} bytes)")
        
        # Extract audio
        mp3_filename = f"audio_{submission_id}.mp3"
        mp3_path = os.path.join(submission_dir, mp3_filename)
        
        try:
            extract_audio(mp4_path, mp3_path)
            print(f"Audio saved: {mp3_path}")
        except Exception as audio_error:
            print(f"Audio extraction failed: {audio_error}")
            return jsonify({'error': f'Audio extraction failed: {str(audio_error)}. Make sure FFmpeg is installed.'}), 500
        
        # Generate transcript
        try:
            transcript = transcribe_audio(mp3_path)
            print(f"Transcript generated: {len(transcript)} characters")
        except Exception as transcribe_error:
            print(f"Transcription failed: {transcribe_error}")
            transcript = "[Transcription failed - audio may be silent or corrupted]"
        
        transcript_filename = f"transcript_{submission_id}.txt"
        transcript_path = os.path.join(submission_dir, transcript_filename)
        with open(transcript_path, 'w') as f:
            f.write(transcript)
        
        # Grade with LLM
        grading_result = grade_with_llm(transcript, QUIZ_QUESTIONS)
        
        # Save submission data
        submission_data = {
            'submission_id': submission_id,
            'username': username,
            'timestamp': timestamp,
            'timestamp_readable': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            'files': {
                'video': mp4_path,
                'audio': mp3_path,
                'transcript': transcript_path
            },
            'transcript_text': transcript,
            'grading_result': grading_result,
            'questions': QUIZ_QUESTIONS
        }
        
        data_path = os.path.join(app.config['DATA_FOLDER'], f"{submission_id}.json")
        with open(data_path, 'w') as f:
            json.dump(submission_data, f, indent=2)
        
        # Update user's submission history
        users = load_users()
        if username in users:
            users[username]['submissions'].append(submission_id)
            save_users(users)
        
        return jsonify({
            'success': True,
            'submission_id': submission_id,
            'transcript': transcript,
            'grading_result': grading_result
        })
        
    except Exception as e:
        print(f"Error processing submission: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


#Two options audioe extracitons
def extract_audio(video_path, audio_path):
    """Extract audio from video file (WebM or MP4)"""
    
    # Method 1: Use FFmpeg directly (best for WebM)
    try:
        # First, check if ffmpeg exists
        check = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
        if check.returncode == 0:
            # FFmpeg exists, try to extract audio
            result = subprocess.run([
                'ffmpeg', 
                '-i', video_path,
                '-vn',                    # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-ab', '128k',            # Bitrate
                '-ar', '44100',           # Sample rate
                '-ac', '2',               # Stereo
                '-y',                     # Overwrite
                audio_path
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(audio_path):
                print(f"Audio extracted successfully with FFmpeg")
                return
            else:
                print(f"FFmpeg stderr: {result.stderr}")
    except FileNotFoundError:
        print("FFmpeg not found in PATH")
    except subprocess.TimeoutExpired:
        print("FFmpeg timed out")
    except Exception as e:
        print(f"FFmpeg error: {e}")
    
    # Method 2: Try MoviePy as fallback
    if HAS_MOVIEPY:
        try:
            video = VideoFileClip(video_path)
            if video.audio is not None:
                video.audio.write_audiofile(audio_path, codec='mp3', verbose=False, logger=None)
                video.close()
                print(f"Audio extracted successfully with MoviePy")
                return
            else:
                video.close()
                print("MoviePy: No audio track found in video")
        except Exception as e:
            print(f"MoviePy error: {e}")
            
    raise RuntimeError(
        "Could not extract audio from video. Please ensure FFmpeg is installed: "
    )
            
def transcribe_audio(audio_path):
    """Transcribe audio to text using Whisper"""
    result = whisper_model.transcribe(audio_path)
    return result['text']    


#LLM call

def grade_with_llm(transcript, questions):
    """Grade transcript using LLM"""
    # Load custom prompt if set by host
    settings = load_host_settings()
    custom_prompt = settings.get('custom_prompt', '').strip()
    
    # Use custom prompt if available, otherwise use default
    rubric = custom_prompt if custom_prompt else DEFAULT_GRADING_RUBRIC
    
    questions_text = "\n".join([
        f"Q{q['id']}: {q['question']} ({q['points']} points)"
        for q in questions
    ])
    
    prompt = f"""
{rubric}       

QUIZ QUESTIONS:
{questions_text}

STUDENT'S ORAL RESPONSES (TRANSCRIPT):
{transcript}

Please grade this submission and provide detailed feedback in the JSON format specified above.
Include detailed grading_reasoning explaining how you evaluated each category.
"""
    
    # Try Anthropic API
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if api_key:
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-sonnet-4-20250514',
                    'max_tokens': 3000,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
                try:
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        return json.loads(json_match.group())
                except:
                    pass
                return {'raw_feedback': content, 'total_score': 'See feedback'}
        except Exception as e:
            print(f"LLM API error: {e}")
    
    # Fallback mock grading
    return generate_mock_grade(transcript)
