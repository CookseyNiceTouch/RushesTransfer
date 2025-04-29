# Rushes Transfer Tool

A modern application to help transfer video rushes from a camera memory card to project folders on your computer.

## Features

- Automatically detect memory cards
- Browse for custom source locations
- Select from existing projects or create new ones
- Progress tracking with estimated time remaining and transfer speed
- Individual file progress monitoring
- Skip duplicate files to avoid redundant transfers
- Support for common video file formats (.mp4, .mov, .avi, .mxf, .m4v)
- Remembers last used settings and paths
- Modern dark mode UI with CustomTkinter

## Requirements

- Python 3.6 or higher
- CustomTkinter 5.2.0 or higher

## Installation

1. Clone this repository or download the source code
2. Make sure Python is installed on your system
3. Install the requirements:

   ```
   # Using pip
   pip install customtkinter

   # Or using UV
   uv pip install customtkinter
   ```

## Usage

1. Run the application:
   ```
   python main.py
   ```

2. Click "Auto-Detect" to find your camera memory card or use "Browse" to manually select it
3. Select an existing project from the dropdown or create a new one
4. Click "Start Transfer" to begin copying files
5. Monitor both overall and individual file progress during transfer
6. The application will remember your settings for the next time you use it

## Configuration

By default, the application looks for:
- Memory card at `G:\M4ROOT\CLIP`
- Project folders at `D:\NextCloud\Nice Touch\Projects`

To modify these paths, edit the `destination_base_path` and `potential_paths` variables in the source code.

Your last used settings are automatically saved to `rushes_transfer_config.json` in the application directory.

## License

MIT
