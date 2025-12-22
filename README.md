# Oral Assignment Grader

A web-based application for recording, transcribing, and automatically grading oral quiz responses using AI. Built with Flask and integrated with Anthropic's Claude API for intelligent grading.

## Features

- User registration and authentication system
- Video recording interface with camera/microphone setup
- Automatic speech-to-text transcription using OpenAI Whisper
- AI-powered grading using Claude API with detailed feedback
- 7-category grading rubric for psychology quizzes
- PDF export of grading results
- Quiz history tracking for students
- Host/admin dashboard to view all submissions
- Customizable grading prompts for instructors

## Prerequisites

Before running this application, ensure you have the following installed:

- **Python 3.8+**
- **FFmpeg** (required for audio extraction from video files)
- **Anthropic API Key** (for AI grading functionality)

### Installing FFmpeg

**Windows:**
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract the zip file and add the `bin` folder to your system PATH
3. Verify installation: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

## Installation

1. **Clone the repository**
```bash
git clone https://github.com/AlinaHyk/CS290_Final_project.git
cd CS290_Final_project
```

2. **Create a virtual environment**
```bash
python -m venv .venv
```

3. **Activate the virtual environment**

**Windows:**
```bash
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

4. **Install Python dependencies**
```bash
pip install flask werkzeug
pip install openai-whisper
pip install moviepy
pip install requests
pip install reportlab
```

5. **Set up environment variables**

Create a `.env` file in the project root or set the environment variable directly:

**Windows (Command Prompt):**
```bash
set ANTHROPIC_API_KEY=your_api_key_here
```

**Windows (PowerShell):**
```bash
$env:ANTHROPIC_API_KEY="your_api_key_here"
```

**macOS/Linux:**
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

To get an Anthropic API key, visit [console.anthropic.com](https://console.anthropic.com/)

## Running the Application

1. **Ensure your virtual environment is activated**

2. **Run the Flask application**
```bash
python main.py
```

3. **Open your browser and navigate to:**
```
http://localhost:5000
```

## Usage

### For Students

1. **Register an account** at `/register`
2. **Login** with your credentials
3. **Allow camera and microphone access** when prompted
4. **Answer the 10 psychology quiz questions** orally
5. **Submit your recording** for automatic grading
6. **View your results** with detailed feedback, scores, and transcript
7. **Download a PDF report** of your submission
8. **Check your history** to see past submissions

### For Instructors/Hosts

1. **Login with host credentials:**
   - Username: `Host_AJ`
   - Password: `12345`

2. **Dashboard:** View all student submissions with scores and timestamps
3. **Settings:** Customize the AI grading prompt and rubric
4. **Users:** View all registered students and their submission counts

## Project Structure

```
CS290_Final_project/
├── main.py                 # Main Flask application
├── templates/              # HTML templates
│   ├── index.html         # Main quiz interface
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── results.html       # Detailed results page
│   ├── history.html       # User submission history
│   ├── host_dashboard.html # Admin dashboard
│   ├── host_settings.html  # Grading settings
│   └── host_users.html     # User management
├── static/
│   ├── css/
│   │   └── style.css      # Application styles
│   └── js/
│       └── recorder.js    # Video recording logic
├── data/                   # User data and submissions
│   ├── users.json         # User accounts (hashed passwords)
│   └── {submission_id}.json # Individual submission data
└── uploads/                # Video files and transcripts
    └── {timestamp}_{id}/
        ├── recording_{id}.webm
        ├── audio_{id}.mp3
        └── transcript_{id}.txt
```

## Default Quiz Questions

The application includes 10 psychology quiz questions covering topics such as:
- Classical vs. Operant Conditioning
- Cognitive Dissonance
- Maslow's Hierarchy of Needs
- Memory Systems
- Bystander Effect
- Psychological Approaches
- Erikson's Psychosocial Development
- Confirmation Bias
- Motivation Types
- Amygdala and Emotional Processing

## Grading Rubric

The AI grades responses based on 7 categories (100 points total):
1. **Conceptual Understanding** (20 points)
2. **Application of Theories** (15 points)
3. **Use of Terminology** (15 points)
4. **Critical Thinking** (15 points)
5. **Clarity of Explanation** (15 points)
6. **Completeness** (10 points)
7. **Examples and Evidence** (10 points)

## Troubleshooting

**Issue: Audio extraction fails**
- Ensure FFmpeg is installed and accessible in your system PATH
- Verify installation: `ffmpeg -version`

**Issue: Transcription is slow**
- The first run downloads the Whisper model (several hundred MB)
- Subsequent runs will be faster
- Consider using a smaller Whisper model by changing `base` to `tiny` in main.py

**Issue: Grading returns mock data**
- Verify your `ANTHROPIC_API_KEY` environment variable is set correctly
- Check your API key has sufficient credits
- Review console output for API error messages

**Issue: Video recording not working**
- Ensure you're accessing the app via `localhost` (not 127.0.0.1)
- Grant camera and microphone permissions when prompted
- Use a modern browser (Chrome, Firefox, Edge)

## Credits

Created by Joseph Slade and Alina Hyk for CS 290

## License

Educational project for Oregon State University