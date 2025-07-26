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
from urllib.parse import urlparse
import threading

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
    
    async def download_file(self, url: str, filename: Optional[str] = None) -> bool:
        """Download a file using multiple fragments with progress tracking"""
        if not filename:
            filename = Path(urlparse(url).path).name or "downloaded_file"
        
        output_path = Path(self.config.output_directory) / filename
        
        print(f"Starting download: {filename}")
        print(f"URL: {url}")
        
        # Get file size
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
        print(f"Progress style: {self.config.progress_style}")
        print()  # Empty line before progress
        
        # Initialize progress tracker
        if self.config.show_progress:
            self.progress_tracker = ProgressTracker(len(fragments), self.config.progress_style)
            self.progress_tracker.display_active = True
            
            # Start progress display in background thread
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
            time.sleep(0.6)  # Give time for display thread to stop
            
            # Clear progress lines if using inline mode
            if self.config.progress_style == "inline" and self.progress_tracker.supports_ansi:
                print(f"\033[{self.progress_tracker.last_line_count}A", end="")
                for _ in range(self.progress_tracker.last_line_count):
                    print("\033[K")  # Clear each line
            elif self.config.progress_style == "full_screen" and self.progress_tracker.supports_ansi:
                print("\033[2J\033[H", end="")  # Clear screen
        
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
            speed = file_size / download_time / (1024 * 1024)  # MB/s
            print(f"✓ Download completed in {download_time:.2f}s ({speed:.2f} MB/s)")
            print(f"✓ File saved to: {output_path}")
        
        # Cleanup temporary fragments
        self.cleanup_fragments(fragments)
        
        return success
    
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
