# YouTube Pipeline with Stem Separation

A web application for downloading YouTube videos and separating them into individual audio stems (vocals, drums, bass, other) using AudioShake SDK.

## Features

* 🎵 Download YouTube videos as WAV files via y2down.cc
* 🎚️ Separate audio into stems using AudioShake SDK
* 🌐 Simple web interface with authentication
* ⚡ Fast downloads and processing

## Setup

### Prerequisites

* Python 3.11+
* Chrome/Chromium browser (for Selenium)
* AudioShake API credentials (Client ID and Client Secret)

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

3. Configure environment variables:
   - Copy `env.example` to `.env` (if available) or set environment variables:
   - `AUDIOSHAKE_CLIENT_ID` - Your AudioShake client ID
   - `AUDIOSHAKE_CLIENT_SECRET` - Your AudioShake client secret
   - `AUDIOSHAKE_API_URL` - AudioShake API URL (default: https://api.audioshake.ai)
   - `APP_PASSWORD` - Password for web interface (default: CookieRocks)
   - `SECRET_KEY` - Flask session secret key

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

The application uses AudioShake SDK to separate audio into:
- **Vocals** - Isolated vocal track
- **Drums** - Drum and percussion elements
- **Bass** - Bass instruments
- **Other** - All other instruments

### Getting AudioShake Credentials

1. Visit [AudioShake Developer Portal](https://developer.audioshake.ai)
2. Sign up for an account
3. Contact info@audioshake.ai for API credentials
4. Set `AUDIOSHAKE_CLIENT_ID` and `AUDIOSHAKE_CLIENT_SECRET` environment variables

## Project Structure

```
ytpipeStemEx/
├── api_server.py          # Flask backend server
├── downloader.py          # y2down.cc integration module
├── stem_separator.py      # AudioShake SDK integration
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
4. Set environment variables for AudioShake credentials
5. Deploy

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

This project extends the original ytPipelineV3 with AudioShake SDK integration for professional-grade stem separation.

