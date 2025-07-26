from pathlib import Path
import json

from core import FragmentDownloader, DownloadConfig


class DownloadManagerCLI:
    def __init__(self):
        self.config_file = Path("download_config.json")
        self.config = self.load_config()
        self.downloader = FragmentDownloader(self.config)
    
    def load_config(self) -> DownloadConfig:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                return DownloadConfig(**config_data)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
        
        return DownloadConfig()
    
    def save_config(self):
        """Save current configuration to file"""
        config_dict = {
            'max_concurrent_fragments': self.config.max_concurrent_fragments,
            'chunk_size': self.config.chunk_size,
            'timeout': self.config.timeout,
            'retry_attempts': self.config.retry_attempts,
            'output_directory': self.config.output_directory,
            'temp_directory': self.config.temp_directory,
            'verify_ssl': self.config.verify_ssl,
            'show_progress': self.config.show_progress,
            'progress_style': self.config.progress_style
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        print(f"Configuration saved to {self.config_file}")
    
    def print_config(self):
        """Display current configuration"""
        print("\n=== Download Manager Configuration ===")
        print(f"Max concurrent fragments: {self.config.max_concurrent_fragments}")
        print(f"Chunk size: {self.config.chunk_size} bytes")
        print(f"Timeout: {self.config.timeout} seconds")
        print(f"Retry attempts: {self.config.retry_attempts}")
        print(f"Output directory: {self.config.output_directory}")
        print(f"Temp directory: {self.config.temp_directory}")
        print(f"SSL verification: {'Enabled' if self.config.verify_ssl else 'Disabled'}")
        print(f"Show progress: {'Enabled' if self.config.show_progress else 'Disabled'}")
        print(f"Progress style: {self.config.progress_style}")
        print("=====================================\n")
    
    async def download_command(self, args):
        """Handle download command"""
        # Override progress setting if specified
        if args.no_progress:
            self.config.show_progress = False
            self.downloader = FragmentDownloader(self.config)
        
        success = await self.downloader.download_file(args.url, args.filename)
        return 0 if success else 1
    
    def config_command(self, args):
        """Handle configuration command"""
        if args.show:
            self.print_config()
            return 0
        
        # Update configuration
        if args.fragments:
            self.config.max_concurrent_fragments = args.fragments
        if args.chunk_size:
            self.config.chunk_size = args.chunk_size
        if args.timeout:
            self.config.timeout = args.timeout
        if args.retry_attempts:
            self.config.retry_attempts = args.retry_attempts
        if args.output_dir:
            self.config.output_directory = args.output_dir
        if args.temp_dir:
            self.config.temp_directory = args.temp_dir
        if args.no_ssl_verify:
            self.config.verify_ssl = False
        if args.ssl_verify:
            self.config.verify_ssl = True
        if args.no_progress:
            self.config.show_progress = False
        if args.show_progress:
            self.config.show_progress = True
        if args.progress_style:
            if args.progress_style in ["inline", "full_screen", "simple"]:
                self.config.progress_style = args.progress_style
            else:
                print("Invalid progress style. Use: inline, full_screen, or simple")
                return 1
        
        # Recreate downloader with new config
        self.downloader = FragmentDownloader(self.config)
        
        if args.save:
            self.save_config()
        
        self.print_config()
        return 0