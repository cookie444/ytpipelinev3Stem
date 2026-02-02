#!/usr/bin/env python3
"""
Downloader module for integrating with downloaderto.com
Uses Selenium headless browser to handle JavaScript-rendered content
"""

import logging
import os
from typing import Optional, Tuple
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys
import requests

logger = logging.getLogger(__name__)


def get_download_url(youtube_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Get download URL from y2down.cc using headless browser."""
    driver = None
    try:
        base_url = "https://y2down.cc/enV8/youtube-wav"
        logger.info(f"Submitting YouTube URL to y2down.cc: {youtube_url}")
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Try to find Chrome/Chromium binary (for Render/Linux environments)
        chrome_binary_paths = [
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/usr/bin/google-chrome',
            '/usr/bin/chrome',
        ]
        chrome_binary = None
        for path in chrome_binary_paths:
            if os.path.exists(path):
                chrome_binary = path
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary: {chrome_binary}")
                break
        
        # Try to find ChromeDriver (for Render/Linux environments)
        chromedriver_paths = [
            '/usr/bin/chromedriver',
            '/usr/lib/chromium-browser/chromedriver',
        ]
        chromedriver_path = None
        for path in chromedriver_paths:
            if os.path.exists(path):
                chromedriver_path = path
                logger.info(f"Using ChromeDriver: {chromedriver_path}")
                break
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Fallback to webdriver-manager
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.warning(f"Failed to use ChromeDriverManager: {e}, trying default Chrome")
            try:
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as e2:
                logger.error(f"Failed to start Chrome: {e2}")
                return None, None, None
        
        logger.info("Headless browser started")
        driver.get(base_url)
        logger.info(f"Loaded page: {driver.current_url}")
        
        wait = WebDriverWait(driver, 20)
        
        # Find URL input
        input_selectors = [
            (By.ID, "url"),
            (By.NAME, "url"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.XPATH, "//input[@type='text']"),
        ]
        
        url_input = None
        for by, selector in input_selectors:
            try:
                url_input = wait.until(EC.presence_of_element_located((by, selector)))
                logger.info(f"Found input field using {by}: {selector}")
                break
            except TimeoutException:
                continue
        
        if not url_input:
            logger.error("Could not find URL input field")
            return None, None, None
        
        url_input.clear()
        url_input.send_keys(youtube_url)
        logger.info("Entered YouTube URL")
        
        # Submit form
        try:
            url_input.send_keys(Keys.RETURN)
            logger.info("Submitted by pressing Enter")
        except Exception as e:
            logger.warning(f"Enter key failed: {e}")
            # Try to find submit button
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_btn.click()
            except:
                pass
        
        # Wait for page to process and show download options
        logger.info("Waiting for download links...")
        time.sleep(8)
        
        # Check if page redirected or updated
        current_url = driver.current_url
        logger.info(f"Current URL after submission: {current_url}")
        
        # Wait for download buttons/links to appear
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a, button")))
        except:
            pass
        
        time.sleep(5)
        
        # Try clicking format buttons (WAV, MP3, MP4, etc.)
        try:
            # Look for format buttons - they might be in different formats
            format_selectors = [
                (By.XPATH, "//a[contains(text(), 'WAV')]"),
                (By.XPATH, "//a[contains(text(), 'MP3')]"),
                (By.XPATH, "//a[contains(text(), 'MP4')]"),
                (By.XPATH, "//button[contains(text(), 'WAV')]"),
                (By.XPATH, "//button[contains(text(), 'MP3')]"),
                (By.XPATH, "//button[contains(text(), 'Download')]"),
                (By.CSS_SELECTOR, "a[href*='wav']"),
                (By.CSS_SELECTOR, "a[href*='mp3']"),
                (By.CSS_SELECTOR, "a[href*='mp4']"),
                (By.CSS_SELECTOR, "button[onclick*='download']"),
            ]
            
            for by, selector in format_selectors:
                try:
                    buttons = driver.find_elements(by, selector)
                    for btn in buttons[:5]:  # Try first 5
                        try:
                            if btn.is_displayed() and btn.is_enabled():
                                btn_text = btn.text or btn.get_attribute('href') or ''
                                logger.info(f"Trying to click: {btn_text[:50]}")
                                btn.click()
                                time.sleep(4)
                                
                                # Check if we got redirected to download
                                new_url = driver.current_url
                                if new_url != current_url:
                                    logger.info(f"URL changed to: {new_url}")
                                    if any(ext in new_url.lower() for ext in ['.mp4', '.mp3', '.wav', '.m4a', '.webm']):
                                        logger.info(f"Redirected to download file: {new_url}")
                                        format_ext = 'wav' if '.wav' in new_url.lower() else 'mp3' if '.mp3' in new_url.lower() else 'mp4'
                                        return new_url, video_title, format_ext
                                    # Check page source for download link
                                    page_source = driver.page_source
                                    import re
                                    direct_url = re.search(r'https?://[^\s"\'<>]+\.(?:mp4|mp3|wav|m4a)', page_source, re.IGNORECASE)
                                    if direct_url:
                                        download_url = direct_url.group(0)
                                        logger.info(f"Found direct download in new page: {download_url}")
                                        return download_url, video_title, 'wav' if '.wav' in download_url.lower() else 'mp3'
                                break
                        except Exception as e:
                            logger.debug(f"Error clicking button: {e}")
                            continue
                    if download_url:
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error with format buttons: {e}")
        
        time.sleep(3)  # Additional wait
        
        download_url = None
        video_title = None
        file_format = 'mp4'
        
        # Look for download links with better filtering
        download_selectors = [
            (By.CSS_SELECTOR, "a[href*='.mp4']"),
            (By.CSS_SELECTOR, "a[href*='.mp3']"),
            (By.CSS_SELECTOR, "a[href*='.webm']"),
            (By.CSS_SELECTOR, "a[href*='.wav']"),
            (By.CSS_SELECTOR, "a[href*='.m4a']"),
            (By.CSS_SELECTOR, "a[download]"),
            (By.XPATH, "//a[contains(@href, 'download')]"),
            (By.XPATH, "//a[contains(text(), 'Download')]"),
            (By.XPATH, "//button[contains(text(), 'Download')]"),
            (By.CSS_SELECTOR, "button[onclick*='download']"),
            (By.CSS_SELECTOR, "[data-url]"),
        ]
        
        for by, selector in download_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for elem in elements:
                    href = elem.get_attribute('href') or elem.get_attribute('onclick') or elem.get_attribute('data-url')
                    if href:
                        # Extract URL from onclick
                        if 'onclick' in str(href):
                            import re
                            url_match = re.search(r'https?://[^\s"\'<>)]+', href)
                            if url_match:
                                href = url_match.group(0)
                        
                        # Validate it's a real download URL
                        is_valid = (
                            href and href.startswith('http') and len(href) > 40 and
                            'y2down.cc/en' not in href and
                            'y2down.cc/' != href and
                            (any(ext in href.lower() for ext in ['.mp4', '.mp3', '.webm', '.m4a', '.wav', '.flac']) or
                             ('download' in href.lower() and ('api' in href.lower() or 'cdn' in href.lower() or 'storage' in href.lower() or 'get' in href.lower()) and len(href) > 50))
                        )
                        if is_valid:
                            download_url = href
                            if '.mp4' in href.lower():
                                file_format = 'mp4'
                            elif '.mp3' in href.lower():
                                file_format = 'mp3'
                            elif '.wav' in href.lower():
                                file_format = 'wav'
                            elif '.m4a' in href.lower():
                                file_format = 'm4a'
                            elif '.webm' in href.lower():
                                file_format = 'webm'
                            logger.info(f"Found download URL: {download_url}")
                            break
                if download_url:
                    break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        # Check page source for URLs
        if not download_url:
            page_source = driver.page_source
            import re
            
            # Debug: check what's on the page
            logger.info(f"Page title: {driver.title}")
            logger.info(f"Page URL: {driver.current_url}")
            
            # Look for all links on the page
            try:
                all_links = driver.find_elements(By.TAG_NAME, "a")
                logger.info(f"Found {len(all_links)} links on page")
                for i, link in enumerate(all_links[:10]):
                    href = link.get_attribute('href')
                    text = link.text[:50]
                    if href:
                        logger.info(f"  Link {i}: {href[:80]} (text: {text})")
            except:
                pass
            
            patterns = [
                r'https?://[^\s"\'<>]+\.(?:mp4|mp3|webm|m4a|wav|flac)',
                r'["\'](https?://[^"\']*download[^"\']*\.(?:mp4|mp3|webm|m4a|wav|flac)[^"\']*)["\']',
                r'downloadUrl["\']?\s*[:=]\s*["\'](https?://[^"\']+)["\']',
                r'url["\']?\s*[:=]\s*["\'](https?://[^"\']*\.(?:mp4|mp3|wav|m4a)[^"\']*)["\']',
                r'https?://[^"\'\s<>]+/get/[^"\'\s<>]+',
                r'https?://[^"\'\s<>]+/download/[^"\'\s<>]+',
                r'https?://[^"\'\s<>]*y2down[^"\'\s<>]*/get[^"\'\s<>]+',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    if (match and len(match) > 40 and 
                        'y2down.cc/en' not in match and 
                        'y2down.cc/' != match and
                        '.xml' not in match and
                        (any(ext in match.lower() for ext in ['.mp4', '.mp3', '.webm', '.m4a', '.wav', '.flac']) or 
                         ('download' in match.lower() and ('api' in match.lower() or 'get' in match.lower()) and len(match) > 50))):
                        download_url = match
                        if '.mp4' in download_url.lower():
                            file_format = 'mp4'
                        elif '.mp3' in download_url.lower():
                            file_format = 'mp3'
                        elif '.wav' in download_url.lower():
                            file_format = 'wav'
                        elif '.m4a' in download_url.lower():
                            file_format = 'm4a'
                        elif '.webm' in download_url.lower():
                            file_format = 'webm'
                        logger.info(f"Found download URL in source: {download_url}")
                        break
                if download_url:
                    break
        
        if download_url:
            return download_url, video_title, file_format
        else:
            logger.warning("Could not find download URL")
            # Debug: save page source
            try:
                current_url = driver.current_url
                logger.info(f"Current page URL: {current_url}")
                # Check if we were redirected to a download
                if current_url != base_url and 'y2down.cc/en' not in current_url:
                    if any(ext in current_url.lower() for ext in ['.mp4', '.mp3', '.webm', '.wav', '.m4a']):
                        logger.info(f"Current URL appears to be download: {current_url}")
                        return current_url, video_title, file_format
            except:
                pass
            return None, video_title, None
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def stream_download(download_url: str, chunk_size: int = 8192):
    """Stream download from a URL."""
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://y2down.cc/',
        })
        
        response = session.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
                
    except Exception as e:
        logger.error(f"Error streaming download: {e}")
        raise
