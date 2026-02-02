#!/usr/bin/env python3
"""
Stem Separation Module using Demucs v4
Handles audio stem separation using Facebook's Demucs v4 model
"""

import logging
import os
import subprocess
from typing import Optional, Dict
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)


class DemucsSeparator:
    """Demucs v4 stem separator."""
    
    def __init__(self, model: str = "htdemucs", device: Optional[str] = None):
        """
        Initialize Demucs separator.
        
        Args:
            model: Demucs model to use (default: htdemucs for v4)
            device: Device to use ('cpu', 'cuda', etc.). Auto-detects if None.
        """
        self.model = model
        self.device = device
        
    def separate_audio(self, audio_file_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Separate audio file into stems using Demucs.
        
        Args:
            audio_file_path: Path to audio file to separate
            output_dir: Directory for output stems (defaults to temp directory)
            
        Returns:
            Dictionary mapping stem names to file paths
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix='stems_')
        
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Build demucs command
            cmd = [
                'python', '-m', 'demucs.separate',
                '--model', self.model,
                '--out', output_dir,
                '--filename', '{stem}.{ext}',
            ]
            
            # Add device if specified
            if self.device:
                cmd.extend(['--device', self.device])
            
            # Add input file
            cmd.append(audio_file_path)
            
            logger.info(f"Running Demucs separation: {' '.join(cmd)}")
            
            # Run demucs
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Demucs separation failed: {result.stderr}")
                return {}
            
            logger.info(f"Demucs separation completed. Output: {result.stdout}")
            
            # Find the output files
            # Demucs creates: output_dir/model_name/track_name/stem.wav
            stem_files = {}
            base_name = Path(audio_file_path).stem
            
            # Look for the separated files
            model_dir = os.path.join(output_dir, self.model)
            if os.path.exists(model_dir):
                track_dir = None
                # Find the track directory (usually matches input filename)
                for item in os.listdir(model_dir):
                    item_path = os.path.join(model_dir, item)
                    if os.path.isdir(item_path):
                        track_dir = item_path
                        break
                
                if track_dir:
                    # Demucs outputs: vocals.wav, drums.wav, bass.wav, other.wav
                    stem_names = ['vocals', 'drums', 'bass', 'other']
                    for stem_name in stem_names:
                        stem_path = os.path.join(track_dir, f"{stem_name}.wav")
                        if os.path.exists(stem_path):
                            # Copy to output_dir with simpler naming
                            output_path = os.path.join(output_dir, f"{stem_name}.wav")
                            import shutil
                            shutil.copy2(stem_path, output_path)
                            stem_files[stem_name] = output_path
                            logger.info(f"Found stem: {stem_name} -> {output_path}")
            
            if not stem_files:
                logger.warning("No stem files found after separation")
                # Try alternative location structure
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.endswith('.wav'):
                            file_path = os.path.join(root, file)
                            stem_name = Path(file).stem
                            if stem_name in ['vocals', 'drums', 'bass', 'other']:
                                output_path = os.path.join(output_dir, f"{stem_name}.wav")
                                if file_path != output_path:
                                    import shutil
                                    shutil.copy2(file_path, output_path)
                                stem_files[stem_name] = output_path
            
            logger.info(f"Separated {len(stem_files)} stems: {list(stem_files.keys())}")
            return stem_files
            
        except subprocess.TimeoutExpired:
            logger.error("Demucs separation timed out after 30 minutes")
            return {}
        except Exception as e:
            logger.error(f"Error during Demucs separation: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}


def separate_audio_file(audio_file_path: str, output_dir: Optional[str] = None, model: str = "htdemucs") -> Dict[str, str]:
    """
    Convenience function to separate audio file using Demucs v4.
    
    Args:
        audio_file_path: Path to audio file
        output_dir: Output directory for stems
        model: Demucs model to use (default: htdemucs for v4)
        
    Returns:
        Dictionary mapping stem names to file paths
    """
    separator = DemucsSeparator(model=model)
    return separator.separate_audio(audio_file_path, output_dir)
