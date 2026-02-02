#!/usr/bin/env python3
"""
Stem Separation Module using AudioShake SDK/API
Handles audio stem separation via AudioShake API
"""

import logging
import os
import time
import requests
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

# AudioShake API Configuration
AUDIOSHAKE_API_BASE_URL = os.getenv('AUDIOSHAKE_API_URL', 'https://api.audioshake.ai')
AUDIOSHAKE_CLIENT_ID = os.getenv('AUDIOSHAKE_CLIENT_ID', '')
AUDIOSHAKE_CLIENT_SECRET = os.getenv('AUDIOSHAKE_CLIENT_SECRET', '')


class AudioShakeSeparator:
    """AudioShake SDK client for stem separation."""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize AudioShake separator client.
        
        Args:
            client_id: AudioShake client ID (defaults to env var)
            client_secret: AudioShake client secret (defaults to env var)
        """
        self.client_id = client_id or AUDIOSHAKE_CLIENT_ID
        self.client_secret = client_secret or AUDIOSHAKE_CLIENT_SECRET
        self.api_base_url = AUDIOSHAKE_API_BASE_URL
        self.session = requests.Session()
        self.access_token = None
        
        if not self.client_id or not self.client_secret:
            logger.warning("AudioShake credentials not configured. Set AUDIOSHAKE_CLIENT_ID and AUDIOSHAKE_CLIENT_SECRET environment variables.")
    
    def authenticate(self) -> bool:
        """
        Authenticate with AudioShake API and obtain access token.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.error("Cannot authenticate: missing credentials")
            return False
        
        try:
            auth_url = f"{self.api_base_url}/oauth/token"
            response = self.session.post(
                auth_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get('access_token')
            
            if self.access_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                logger.info("Successfully authenticated with AudioShake API")
                return True
            else:
                logger.error("Authentication failed: no access token received")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def upload_audio(self, audio_file_path: str) -> Optional[str]:
        """
        Upload audio file to AudioShake for processing.
        
        Args:
            audio_file_path: Path to audio file to upload
            
        Returns:
            Task ID if successful, None otherwise
        """
        if not self.access_token:
            if not self.authenticate():
                return None
        
        try:
            upload_url = f"{self.api_base_url}/v1/tasks"
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {'file': (os.path.basename(audio_file_path), audio_file, 'audio/wav')}
                data = {
                    'type': 'stem-separation',
                    'stems': 'vocals,drums,bass,other'  # Standard stem types
                }
                
                response = self.session.post(
                    upload_url,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout for upload
                )
                response.raise_for_status()
                result = response.json()
                task_id = result.get('task_id') or result.get('id')
                
                if task_id:
                    logger.info(f"Audio uploaded successfully. Task ID: {task_id}")
                    return task_id
                else:
                    logger.error(f"Upload failed: no task ID in response: {result}")
                    return None
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Upload error: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            return None
    
    def check_task_status(self, task_id: str) -> Dict:
        """
        Check the status of a separation task.
        
        Args:
            task_id: Task ID returned from upload
            
        Returns:
            Dictionary with task status information
        """
        if not self.access_token:
            if not self.authenticate():
                return {'status': 'error', 'message': 'Authentication failed'}
        
        try:
            status_url = f"{self.api_base_url}/v1/tasks/{task_id}"
            response = self.session.get(status_url, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Status check error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def wait_for_completion(self, task_id: str, max_wait_time: int = 600, poll_interval: int = 5) -> Dict:
        """
        Poll for task completion.
        
        Args:
            task_id: Task ID to check
            max_wait_time: Maximum time to wait in seconds (default: 10 minutes)
            poll_interval: Time between polls in seconds (default: 5 seconds)
            
        Returns:
            Final task status dictionary
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.check_task_status(task_id)
            task_status = status.get('status', 'unknown').lower()
            
            logger.info(f"Task {task_id} status: {task_status}")
            
            if task_status in ['completed', 'done', 'success']:
                return status
            elif task_status in ['failed', 'error']:
                logger.error(f"Task {task_id} failed: {status.get('message', 'Unknown error')}")
                return status
            
            time.sleep(poll_interval)
        
        logger.warning(f"Task {task_id} did not complete within {max_wait_time} seconds")
        return {'status': 'timeout', 'message': 'Task did not complete in time'}
    
    def download_stems(self, task_id: str, output_dir: str) -> Dict[str, str]:
        """
        Download separated stems from completed task.
        
        Args:
            task_id: Task ID
            output_dir: Directory to save stem files
            
        Returns:
            Dictionary mapping stem names to file paths
        """
        if not self.access_token:
            if not self.authenticate():
                return {}
        
        os.makedirs(output_dir, exist_ok=True)
        stem_files = {}
        
        try:
            # Get task details to find download URLs
            task_info = self.check_task_status(task_id)
            
            if task_info.get('status') not in ['completed', 'done', 'success']:
                logger.error(f"Cannot download stems: task not completed. Status: {task_info.get('status')}")
                return {}
            
            # Extract download URLs from task info
            # AudioShake API structure may vary, so we'll handle multiple formats
            stems_data = task_info.get('stems', {})
            if isinstance(stems_data, dict):
                for stem_name, stem_info in stems_data.items():
                    if isinstance(stem_info, dict):
                        download_url = stem_info.get('url') or stem_info.get('download_url')
                    elif isinstance(stem_info, str):
                        download_url = stem_info
                    else:
                        continue
                    
                    if download_url:
                        output_path = os.path.join(output_dir, f"{stem_name}.wav")
                        self._download_file(download_url, output_path)
                        stem_files[stem_name] = output_path
            
            # Alternative: check for direct download links in response
            if not stem_files:
                download_urls = task_info.get('download_urls', {})
                for stem_name, url in download_urls.items():
                    output_path = os.path.join(output_dir, f"{stem_name}.wav")
                    self._download_file(url, output_path)
                    stem_files[stem_name] = output_path
            
            logger.info(f"Downloaded {len(stem_files)} stems to {output_dir}")
            return stem_files
            
        except Exception as e:
            logger.error(f"Error downloading stems: {e}")
            return {}
    
    def _download_file(self, url: str, output_path: str) -> bool:
        """Download a file from URL to output path."""
        try:
            response = self.session.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Downloaded {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False
    
    def separate_audio(self, audio_file_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Complete workflow: upload, wait, and download stems.
        
        Args:
            audio_file_path: Path to audio file
            output_dir: Directory for output stems (defaults to temp directory)
            
        Returns:
            Dictionary mapping stem names to file paths
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix='stems_')
        
        # Step 1: Upload
        task_id = self.upload_audio(audio_file_path)
        if not task_id:
            logger.error("Failed to upload audio file")
            return {}
        
        # Step 2: Wait for completion
        final_status = self.wait_for_completion(task_id)
        if final_status.get('status') not in ['completed', 'done', 'success']:
            logger.error(f"Separation failed: {final_status}")
            return {}
        
        # Step 3: Download stems
        stem_files = self.download_stems(task_id, output_dir)
        return stem_files


def separate_audio_file(audio_file_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to separate audio file using AudioShake.
    
    Args:
        audio_file_path: Path to audio file
        output_dir: Output directory for stems
        
    Returns:
        Dictionary mapping stem names to file paths
    """
    separator = AudioShakeSeparator()
    return separator.separate_audio(audio_file_path, output_dir)

