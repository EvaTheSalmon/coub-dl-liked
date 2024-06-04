import os
import sys
import json
import logging
import asyncio
import urllib.request
from datetime import datetime
from dotenv import load_dotenv
import aiohttp
import soundfile as sf
import ffmpeg
import unicodedata
import re
import traceback


VIDEO_QUALITIES = ["higher", "high", "med"]
AUDIO_QUALITIES = ["high", "med"]
PAGES_DUMP_JSON_FILENAME = "likes.json"


load_dotenv(".env")
API_TOKEN = os.getenv("API_TOKEN")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.FileHandler(f"logs/{datetime.now().strftime('%d-%b-%Y %H_%M_%S')}.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore", errors="xmlcharrefreplace")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


async def get_likes_page_as_json(session, page, api_token):
    """Fetch a single page of likes as JSON."""
    logging.debug(f"Fetching page {page}")
    async with session.get(f"https://coub.com/api/v2/timeline/likes?page={page}&per_page=25&api_token={api_token}") as response:
        return await response.json()


async def save_likes_pages():
    """Fetch and save all pages of likes."""
    if not API_TOKEN:
        sys.exit("API_TOKEN environment variable must be specified")

    async with aiohttp.ClientSession() as session:
        first_page = await get_likes_page_as_json(session, 1, API_TOKEN)
        total_pages = first_page.get("total_pages", 0)
        logging.info(f"Total page count: {total_pages}")
        logging.info("Fetching all pages...")
        
        pages = await asyncio.gather(*[get_likes_page_as_json(session, i, API_TOKEN) for i in range(1, total_pages + 1)])
        logging.info(f"{len(pages)} pages fetched")

    with open(PAGES_DUMP_JSON_FILENAME, "w", encoding="utf-8") as f:
        json.dump(pages, f)
    logging.info("COUB's info dumped to a file")


def get_coubs_from_likes_pages_dump():
    """Load COUBs from the JSON dump."""
    with open(PAGES_DUMP_JSON_FILENAME, "r", encoding="utf-8") as f:
        pages = json.load(f)
    logging.info("COUB's info loaded from a file")

    coubs = [coub for page in pages for coub in page.get("coubs", [])]
    logging.info(f"Total COUB's video count: {len(coubs)}")
    return coubs


def get_media_url(coub, quality, media_type, qualities):
    """Get the URL for the specified media type and quality."""
    media_info = coub["file_versions"]["html5"].get(media_type, {})
    if quality in media_info:
        return media_info[quality]["url"]
    
    logging.warning(f"{media_type} with quality {quality} not found, trying lower qualities")
    for q in qualities[qualities.index(quality):]:
        if q in media_info:
            return media_info[q]["url"]
    return None


def delete_file_if_exists(filepath):
    """Delete the file if it exists."""
    if filepath and os.path.exists(filepath):
        os.remove(filepath)


def validate_quality(quality, allowed_qualities, quality_type):
    """Validate the specified quality."""
    if quality not in allowed_qualities:
        sys.exit(f"Can't use {quality_type} quality {quality}, allowed values: {allowed_qualities}")


def process_coub(coub, index, video_quality, audio_quality):
    """Process and download a COUB."""
    try:
        id = coub["permalink"]
        title = slugify(coub["title"], True)
        liked_date = coub["updated_at"]
        filename = f"{title}-{id}" if title else id

        logging.info(f"Downloading video {index + 1}, filename: {filename.encode('utf-8', errors='xmlcharrefreplace')}")

        date_year_path = os.path.join("videos", liked_date[:4], liked_date[5:7])
        os.makedirs(date_year_path, exist_ok=True)

        out_video_fpath = os.path.join(date_year_path, f"{filename}.mp4").encode("utf-8", errors="xmlcharrefreplace")
        if os.path.exists(out_video_fpath):
            logging.info(f"{out_video_fpath} already exists, ignoring.")
            return

        download_and_process_coub(coub, id, video_quality, audio_quality, out_video_fpath)
    except Exception as e:
        logging.error(f"Failed to process video {id}")
        logging.error(traceback.format_exc())


