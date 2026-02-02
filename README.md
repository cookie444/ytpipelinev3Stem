# YouTube Pipeline with Stem Separation

A web application for downloading YouTube videos and separating them into individual audio stems (vocals, drums, bass, other) using Demucs v4.

## Features

* 🎵 Download YouTube videos as WAV files via y2down.cc
* 🎚️ Separate audio into stems using Demucs v4 (free, open-source)
* 🌐 Simple web interface with authentication
* ⚡ Fast downloads and processing
* 🆓 No API credentials required - runs locally

## Setup

### Prerequisites

* Python 3.11+
* Chrome/Chromium browser (for Selenium)
* PyTorch (automatically installed with dependencies)
* GPU optional but recommended for faster processing

### Installation

1. Clone the repository:
```bash
git clone https://github.com/cookie444/ytpipelinev3Stem.git
cd ytpipelinev3Stem
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (optional):
   - `APP_PASSWORD` - Password for web interface (default: CookieRocks)
   - `SECRET_KEY` - Flask session secret key
   - `HOST` - Server host (default: 0.0.0.0)
   - `PORT` - Server port (default: 5000)

4. Run the server:
```bash
python api_server.py
```

5. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. Enter your password to access the web interface
2. Paste a YouTube video URL
3. Check "Separate into stems" if you want stem separation
4. Click "Download Video" or "Separate Stems"
5. Download the file or separated stems ZIP

## Stem Separation

The application uses Demucs v4 (Facebook's open-source model) to separate audio into:
- **Vocals** - Isolated vocal track
- **Drums** - Drum and percussion elements
- **Bass** - Bass instruments
- **Other** - All other instruments

### About Demucs v4

Demucs v4 is a free, open-source deep learning model for music source separation. It runs locally on your machine - no API credentials or internet connection required after installation. The model will be automatically downloaded on first use.

**Performance Tips:**
- GPU acceleration is supported (CUDA) for faster processing
- CPU processing is available but slower
- First run will download the model (~1.5GB)

## Project Structure

```
ytpipeStemEx/
├── api_server.py          # Flask backend server
├── downloader.py          # y2down.cc integration module
├── stem_separator.py      # Demucs v4 integration
├── index.html             # Web interface
├── login.html             # Login page
├── requirements.txt       # Python dependencies
├── static/
│   ├── script.js          # Frontend JavaScript
│   └── style.css          # Styling
└── README.md              # This file
```

## API Endpoints

- `POST /api/download` - Download YouTube video
- `POST /api/separate-stems` - Separate audio into stems
- `GET /api/status` - Check API status
- `POST /api/login` - Authenticate user
- `POST /api/logout` - Logout user

## Deployment

### Render

1. Go to Render Dashboard
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Set environment variables (APP_PASSWORD, SECRET_KEY, etc.)
5. Deploy

**Note:** Demucs requires significant resources. For production deployments, consider:
- Using GPU instances for faster processing
- Setting appropriate timeout values
- Monitoring memory usage (model requires ~2GB RAM)

### Other Platforms

The application is a standard Flask app and can be deployed to:
- Railway
- Heroku
- AWS Elastic Beanstalk
- Google Cloud Run
- Azure App Service
- DigitalOcean App Platform

## License

MIT

## About

This project extends the original ytPipelineV3 with Demucs v4 integration for free, open-source stem separation.

