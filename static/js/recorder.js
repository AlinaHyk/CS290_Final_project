/**
 * ORAL ASSIGNMENT GRADER - Client-Side Recorder
 */


const AppState = {
    mediaStream: null,
    mediaRecorder: null,
    recordedChunks: [],
    currentQuestion: 0,
    totalQuestions: QUIZ_QUESTIONS.length,
    isRecording: false,
    recordingStartTime: null,
    timerInterval: null,
    submissionId: null
};

const Elements = {
    steps: {
        info: document.getElementById('step-info'),
        camera: document.getElementById('step-camera'),
        quiz: document.getElementById('step-quiz'),
        processing: document.getElementById('step-processing'),
        results: document.getElementById('step-results')
    },
    
    btnStartSetup: document.getElementById('btn-start-setup'),
    
    previewVideo: document.getElementById('preview-video'),
    cameraPlaceholder: document.getElementById('camera-placeholder'),
    cameraStatus: document.getElementById('camera-status'),
    micStatus: document.getElementById('mic-status'),
    btnEnableCamera: document.getElementById('btn-enable-camera'),
    btnStartQuiz: document.getElementById('btn-start-quiz'),
    
    recordingVideo: document.getElementById('recording-video'),
    questionDisplay: document.getElementById('question-display'),
    questionCounter: document.getElementById('question-counter'),
    questionPoints: document.getElementById('question-points'),
    progressFill: document.getElementById('progress-fill'),
    recordingIndicator: document.getElementById('recording-indicator'),
    recordingTime: document.getElementById('recording-time'),
    recordingTip: document.getElementById('recording-tip'),
    btnBeginRecording: document.getElementById('btn-begin-recording'),
    btnNextQuestion: document.getElementById('btn-next-question'),
    btnSubmit: document.getElementById('btn-submit'),
    
    processingStatus: document.getElementById('processing-status'),
    procSteps: {
        upload: document.getElementById('proc-upload'),
        audio: document.getElementById('proc-audio'),
        transcript: document.getElementById('proc-transcript'),
        grading: document.getElementById('proc-grading')
    },
    
    resultsContent: document.getElementById('results-content'),
    btnNewSubmission: document.getElementById('btn-new-submission'),
    btnDownloadPdf: document.getElementById('btn-download-pdf'),
    btnViewDetails: document.getElementById('btn-view-details')
};

function goToStep(stepName) {
    Object.values(Elements.steps).forEach(step => {
        step.classList.remove('active');
    });
    if (Elements.steps[stepName]) {
        Elements.steps[stepName].classList.add('active');
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateStatus(element, status, message) {
    element.className = 'status-item ' + status;
    const icon = status === 'success' ? '+' : status === 'error' ? 'x' : '...';
    element.innerHTML = `<span class="status-icon">${icon}</span><span>${message}</span>`;
}

// Step 1: Start Setup
Elements.btnStartSetup.addEventListener('click', () => {
    goToStep('camera');
});

// Step 2: Camera Setup
async function requestMediaAccess() {
    try {
        updateStatus(Elements.cameraStatus, 'waiting', 'Camera: Requesting...');
        updateStatus(Elements.micStatus, 'waiting', 'Microphone: Requesting...');
        
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            },
            audio: {
                echoCancellation: true,
                noiseSuppression: true
            }
        });
        
        AppState.mediaStream = stream;
        Elements.previewVideo.srcObject = stream;
        Elements.cameraPlaceholder.classList.add('hidden');
        
        updateStatus(Elements.cameraStatus, 'success', 'Camera: Connected');
        updateStatus(Elements.micStatus, 'success', 'Microphone: Connected');
        
        Elements.btnStartQuiz.disabled = false;
        Elements.btnEnableCamera.textContent = 'Camera Ready';
        Elements.btnEnableCamera.disabled = true;
        
    } catch (error) {
        console.error('Media access error:', error);
        
        let errorMessage = 'Unknown error';
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Permission denied';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'No camera/microphone found';
        }
        
        updateStatus(Elements.cameraStatus, 'error', `Camera: ${errorMessage}`);
        updateStatus(Elements.micStatus, 'error', 'Microphone: Failed');
        alert(`Could not access camera/microphone: ${errorMessage}`);
    }
}

Elements.btnEnableCamera.addEventListener('click', requestMediaAccess);

Elements.btnStartQuiz.addEventListener('click', () => {
    Elements.recordingVideo.srcObject = AppState.mediaStream;
    showQuestion(0);
    goToStep('quiz');
});

