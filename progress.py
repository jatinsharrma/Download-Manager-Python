import os
import time
import math
from datetime import datetime
import threading
import platform


class ProgressTracker:
    def __init__(self, total_fragments: int, progress_style: str = "inline"):
        self.total_fragments = total_fragments
        self.fragment_progress = {}
        self.fragment_sizes = {}
        self.fragment_speeds = {}
        self.start_times = {}
        self.lock = threading.Lock()
        self.display_active = False
        self.progress_style = progress_style
        self.last_line_count = 0
        
        # Detect if we can use ANSI escape codes
        self.supports_ansi = self._supports_ansi()
    
    def _supports_ansi(self) -> bool:
        """Check if terminal supports ANSI escape codes"""
        if platform.system() == "Windows":
            try:
                import subprocess
                result = subprocess.run(['ver'], capture_output=True, text=True, shell=True)
                if 'Windows' in result.stdout:
                    os.system("")  # This enables ANSI escape sequences on Windows 10+
                    return True
            except:
                pass
            return False
        else:
            return os.getenv('TERM') is not None
    
    def initialize_fragment(self, fragment_id: int, total_size: int):
        with self.lock:
            self.fragment_progress[fragment_id] = 0
            self.fragment_sizes[fragment_id] = total_size
            self.fragment_speeds[fragment_id] = 0
            self.start_times[fragment_id] = time.time()
    
    def update_fragment_progress(self, fragment_id: int, downloaded: int):
        with self.lock:
            self.fragment_progress[fragment_id] = downloaded
            
            # Calculate speed
            elapsed = time.time() - self.start_times[fragment_id]
            if elapsed > 0:
                self.fragment_speeds[fragment_id] = downloaded / elapsed
    
    def get_progress_info(self):
        with self.lock:
            total_downloaded = sum(self.fragment_progress.values())
            total_size = sum(self.fragment_sizes.values())
            overall_progress = (total_downloaded / total_size * 100) if total_size > 0 else 0
            
            fragment_info = []
            for i in range(self.total_fragments):
                if i in self.fragment_progress:
                    downloaded = self.fragment_progress[i]
                    total = self.fragment_sizes[i]
                    progress = (downloaded / total * 100) if total > 0 else 0
                    speed = self.fragment_speeds[i]
                    fragment_info.append({
                        'id': i,
                        'progress': progress,
                        'downloaded': downloaded,
                        'total': total,
                        'speed': speed
                    })
            
            return {
                'overall_progress': overall_progress,
                'total_downloaded': total_downloaded,
                'total_size': total_size,
                'fragments': fragment_info
            }
    
    def display_progress(self):
        """Display real-time progress with different styles"""
        if self.progress_style == "simple":
            self._display_simple_progress()
        elif self.progress_style == "full_screen" and self.supports_ansi:
            self._display_full_screen_progress()
        else:
            self._display_inline_progress()
    
    def _display_inline_progress(self):
        """Display progress inline, updating the same lines"""
        while self.display_active:
            try:
                info = self.get_progress_info()
                
                # Move cursor up to overwrite previous output
                if self.last_line_count > 0 and self.supports_ansi:
                    print(f"\033[{self.last_line_count}A", end="")
                
                lines = []
                
                # Overall progress
                overall_bar = self.create_progress_bar(info['overall_progress'])
                lines.append(f"Overall: {overall_bar} {info['overall_progress']:5.1f}% | {self.format_size(info['total_downloaded'])}/{self.format_size(info['total_size'])}")
                
                # Fragment progress
                for fragment in info['fragments']:
                    frag_bar = self.create_progress_bar(fragment['progress'], width=20)
                    speed_str = f"{self.format_size(fragment['speed'])}/s" if fragment['speed'] > 0 else "0 B/s"
                    lines.append(f"Frag {fragment['id']+1:2d}: {frag_bar} {fragment['progress']:5.1f}% | {speed_str:>8}")
                
                # Print all lines
                for line in lines:
                    # Clear the line and print
                    if self.supports_ansi:
                        print(f"\033[K{line}")  # \033[K clears from cursor to end of line
                    else:
                        # Fallback: pad with spaces to clear the line
                        print(f"{line:<80}")
                
                self.last_line_count = len(lines)
                
                # If ANSI not supported, add separator
                if not self.supports_ansi:
                    print("-" * 50)
                
                time.sleep(1.0)  # Update every second for better readability
            except:
                break
    
    def _display_full_screen_progress(self):
        """Display full screen progress (requires ANSI support)"""
        while self.display_active:
            try:
                info = self.get_progress_info()
                
                # Clear screen and move cursor to top
                print("\033[2J\033[H", end="")
                
                print("=" * 60)
                print(f"DOWNLOAD PROGRESS - {datetime.now().strftime('%H:%M:%S')}")
                print("=" * 60)
                
                # Overall progress
                overall_bar = self.create_progress_bar(info['overall_progress'])
                overall_speed = sum(f['speed'] for f in info['fragments'])
                print(f"Overall: {overall_bar} {info['overall_progress']:.1f}%")
                print(f"Downloaded: {self.format_size(info['total_downloaded'])} / {self.format_size(info['total_size'])}")
                print(f"Total Speed: {self.format_size(overall_speed)}/s")
                print()
                
                # Fragment progress
                print("Fragment Progress:")
                print("-" * 60)
                for fragment in info['fragments']:
                    frag_bar = self.create_progress_bar(fragment['progress'])
                    speed_str = f"{self.format_size(fragment['speed'])}/s" if fragment['speed'] > 0 else "0 B/s"
                    status = "✓" if fragment['progress'] >= 100 else "↓"
                    print(f"{status} Fragment {fragment['id']+1:2d}: {frag_bar} {fragment['progress']:5.1f}% | {speed_str:>10}")
                
                print("=" * 60)
                
                time.sleep(0.5)
            except:
                break
    
    def _display_simple_progress(self):
        """Simple progress display without overwriting"""
        last_overall = 0
        while self.display_active:
            try:
                info = self.get_progress_info()
                
                # Only update when overall progress changes significantly
                if abs(info['overall_progress'] - last_overall) >= 5:
                    overall_speed = sum(f['speed'] for f in info['fragments'])
                    completed_fragments = sum(1 for f in info['fragments'] if f['progress'] >= 100)
                    
                    print(f"Progress: {info['overall_progress']:5.1f}% | "
                          f"Speed: {self.format_size(overall_speed)}/s | "
                          f"Fragments: {completed_fragments}/{len(info['fragments'])} completed")
                    
                    last_overall = info['overall_progress']
                
                time.sleep(2.0)  # Less frequent updates
            except:
                break
    
    def create_progress_bar(self, percentage: float, width: int = 30) -> str:
        """Create a visual progress bar"""
        filled = int(width * percentage / 100)
        
        if self.supports_ansi:
            # Use Unicode blocks for better visual
            bar = "█" * filled + "░" * (width - filled)
        else:
            # ASCII fallback
            bar = "#" * filled + "-" * (width - filled)
        
        return f"[{bar}]"
    
    @staticmethod
    def format_size(size_bytes: float) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(abs(size_bytes), 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"