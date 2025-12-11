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

