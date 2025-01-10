from flask import Blueprint, request, jsonify
from faster_whisper import WhisperModel
import yt_dlp
from dotenv import load_dotenv
import os

load_dotenv()
api = Blueprint('api', __name__)
whisper_model = WhisperModel("tiny")

@api.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'message': 'pong'})

@api.route('/api/get_audio', methods=['GET'])
def handle_data():
    url = request.args.get('url', 'No message provided')
    model = whisper_model

    ##TODO: wrapper für po-token und cookie jar
    ydl_opts = {
        'cookiefile': 'cookies.txt',
        'po-token': os.getenv('PO_TOKEN'),
        'extract_audio': True,
        'format': 'bestaudio',
        'outtmpl': os.path.join('data/', '%(id)s.mp3')
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_title = info['id']
        ydl.download(url)
        segments, info = model.transcribe(f'./data/{video_title}.mp3')

        segment_list = []
        for segment in segments:
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
            print(segment)

        response = {
            "video_info": {
                "title": video_title,
                "url": url
            },
            "transcription": segment_list,
        }

        return jsonify(response)