def download_and_process_coub(coub, id, video_quality, audio_quality, out_video_fpath):
    """Download and process COUB's video and audio."""
    out_video_fname_tmp = f"{id}_tmp.mp4"
    out_wav_fname = f"{id}.wav"
    video_fname = None
    mp3_fname = None

    try:
        video_url = get_media_url(coub, video_quality, "video", VIDEO_QUALITIES)
        video_fname = video_url.split("/")[-1]
        urllib.request.urlretrieve(video_url, video_fname)

        mp3_url = get_media_url(coub, audio_quality, "audio", AUDIO_QUALITIES)
        if mp3_url:
            mp3_fname = mp3_url.split("/")[-1]
            urllib.request.urlretrieve(mp3_url, mp3_fname)
            process_audio(mp3_fname, out_wav_fname)
            wav_len = get_wav_length(out_wav_fname)
            loop_video(video_fname, out_video_fname_tmp, wav_len)
            combine_video_audio(out_video_fname_tmp, mp3_fname, out_video_fpath, coub)
        else:
            os.rename(video_fname, out_video_fpath)
    finally:
        cleanup_temp_files([out_video_fname_tmp, video_fname, out_wav_fname, mp3_fname])


def process_audio(mp3_fname, out_wav_fname):
    """Process audio using ffmpeg."""
    ffmpeg.input(mp3_fname).output(out_wav_fname, acodec="pcm_s16le", ac=2, ar="44100", f="wav", loglevel="error").run()


def get_wav_length(wav_fname):
    """Get the length of the WAV file."""
    x, sr = sf.read(wav_fname)
    return len(x) / sr


def loop_video(video_fname, out_video_fname_tmp, duration):
    """Loop video using ffmpeg."""
    ffmpeg.input(video_fname, stream_loop="-1").output(out_video_fname_tmp, t=duration, c="copy", loglevel="error").run()


def combine_video_audio(video_fname, audio_fname, out_fpath, coub):
    """Combine video and audio using ffmpeg."""
    channel_title = coub["channel"]["title"]
    channel_permalink = coub["channel"]["permalink"]
    tags = ";".join(tag["title"] for tag in coub["tags"])
    external_video_link = coub["media_blocks"].get("external_video", {}).get("url", "")

    comment = (
        f"Author: {channel_title}\n"
        f"Link: https://coub.com/{channel_permalink}\n"
        f"Original video: https://coub.com/view/{coub['permalink']}\n"
        f"Tags: {tags}\n"
        f"External video: {external_video_link}"
    )

    ffmpeg.input(video_fname, i=audio_fname).output(
        out_fpath, vcodec="copy", acodec="aac", strict="experimental", 
        metadata={"title": coub["title"], "comment": comment, "creation_time": coub["updated_at"]},
        loglevel="error"
    ).run()


def cleanup_temp_files(filenames):
    """Clean up temporary files."""
    for fname in filenames:
        if fname and os.path.exists(fname):
            os.remove(fname)


async def main():
    VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "high").lower()
    AUDIO_QUALITY = os.getenv("AUDIO_QUALITY", "high").lower()

    validate_quality(VIDEO_QUALITY, VIDEO_QUALITIES, "video")
    validate_quality(AUDIO_QUALITY, AUDIO_QUALITIES, "audio")

    logging.info(f"Using {VIDEO_QUALITY} video quality")
    logging.info(f"Using {AUDIO_QUALITY} audio quality")

    if not os.path.exists(PAGES_DUMP_JSON_FILENAME):
        await save_likes_pages()

    coubs = get_coubs_from_likes_pages_dump()

    proceed = input("Proceed to download. y/n (y) ")
    if proceed.lower() not in ["", "y"]:
        sys.exit(0)

    for i, coub in enumerate(coubs):
        process_coub(coub, i, VIDEO_QUALITY, AUDIO_QUALITY)


if __name__ == "__main__":
    asyncio.run(main())
