# coub-dl-liked
Download your liked videos from coub.com. Program downloads mp3, mp4 files and combines them together using `ffmpeg`. All videos will be looped to the length of the audio file. Pages with an info about your liked videos will be saved to json dump: `all_likes.json`

### How to use it
Install python

Install dependencies:
```
pip install -r requirements.txt
```
Install [ffmpeg](https://ffmpeg.org/) programm ([Windows detailed instruction](https://www.geeksforgeeks.org/how-to-install-ffmpeg-on-windows/))

Go to https://coub.com/api/v2/users/me and find your `api_token`: a long sequence of characters, copy it

Now you're ready to download your sweet COUB's:

Windows:
```
cd coub-dl-liked
set API_TOKEN=your_long_token
python .\download_liked_coubs.py
```
Linux&MAC:
```
cd coub-dl-liked
API_TOKEN=your_long_token python ./download_liked_coubs.py
```

All video loops would be downloaded to `/videos` directory.

Tested on Windows 10, Ubuntu 20.04, python 3.10.3
