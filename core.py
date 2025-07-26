import asyncio
import aiohttp
import aiofiles
import ssl
import certifi
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import math
import time
from urllib.parse import urlparse, unquote
import threading
import re
import os

from progress import ProgressTracker

@dataclass
class DownloadConfig:
    """Configuration for the download manager"""
    max_concurrent_fragments: int = 4
    chunk_size: int = 8192
    timeout: int = 30
    retry_attempts: int = 3
    output_directory: str = "./downloads"
    temp_directory: str = "./temp"
    verify_ssl: bool = True
    show_progress: bool = True
    progress_style: str = "inline"  # "inline", "full_screen", or "simple"

class FragmentDownloader:
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.ensure_directories()
        self.ssl_context = self._create_ssl_context()
        self.progress_tracker = None
    
    def _create_ssl_context(self):
        """Create SSL context with proper configuration"""
        if self.config.verify_ssl:
            try:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                print("✓ SSL verification enabled")
            except Exception as e:
                print(f"Warning: Could not create SSL context with certifi: {e}")
                ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            print("⚠️  SSL verification disabled")
        return ssl_context
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        Path(self.config.output_directory).mkdir(parents=True, exist_ok=True)
        Path(self.config.temp_directory).mkdir(parents=True, exist_ok=True)
    
    async def get_file_size(self, url: str) -> Optional[int]:
        """Get the total file size from URL headers"""
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        ) as session:
            try:
                async with session.head(url) as response:
                    if response.status == 200:
                        content_length = response.headers.get('Content-Length')
                        accept_ranges = response.headers.get('Accept-Ranges')
                        
                        if content_length and accept_ranges == 'bytes':
                            return int(content_length)
                        else:
                            print("Server doesn't support range requests. Falling back to single-threaded download.")
                            return None
            except Exception as e:
                print(f"Error getting file size: {e}")
                return None
    
    async def download_fragment(self, session: aiohttp.ClientSession, url: str, start: int, end: int, fragment_path: str, fragment_id: int) -> bool:
        """Download a single fragment of the file with progress tracking"""
        headers = {'Range': f'bytes={start}-{end}'}
        fragment_size = end - start + 1
        
        # Initialize progress tracking for this fragment
        if self.progress_tracker:
            self.progress_tracker.initialize_fragment(fragment_id, fragment_size)
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status in [206, 200]:  # 206 Partial Content or 200 OK
                        downloaded = 0
                        async with aiofiles.open(fragment_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(self.config.chunk_size):
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Update progress
                                if self.progress_tracker:
                                    self.progress_tracker.update_fragment_progress(fragment_id, downloaded)
                        
                        if not self.config.show_progress:  # Only print individual completion if not showing live progress
                            print(f"✓ Fragment {fragment_id + 1} downloaded successfully")
                        return True
                    else:
                        if not self.config.show_progress:
                            print(f"✗ Fragment {fragment_id + 1} failed with status {response.status}")
            
            except Exception as e:
                if not self.config.show_progress:
                    print(f"✗ Fragment {fragment_id + 1} attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    async def download_single_threaded(self, url: str, output_path: Path) -> bool:
        """Fallback single-threaded download with progress"""
        print("Using single-threaded download...")
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        ) as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        file_size = response.headers.get('Content-Length')
                        downloaded = 0
                        start_time = time.time()
                        
                        async with aiofiles.open(output_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(self.config.chunk_size):
                                await f.write(chunk)
                                downloaded += len(chunk)
                                
                                if file_size and self.config.show_progress:
                                    progress = (downloaded / int(file_size)) * 100
                                    speed = downloaded / (time.time() - start_time) if time.time() - start_time > 0 else 0
                                    print(f"\rProgress: {progress:.1f}% | Speed: {self.format_size(speed)}/s", end="", flush=True)
                        
                        print(f"\n✓ Single-threaded download completed")
                        return True
                    else:
                        print(f"✗ Download failed with status {response.status}")
            except Exception as e:
                print(f"Single-threaded download failed: {e}")
                return False
        
        return False
    
    async def join_fragments(self, fragments: List, output_path: Path) -> bool:
        """Join downloaded fragments into a single file"""
        try:
            async with aiofiles.open(output_path, 'wb') as output_file:
                for _, _, fragment_path, fragment_id in fragments:
                    if fragment_path.exists():
                        async with aiofiles.open(fragment_path, 'rb') as fragment_file:
                            while True:
                                chunk = await fragment_file.read(self.config.chunk_size)
                                if not chunk:
                                    break
                                await output_file.write(chunk)
                    else:
                        print(f"✗ Fragment {fragment_id} not found")
                        return False
            return True
        except Exception as e:
            print(f"Error joining fragments: {e}")
            return False
    
    def cleanup_fragments(self, fragments: List):
        """Clean up temporary fragment files"""
        for _, _, fragment_path, _ in fragments:
            try:
                if fragment_path.exists():
                    fragment_path.unlink()
            except Exception as e:
                print(f"Warning: Could not delete fragment {fragment_path}: {e}")

    async def get_filename_from_headers(self, url: str) -> Optional[str]:
        """
        Try to get filename from Content-Disposition header ONLY
        Don't return extensions from Content-Type
        """
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        ) as session:
            try:
                async with session.head(url) as response:
                    # ONLY check Content-Disposition header for actual filename
                    content_disposition = response.headers.get('Content-Disposition')
                    if content_disposition:
                        # Parse Content-Disposition: attachment; filename="example.zip"
                        if 'filename=' in content_disposition:
                            filename_match = re.search(r'filename[*]?=([^;]+)', content_disposition)
                            if filename_match:
                                filename = filename_match.group(1).strip('"\'')
                                return unquote(filename)
                    
                    # DON'T return extensions from Content-Type anymore
                    return None
                            
            except Exception:
                pass
        
        return None

    def extract_filename_from_url(self, url: str) -> str:
        """
        Extract a clean filename from URL, handling query parameters and edge cases
        """
        try:
            # Parse the URL to separate components
            parsed_url = urlparse(url)
            
            # Get the path component (without query parameters)
            path = parsed_url.path
            
            # URL decode the path to handle encoded characters
            path = unquote(path)
            
            # Extract filename from path
            filename = Path(path).name
            
            # Clean the filename of any remaining query parameter artifacts
            if '?' in filename:
                filename = filename.split('?')[0]
            
            # Remove invalid characters for filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            
            # Handle edge cases
            if not filename or filename == '.' or filename == '..':
                # Try to get a meaningful name from the path
                path_parts = [part for part in path.split('/') if part and part not in ('.', '..')]
                if path_parts:
                    filename = path_parts[-1]
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                else:
                    filename = "downloaded_file"
            
            # If no extension, try to guess from URL or add default
            if '.' not in filename:
                # Try to get extension from the URL path
                for part in reversed(path.split('/')):
                    if '.' in part and not part.startswith('.'):
                        # Found a part with extension, use it
                        ext = '.' + part.split('.')[-1]
                        filename += ext
                        break
                else:
                    # No extension found, add default
                    filename += ".bin"
            
            # Limit filename length (most filesystems support 255 chars)
            if len(filename) > 200:
                name_part, ext_part = os.path.splitext(filename)
                name_part = name_part[:200-len(ext_part)]
                filename = name_part + ext_part
            
            return filename
            
        except Exception as e:
            print(f"Warning: Could not extract filename from URL: {e}")
            return "downloaded_file.bin"

    def get_extension_from_content_type(self, content_type: str) -> str:
        """
        Get file extension from Content-Type header
        """
        type_to_ext = {
            'application/zip': '.zip',
            'application/pdf': '.pdf',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'video/mp4': '.mp4',
            'application/json': '.json',
            'text/plain': '.txt',
            'application/octet-stream': '.bin',
            'video/x-msvideo': '.avi',
            'image/gif': '.gif',
        }
        return type_to_ext.get(content_type.split(';')[0], '.bin')

    async def get_content_type_extension(self, url: str) -> Optional[str]:
        """
        Get extension from Content-Type header (separate method)
        """
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        ) as session:
            try:
                async with session.head(url) as response:
                    content_type = response.headers.get('Content-Type')
                    if content_type:
                        return self.get_extension_from_content_type(content_type)
            except Exception:
                pass
        return None

    async def download_file(self, url: str, filename: Optional[str] = None) -> bool:
        """Download a file using multiple fragments with proper filename handling"""
        
        if not filename:
            # Step 1: Try to get filename from Content-Disposition header
            header_filename = await self.get_filename_from_headers(url)
            if header_filename:
                filename = header_filename
                print(f"Using filename from server header: {filename}")
            else:
                # Step 2: Extract from URL
                filename = self.extract_filename_from_url(url)
                print(f"Using filename from URL: {filename}")
                
                # Step 3: If URL filename has no extension, try to get it from Content-Type
                if '.' not in filename or filename.endswith('.bin'):
                    content_extension = await self.get_content_type_extension(url)
                    if content_extension and content_extension != '.bin':
                        # Replace .bin with proper extension, or add extension if none
                        if filename.endswith('.bin'):
                            filename = filename[:-4] + content_extension
                        else:
                            filename += content_extension
                        print(f"Added extension from Content-Type: {filename}")
        
        # Final validation
        if not filename or filename in ['.zip', '.txt', '.pdf']:  # Just extensions
            filename = f"downloaded_file{filename if filename.startswith('.') else '.bin'}"
            print(f"Fixed invalid filename to: {filename}")
        
        output_path = Path(self.config.output_directory) / filename
        
        print(f"Starting download: {filename}")
        print(f"URL: {url}")
        print(f"Output path: {output_path}")
        
        # Rest of the method remains the same...
        file_size = await self.get_file_size(url)
        
        if not file_size:
            return await self.download_single_threaded(url, output_path)
        
        print(f"File size: {self.format_size(file_size)}")
        
        # Calculate fragment ranges
        fragment_size = math.ceil(file_size / self.config.max_concurrent_fragments)
        fragments = []
        
        for i in range(self.config.max_concurrent_fragments):
            start = i * fragment_size
            end = min(start + fragment_size - 1, file_size - 1)
            
            if start <= end:
                fragment_path = Path(self.config.temp_directory) / f"{filename}.part{i}"
                fragments.append((start, end, fragment_path, i))
        
        print(f"Downloading in {len(fragments)} fragments...")
        if self.config.show_progress:
            print(f"Progress style: {self.config.progress_style}")
        print()
        
        # Initialize progress tracker
        if self.config.show_progress:
            self.progress_tracker = ProgressTracker(len(fragments), self.config.progress_style)
            self.progress_tracker.display_active = True
            
            progress_thread = threading.Thread(target=self.progress_tracker.display_progress)
            progress_thread.daemon = True
            progress_thread.start()
        
        # Download fragments concurrently
        start_time = time.time()
        
        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        ) as session:
            tasks = [
                self.download_fragment(session, url, start, end, str(fragment_path), fragment_id)
                for start, end, fragment_path, fragment_id in fragments
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop progress display
        if self.progress_tracker:
            self.progress_tracker.display_active = False
            time.sleep(0.6)
            
            if self.config.progress_style == "inline" and self.progress_tracker.supports_ansi:
                print(f"\033[{self.progress_tracker.last_line_count}A", end="")
                for _ in range(self.progress_tracker.last_line_count):
                    print("\033[K")
            elif self.config.progress_style == "full_screen" and self.progress_tracker.supports_ansi:
                print("\033[2J\033[H", end="")
        
        # Check if all fragments downloaded successfully
        if not all(isinstance(result, bool) and result for result in results):
            print("✗ Some fragments failed to download")
            self.cleanup_fragments(fragments)
            return False
        
        # Join fragments
        print("Joining fragments...")
        success = await self.join_fragments(fragments, output_path)
        
        if success:
            download_time = time.time() - start_time
            speed = file_size / download_time / (1024 * 1024)
            print(f"✓ Download completed in {download_time:.2f}s ({speed:.2f} MB/s)")
            print(f"✓ File saved to: {output_path}")
        
        # Cleanup temporary fragments
        self.cleanup_fragments(fragments)
        
        return success

    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
