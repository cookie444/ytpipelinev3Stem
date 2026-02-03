const API_BASE = window.location.origin;
let isDownloading = false;
let stemDownloadUrl = null;

const youtubeUrlInput = document.getElementById('youtube-url');
const fileLocationInput = document.getElementById('file-location');
const separateStemsCheckbox = document.getElementById('separate-stems');
const downloadBtn = document.getElementById('download-btn');
const btnText = document.getElementById('btn-text');
const btnSpinner = document.getElementById('btn-spinner');
const statusDiv = document.getElementById('status');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const logoutBtn = document.getElementById('logout-btn');

// Stem separation UI elements
const stemSeparationCard = document.getElementById('stem-separation-card');
const stemSeparationStatus = document.getElementById('stem-separation-status');
const stemProgressFill = document.getElementById('stem-progress-fill');
const stemProgressText = document.getElementById('stem-progress-text');
const stemResults = document.getElementById('stem-results');
const downloadStemsBtn = document.getElementById('download-stems-btn');

document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
});

async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }
    } catch (error) {
        if (error.message.includes('401') || error.message.includes('Authentication')) {
            window.location.href = '/login';
            return;
        }
    }
}

logoutBtn.addEventListener('click', async () => {
    try {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        window.location.href = '/login';
    }
});

downloadBtn.addEventListener('click', async () => {
    if (isDownloading) return;

    const youtubeUrl = youtubeUrlInput.value.trim();
    if (!youtubeUrl) {
        showStatus('Please enter a YouTube URL', 'error');
        return;
    }

    if (!youtubeUrl.startsWith('http://') && !youtubeUrl.startsWith('https://')) {
        showStatus('Please enter a valid URL starting with http:// or https://', 'error');
        return;
    }

    const separateStems = separateStemsCheckbox.checked;

    if (separateStems) {
        await handleStemSeparation(youtubeUrl);
    } else {
        await handleRegularDownload(youtubeUrl);
    }
});

async function handleRegularDownload(youtubeUrl) {
    startDownload();
    
    try {
        updateProgress(10, 'Getting download URL from y2down.cc...');
        showStatus('Processing download request...', 'info');
        
        const response = await fetch(`${API_BASE}/api/download`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                youtube_url: youtubeUrl,
                file_location: fileLocationInput.value
            })
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (!response.ok) {
            // Check if response is JSON before parsing
            const contentType = response.headers.get('content-type');
            let errorMessage = `Server error: ${response.status}`;
            
            if (contentType && contentType.includes('application/json')) {
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // If JSON parsing fails, try to get text
                    const text = await response.text();
                    errorMessage = text || errorMessage;
                }
            } else {
                // Not JSON, try to get text
                try {
                    const text = await response.text();
                    errorMessage = text.substring(0, 200) || errorMessage; // Limit length
                } catch (e) {
                    // Keep default error message
                }
            }
            
            throw new Error(errorMessage);
        }

        updateProgress(50, 'Downloading file...');
        showStatus('Download started!', 'success');

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'video.mp4';
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        const blob = await response.blob();
        updateProgress(100, 'Download complete!');
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showStatus(`Download complete! File saved as: ${filename}`, 'success');
        stopDownload();
        
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        updateProgress(0, 'Download failed');
        stopDownload();
    }
}

async function handleStemSeparation(youtubeUrl) {
    startDownload();
    stemSeparationCard.style.display = 'block';
    stemResults.style.display = 'none';
    stemDownloadUrl = null;
    
    try {
        updateStemProgress(10, 'Downloading audio from YouTube...');
        showStemStatus('Starting stem separation process...', 'info');
        
        const response = await fetch(`${API_BASE}/api/separate-stems`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                youtube_url: youtubeUrl
            })
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (!response.ok) {
            // Check if response is JSON before parsing
            const contentType = response.headers.get('content-type');
            let errorMessage = `Server error: ${response.status}`;
            
            if (contentType && contentType.includes('application/json')) {
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // If JSON parsing fails, try to get text
                    const text = await response.text();
                    errorMessage = text || errorMessage;
                }
            } else {
                // Not JSON, try to get text
                try {
                    const text = await response.text();
                    errorMessage = text.substring(0, 200) || errorMessage; // Limit length
                } catch (e) {
                    // Keep default error message
                }
            }
            
            throw new Error(errorMessage);
        }

        updateStemProgress(50, 'Processing stems with Demucs v4...');
        showStemStatus('Separating audio into stems (this may take a few minutes)...', 'info');

        // Download the zip file
        const blob = await response.blob();
        updateStemProgress(100, 'Stem separation complete!');
        showStemStatus('Stem separation completed successfully!', 'success');
        
        // Store blob URL for download button
        stemDownloadUrl = window.URL.createObjectURL(blob);
        stemResults.style.display = 'block';
        
        stopDownload();
        
    } catch (error) {
        showStemStatus(`Error: ${error.message}`, 'error');
        updateStemProgress(0, 'Stem separation failed');
        stopDownload();
    }
}

downloadStemsBtn.addEventListener('click', () => {
    if (stemDownloadUrl) {
        const a = document.createElement('a');
        a.href = stemDownloadUrl;
        a.download = 'separated_stems.zip';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(stemDownloadUrl);
        document.body.removeChild(a);
        stemDownloadUrl = null;
    }
});

function startDownload() {
    isDownloading = true;
    downloadBtn.disabled = true;
    btnText.textContent = 'Downloading...';
    btnSpinner.classList.remove('hidden');
    updateProgress(0, 'Starting...');
}

function stopDownload() {
    isDownloading = false;
    downloadBtn.disabled = false;
    btnText.textContent = 'Download Video';
    btnSpinner.classList.add('hidden');
}

function updateProgress(percent, message) {
    progressFill.style.width = `${percent}%`;
    progressText.textContent = message || 'Ready';
}

function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.className = 'status-message';
            statusDiv.textContent = '';
        }, 5000);
    }
}

function updateStemProgress(percent, message) {
    stemProgressFill.style.width = `${percent}%`;
    stemProgressText.textContent = message || 'Waiting...';
}

function showStemStatus(message, type) {
    stemSeparationStatus.textContent = message;
    stemSeparationStatus.className = `status-message ${type}`;
    
    if (type === 'error') {
        stemSeparationStatus.style.display = 'block';
    }
}

youtubeUrlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !isDownloading) {
        downloadBtn.click();
    }
});
