# COUB Download Liked Videos

Download your liked videos from coub.com.

This program downloads mp3 and mp4 files and combines them together using `ffmpeg`. All videos will be looped to the length of the audio file. Pages with information about your liked videos will be saved to a JSON dump (`likes.json`). Any future runs will use that instead of the API. In case of multiple sequential runs, it doesn't re-download already downloaded videos; comparison is based on filenames only.

## Features

- Downloads and combines video and audio files.
- Loops videos to match the length of the audio.
- Saves liked videos information to `likes.json`.
- Avoids re-downloading already downloaded videos.

## Prerequisites

- Python 3.x
- `ffmpeg` installed and accessible from the command line.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/coub-dl-liked.git
cd coub-dl-liked
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Obtain your API token:
   - Login to [coub.com](https://coub.com).
   - Open the source of the main page: `view-source:https://coub.com/hot`.
   - Search for `api_token` using `Ctrl+F`. The API token is a 128-character long sequence.
   - Copy the API token and place it in a `.env` file in the project directory as follows:

```
API_TOKEN=your_api_token_here
```

## Usage

### Windows

1. Open Command Prompt and navigate to the project directory:

```cmd
cd coub-dl-liked
```

2. (Optional) Set video and audio quality preference:

```cmd
set VIDEO_QUALITY=high
set AUDIO_QUALITY=high
```

Available values for `VIDEO_QUALITY`: `higher`, `high`, `med`. Default is `high`.
Available values for `AUDIO_QUALITY`: `high`, `med`. Default is `high`.

3. Run the script:

```cmd
python .\download_liked_coubs.py
```

### Linux & macOS

1. Open Terminal and navigate to the project directory:

```bash
cd coub-dl-liked
```

2. (Optional) Set video and audio quality preference and run the script:

```bash
VIDEO_QUALITY=high AUDIO_QUALITY=high python ./download_liked_coubs.py
```

## Output

All video loops will be downloaded to the `videos` directory, organized by year and month.

### Disk Usage Estimation

- 1000 higher quality videos will require approximately 38 GB of disk space.

## License

This project is licensed under the MIT License.