// Step 3: Quiz Recording
function showQuestion(index) {
    const question = QUIZ_QUESTIONS[index];
    
    Elements.questionDisplay.textContent = question.question;
    Elements.questionPoints.textContent = `${question.points} points`;
    
    Elements.questionCounter.textContent = `Question ${index + 1} of ${AppState.totalQuestions}`;
    Elements.progressFill.style.width = `${((index + 1) / AppState.totalQuestions) * 100}%`;
    
    if (index === AppState.totalQuestions - 1) {
        Elements.btnNextQuestion.classList.add('hidden');
        Elements.btnSubmit.classList.remove('hidden');
    } else {
        Elements.btnNextQuestion.classList.remove('hidden');
        Elements.btnSubmit.classList.add('hidden');
    }
}

function startRecording() {
    AppState.recordedChunks = [];
    
    // Try different codecs for better compatibility
    const mimeTypes = [
        'video/webm;codecs=vp9,opus',
        'video/webm;codecs=vp8,opus', 
        'video/webm;codecs=h264,opus',
        'video/webm',
        'video/mp4'
    ];
    
    let selectedMimeType = '';
    for (const mimeType of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mimeType)) {
            selectedMimeType = mimeType;
            console.log(`Using codec: ${mimeType}`);
            break;
        }
    }
    
    try {
        const options = selectedMimeType ? { mimeType: selectedMimeType } : {};
        AppState.mediaRecorder = new MediaRecorder(AppState.mediaStream, options);
        console.log(`MediaRecorder created with: ${AppState.mediaRecorder.mimeType}`);
    } catch (e) {
        console.log('Fallback to default MediaRecorder');
        AppState.mediaRecorder = new MediaRecorder(AppState.mediaStream);
    }
    
    AppState.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            AppState.recordedChunks.push(event.data);
            console.log(`Chunk recorded: ${event.data.size} bytes`);
        }
    };
    
    AppState.mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
    };
    
    AppState.mediaRecorder.start(1000);
    AppState.isRecording = true;
    
    Elements.recordingIndicator.classList.remove('hidden');
    Elements.btnBeginRecording.classList.add('hidden');
    Elements.btnNextQuestion.disabled = false;
    
    AppState.recordingStartTime = Date.now();
    AppState.timerInterval = setInterval(updateTimer, 1000);
    
    Elements.recordingTip.textContent = 'Recording in progress. Speak clearly into your microphone.';
}

function updateTimer() {
    const elapsed = Math.floor((Date.now() - AppState.recordingStartTime) / 1000);
    Elements.recordingTime.textContent = formatTime(elapsed);
}

function nextQuestion() {
    if (AppState.currentQuestion < AppState.totalQuestions - 1) {
        AppState.currentQuestion++;
        showQuestion(AppState.currentQuestion);
    }
}

async function submitRecording() {
    AppState.mediaRecorder.stop();
    AppState.isRecording = false;
    clearInterval(AppState.timerInterval);
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    goToStep('processing');
    await uploadVideo();
}

