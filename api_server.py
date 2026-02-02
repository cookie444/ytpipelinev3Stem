#!/usr/bin/env python3
"""
YouTube Downloader Web App
Simple web application for downloading YouTube videos via downloaderto.com
"""

from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, Response
from flask_cors import CORS
import logging
import os
from pathlib import Path
from functools import wraps
import secrets
from downloader import get_download_url, stream_download
from stem_separator import DemucsSeparator
import tempfile
import shutil
import zipfile

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app)

# Session configuration for password protection
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')
APP_PASSWORD = os.getenv('APP_PASSWORD', 'CookieRocks')


def login_required(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated', False):
            if request.path.startswith('/static/'):
                return f(*args, **kwargs)
            if request.path == '/login' or request.path == '/api/login':
                return f(*args, **kwargs)
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET'])
def login_page():
    """Serve the login page."""
    if session.get('authenticated', False):
        return redirect(url_for('index'))
    return send_from_directory(BASE_DIR, 'login.html')


@app.route('/api/login', methods=['POST'])
def login():
    """Handle login authentication."""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        if password == APP_PASSWORD:
            session['authenticated'] = True
            logger.info("User authenticated successfully")
            return jsonify({
                'success': True,
                'message': 'Authentication successful'
            }), 200
        else:
            logger.warning("Failed login attempt")
            return jsonify({
                'success': False,
                'error': 'Invalid password'
            }), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Handle logout."""
    session.pop('authenticated', None)
    logger.info("User logged out")
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@app.route('/')
@login_required
def index():
    """Serve the main HTML page."""
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files explicitly."""
    return send_from_directory(STATIC_DIR, filename)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (public, no auth required)."""
    return jsonify({'status': 'healthy', 'service': 'youtube-downloader'})


@app.route('/api/status', methods=['GET'])
@login_required
def status():
    """Get API status."""
    return jsonify({
        'status': 'running',
        'service': 'youtube-downloader'
    })


@app.route('/api/download', methods=['POST'])
@login_required
def download():
    """Download YouTube video via downloaderto.com."""
    try:
        data = request.get_json()
        
        if not data or 'youtube_url' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing "youtube_url" in request body'
            }), 400
        
        youtube_url = data.get('youtube_url', '').strip()
        file_location = data.get('file_location', 'C:\\Users\\bmack\\Downloads')
        
        if not youtube_url:
            return jsonify({
                'success': False,
                'error': 'YouTube URL cannot be empty'
            }), 400
        
        if not (youtube_url.startswith('http://') or youtube_url.startswith('https://')):
            return jsonify({
                'success': False,
                'error': 'Invalid URL format'
            }), 400
        
        logger.info(f"Processing download request for: {youtube_url}")
        
        # Get download URL from y2down.cc
        download_url, video_title, file_format = get_download_url(youtube_url)
        
        if not download_url:
            return jsonify({
                'success': False,
                'error': 'Could not get download URL from y2down.cc. The service may be unavailable or the video may not be accessible.'
            }), 500
        
        # Determine filename
        if video_title:
            import re
            safe_title = re.sub(r'[^\w\s-]', '', video_title)
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            filename = f"{safe_title}.{file_format or 'mp4'}"
        else:
            filename = f"video.{file_format or 'mp4'}"
        
        logger.info(f"Streaming download: {filename} from {download_url}")
        
        # Stream the file to the client
        def generate():
            try:
                for chunk in stream_download(download_url):
                    yield chunk
            except Exception as e:
                logger.error(f"Error streaming download: {e}")
                raise
        
        response = Response(
            generate(),
            mimetype=f'video/{file_format or "mp4"}' if file_format == 'mp4' else 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': f'video/{file_format or "mp4"}' if file_format == 'mp4' else 'application/octet-stream'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing download request: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error processing download: {str(e)}'
        }), 500


@app.route('/api/separate-stems', methods=['POST'])
@login_required
def separate_stems():
    """Separate audio into stems using AudioShake SDK."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body'
            }), 400
        
        youtube_url = data.get('youtube_url', '').strip()
        uploaded_file = request.files.get('audio_file')
        
        # Validate input
        if not youtube_url and not uploaded_file:
            return jsonify({
                'success': False,
                'error': 'Must provide either "youtube_url" or upload an audio file'
            }), 400
        
        temp_dir = tempfile.mkdtemp(prefix='stem_separation_')
        audio_file_path = None
        
        try:
            # Step 1: Get audio file (download from YouTube or use uploaded file)
            if youtube_url:
                logger.info(f"Downloading audio from YouTube: {youtube_url}")
                
                if not (youtube_url.startswith('http://') or youtube_url.startswith('https://')):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid URL format'
                    }), 400
                
                # Get download URL
                download_url, video_title, file_format = get_download_url(youtube_url)
                
                if not download_url:
                    return jsonify({
                        'success': False,
                        'error': 'Could not get download URL from y2down.cc'
                    }), 500
                
                # Download audio file to temp directory
                import requests
                audio_filename = f"audio.{file_format or 'wav'}"
                audio_file_path = os.path.join(temp_dir, audio_filename)
                
                logger.info(f"Downloading audio to: {audio_file_path}")
                response = requests.get(download_url, stream=True, timeout=300)
                response.raise_for_status()
                
                with open(audio_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"Audio downloaded successfully: {audio_file_path}")
            else:
                # Save uploaded file
                if uploaded_file.filename == '':
                    return jsonify({
                        'success': False,
                        'error': 'No file uploaded'
                    }), 400
                
                audio_file_path = os.path.join(temp_dir, uploaded_file.filename)
                uploaded_file.save(audio_file_path)
                logger.info(f"Uploaded file saved to: {audio_file_path}")
            
            # Step 2: Separate stems using Demucs v4
            logger.info("Starting stem separation with Demucs v4...")
            separator = DemucsSeparator(model="htdemucs")
            output_dir = os.path.join(temp_dir, 'stems')
            os.makedirs(output_dir, exist_ok=True)
            
            stem_files = separator.separate_audio(audio_file_path, output_dir)
            
            if not stem_files:
                return jsonify({
                    'success': False,
                    'error': 'Stem separation failed or returned no stems'
                }), 500
            
            logger.info(f"Stem separation completed. Generated {len(stem_files)} stems")
            
            # Step 3: Create zip archive of stems + original audio
            zip_path = os.path.join(temp_dir, 'stems.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add original audio file (always include it)
                if audio_file_path and os.path.exists(audio_file_path):
                    # Get file extension
                    file_ext = os.path.splitext(audio_file_path)[1].lower()
                    # Use appropriate name based on format
                    if file_ext == '.wav':
                        original_zip_name = 'original.wav'
                    else:
                        # Keep original extension but use clear name
                        original_zip_name = f'original{file_ext}'
                    
                    zipf.write(audio_file_path, original_zip_name)
                    logger.info(f"Added original audio to zip: {audio_file_path} as {original_zip_name}")
                
                # Add all separated stems
                for stem_name, stem_path in stem_files.items():
                    if os.path.exists(stem_path):
                        zipf.write(stem_path, os.path.basename(stem_path))
                        logger.info(f"Added stem to zip: {stem_name} -> {os.path.basename(stem_path)}")
            
            logger.info(f"Created zip archive with original audio and {len(stem_files)} stems: {zip_path}")
            
            # Step 4: Return zip file
            return send_from_directory(
                temp_dir,
                'stems.zip',
                as_attachment=True,
                download_name='separated_stems.zip',
                mimetype='application/zip'
            )
            
        except Exception as e:
            logger.error(f"Error in stem separation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Error during stem separation: {str(e)}'
            }), 500
        finally:
            # Cleanup temp directory after a delay (to allow download to complete)
            # In production, consider using a background task to clean up
            pass
    
    except Exception as e:
        logger.error(f"Error processing stem separation request: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error processing request: {str(e)}'
        }), 500


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    
    logger.info(f"Starting YouTube Downloader on {HOST}:{PORT}")
    logger.info(f"Web interface available at http://{HOST}:{PORT}")
    logger.info(f"Password: {APP_PASSWORD}")
    
    app.run(host=HOST, port=PORT, debug=False)
