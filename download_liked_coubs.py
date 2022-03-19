import os
import urllib
import urllib.request
import aiohttp
import soundfile as sf
import json
import traceback
import asyncio
import subprocess

# https://coub.com/api/v2/users/me
api_token = os.getenv("API_TOKEN")
if api_token is None:
    print("API_TOKEN environment variable must be specified")
    exit(1)

async def get_page_as_json(session, i):
    async with session.get(f"https://coub.com/api/v2/timeline/likes?page={i}&per_page=25&api_token={api_token}") as response:
        return await response.json()

async def main():
    # async fetch all "pages" with videos info
    async with aiohttp.ClientSession() as session:
        total_pages = (await get_page_as_json(session, 1))['total_pages']
        print(f"Total page count: {total_pages}")
        print("Fetching all pages...")
        pages = await asyncio.gather(*(get_page_as_json(session, i) for i in range(1, total_pages+1)))
        print(f"{len(pages)} pages fetched")
   
    # save fetched info
    with open('all_likes.json', 'w') as outfile:
        json.dump(pages, outfile)

    coubs = []
    for i in range(len(pages)):
        coubs = coubs + pages[i]['coubs']

    print(f'Total COUB\'s video count: {len(coubs)}')

    proceed = input("Proceed to download. y/n (y) ")
    if len(proceed) != 0 and proceed.lower() != 'y':
        exit()

    # download liked videos to dir videos/
    for i, coub in enumerate(coubs):
        try:
            id = coub['permalink']
            print("-" * 24)
            print(f"Downloading video {i+1}, permalink: {id}")

            mp3_url = coub['file_versions']['html5']['audio']['high']['url']
            mp3_fln = mp3_url.split('/')[-1]
            video_url = coub['file_versions']['html5']['video']['high']['url']
            video_fln = video_url.split('/')[-1]
            
            urllib.request.urlretrieve(mp3_url, mp3_fln)
            urllib.request.urlretrieve(video_url, video_fln)

            out_video_fln = f'{i+1}_{id}.mp4'
            out_video_fln_tmp = f'{id}_tmp.mp4'
            out_wav_fln = f'{id}.wav'

            # convert mp3 to wav
            subprocess.run(['ffmpeg', '-i', mp3_fln, '-vn', '-acodec', 'pcm_s16le', 
                '-ac', '2', '-ar', '44100', '-f', 'wav', out_wav_fln]).check_returncode()
            # read wav and get file len in seconds
            x, sr = sf.read(f'{out_wav_fln}')
            wav_len = len(x)/sr
            # loop video to duration of file len
            subprocess.run(['ffmpeg', '-stream_loop', '-1', '-t', str(wav_len), 
                '-i', video_fln, '-c', 'copy', out_video_fln_tmp]).check_returncode()
            
            # combine MP3 with looped video, add metadata
            channel_title = coub['channel']['title']
            channel_permalink = coub['channel']['permalink']
            tags = []
            for tag in coub['tags']:
                tags.append(tag['title'])
            tags_str = ';'.join(tags)
            comment = 'Author: %s\nLink: %s\nOriginal video: %s\nTags: %s' % (
                    channel_title,
                    f'https://coub.com/{channel_permalink}',
                    f'https://coub.com/view/{id}',
                    tags_str)
            title = coub['title']
            subprocess.run(["ffmpeg", "-i", out_video_fln_tmp, "-i", mp3_fln, 
                                    "-metadata", "title=%s" % title,
                                    "-metadata", "comment=%s" % comment,
                                    "-c:v", "copy", "-c:a", "aac", f"videos/{out_video_fln}"]).check_returncode()
            # remove temp files
            os.remove(out_video_fln_tmp)
            os.remove(out_wav_fln)
            os.remove(mp3_fln)
            os.remove(video_fln)
        except Exception as e:
            print("-" * 24)
            print(traceback.format_exc())
            proceed = input("Caught some errors, proceed downloading? y/n (y) ")
            if len(proceed) != 0 and proceed.lower() != 'y':
                exit()
            pass

if __name__ == '__main__':
    asyncio.run(main())