async function uploadVideo() {
    try {
        setProcessingStep('upload');
        Elements.processingStatus.textContent = 'Uploading video...';
        
        const videoBlob = new Blob(AppState.recordedChunks, { type: 'video/webm' });
        
        const formData = new FormData();
        formData.append('video', videoBlob, 'recording.webm');
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`);
        }
        
        setProcessingStep('audio');
        Elements.processingStatus.textContent = 'Extracting audio...';
        await new Promise(r => setTimeout(r, 800));
        
        setProcessingStep('transcript');
        Elements.processingStatus.textContent = 'Generating transcript...';
        await new Promise(r => setTimeout(r, 800));
        
        setProcessingStep('grading');
        Elements.processingStatus.textContent = 'AI grading in progress...';
        
        const result = await response.json();
        
        if (result.success) {
            AppState.submissionId = result.submission_id;
            displayResults(result);
        } else {
            throw new Error(result.error || 'Unknown error');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        alert(`Error uploading video: ${error.message}`);
        goToStep('quiz');
    }
}

function setProcessingStep(currentStep) {
    const steps = ['upload', 'audio', 'transcript', 'grading'];
    
    steps.forEach((step, index) => {
        const element = Elements.procSteps[step];
        const currentIndex = steps.indexOf(currentStep);
        
        if (index < currentIndex) {
            element.className = 'processing-step complete';
        } else if (index === currentIndex) {
            element.className = 'processing-step active';
        } else {
            element.className = 'processing-step';
        }
    });
}

function displayResults(result) {
    const grading = result.grading_result;
    const score = grading.total_score;
    
    let scoreClass = 'score-low';
    if (score >= 80) scoreClass = 'score-high';
    else if (score >= 60) scoreClass = 'score-medium';
    
    let resultsHtml = `
        <div class="results-summary">
            <div class="score-display ${scoreClass}">
                <span class="big-score">${score}</span>
                <span class="score-max">/ 100</span>
            </div>
            <h3>Grading complete, ${USERNAME}!</h3>
        </div>
        <div class="results-sections">
    `;
    
    // Category scores
    if (grading.category_scores) {
        const maxScores = {
            'conceptual_understanding': 20,
            'application_of_theories': 15,
            'use_of_terminology': 15,
            'critical_thinking': 15,
            'clarity_of_explanation': 15,
            'completeness': 10,
            'examples_and_evidence': 10
        };
        
        resultsHtml += `<div class="result-section">
            <h4>Score Breakdown</h4>
            <div class="mini-breakdown">`;
        for (const [category, catScore] of Object.entries(grading.category_scores)) {
            const maxScore = maxScores[category] || 15;
            resultsHtml += `<div class="mini-score-item">
                <span class="mini-cat">${category.replace(/_/g, ' ')}</span>
                <span class="mini-val">${catScore}/${maxScore}</span>
            </div>`;
        }
        resultsHtml += `</div></div>`;
    }
    
    // Strengths
    if (grading.strengths && grading.strengths.length) {
        resultsHtml += `<div class="result-section">
            <h4>Strengths</h4>
            <ul>${grading.strengths.map(s => `<li>${s}</li>`).join('')}</ul>
        </div>`;
    }
    
    // Improvements
    if (grading.improvements && grading.improvements.length) {
        resultsHtml += `<div class="result-section">
            <h4>Areas for Improvement</h4>
            <ul>${grading.improvements.map(i => `<li>${i}</li>`).join('')}</ul>
        </div>`;
    }
    
    // Note
    if (grading.note) {
        resultsHtml += `<div class="result-section note">
            <p><strong>Note:</strong> ${grading.note}</p>
        </div>`;
    }
    
    resultsHtml += `</div>`;
    
    Elements.resultsContent.innerHTML = resultsHtml;
    Elements.btnDownloadPdf.href = `/download-pdf/${result.submission_id}`;
    Elements.btnViewDetails.href = `/results/${result.submission_id}`;
    
    goToStep('results');
}

// Event Listeners
Elements.btnBeginRecording.addEventListener('click', startRecording);
Elements.btnNextQuestion.addEventListener('click', nextQuestion);
Elements.btnSubmit.addEventListener('click', submitRecording);

Elements.btnNewSubmission.addEventListener('click', () => {
    AppState.currentQuestion = 0;
    AppState.recordedChunks = [];
    AppState.isRecording = false;
    
    Elements.btnBeginRecording.classList.remove('hidden');
    Elements.recordingIndicator.classList.add('hidden');
    Elements.btnNextQuestion.disabled = true;
    
    showQuestion(0);
    goToStep('info');
});

// Styles for results
const resultsStyles = document.createElement('style');
resultsStyles.textContent = `
    .results-summary {
        text-align: center;
        margin-bottom: var(--space-xl);
    }
    
    .score-display {
        display: inline-flex;
        align-items: baseline;
        gap: 0.25rem;
        padding: var(--space-lg) var(--space-xl);
        border-radius: var(--radius-lg);
        margin-bottom: var(--space-md);
    }
    
    .score-display.score-high {
        background: rgba(46, 125, 50, 0.2);
        color: #66BB6A;
    }
    
    .score-display.score-medium {
        background: rgba(249, 168, 37, 0.2);
        color: #F9A825;
    }
    
    .score-display.score-low {
        background: rgba(198, 40, 40, 0.2);
        color: #EF5350;
    }
    
    .big-score {
        font-size: 3rem;
        font-weight: 700;
    }
    
    .score-max {
        font-size: 1.5rem;
        opacity: 0.7;
    }
    
    .results-sections {
        display: grid;
        gap: var(--space-lg);
    }
    
    .result-section {
        background: var(--color-bg-dark);
        padding: var(--space-lg);
        border-radius: var(--radius-md);
    }
    
    .result-section h4 {
        margin-bottom: var(--space-md);
        color: var(--color-primary-light);
    }
    
    .result-section ul {
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: var(--space-sm);
    }
    
    .result-section ul li {
        color: var(--color-text-secondary);
        padding-left: var(--space-md);
        position: relative;
    }
    
    .result-section ul li::before {
        content: "-";
        position: absolute;
        left: 0;
        color: var(--color-primary);
    }
    
    .result-section p {
        color: var(--color-text-secondary);
        line-height: 1.7;
    }
    
    .result-section.note {
        background: rgba(249, 168, 37, 0.1);
        border: 1px solid #F9A825;
    }
    
    .mini-breakdown {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: var(--space-sm);
    }
    
    .mini-score-item {
        display: flex;
        justify-content: space-between;
        padding: var(--space-xs) var(--space-sm);
        background: var(--color-bg-medium);
        border-radius: var(--radius-sm);
        font-size: 0.8rem;
    }
    
    .mini-cat {
        color: var(--color-text-secondary);
        text-transform: capitalize;
    }
    
    .mini-val {
        color: var(--color-primary-light);
        font-weight: 600;
    }
`;
document.head.appendChild(resultsStyles);


console.log('Oral Assignment Grader initialized');
console.log(`Loaded ${QUIZ_QUESTIONS.length} psychology questions`);
