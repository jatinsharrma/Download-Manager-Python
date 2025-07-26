#!../venv/bin/python3
# -*- coding: utf-8 -*-

"""Advanced Download Manager with Fixed Progress Display"""

import argparse
import asyncio
from core import FragmentDownloader
from cli import DownloadManagerCLI

def main():
    parser = argparse.ArgumentParser(description="Advanced Download Manager with Fixed Progress Display")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a file')
    download_parser.add_argument('url', help='URL to download')
    download_parser.add_argument('-f', '--filename', help='Output filename (optional)')
    download_parser.add_argument('--no-progress', action='store_true', help='Disable progress display')
    download_parser.add_argument('--progress-style', choices=['inline', 'full_screen', 'simple'], 
                                help='Progress display style')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    config_parser.add_argument('--fragments', type=int, help='Max concurrent fragments')
    config_parser.add_argument('--chunk-size', type=int, help='Chunk size in bytes')
    config_parser.add_argument('--timeout', type=int, help='Timeout in seconds')
    config_parser.add_argument('--retry-attempts', type=int, help='Number of retry attempts')
    config_parser.add_argument('--output-dir', help='Output directory')
    config_parser.add_argument('--temp-dir', help='Temporary directory')
    config_parser.add_argument('--no-ssl-verify', action='store_true', help='Disable SSL certificate verification')
    config_parser.add_argument('--ssl-verify', action='store_true', help='Enable SSL certificate verification')
    config_parser.add_argument('--no-progress', action='store_true', help='Disable progress display')
    config_parser.add_argument('--show-progress', action='store_true', help='Enable progress display')
    config_parser.add_argument('--progress-style', choices=['inline', 'full_screen', 'simple'], 
                                help='Progress display style (inline/full_screen/simple)')
    config_parser.add_argument('--save', action='store_true', help='Save configuration to file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = DownloadManagerCLI()
    
    if args.command == 'download':
        # Override progress style if specified
        if args.progress_style:
            cli.config.progress_style = args.progress_style
            cli.downloader = FragmentDownloader(cli.config)
        
        return asyncio.run(cli.download_command(args))
    elif args.command == 'config':
        return cli.config_command(args)

if __name__ == "__main__":
    exit(main())
