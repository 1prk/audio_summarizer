import json
from faster_whisper import WhisperModel
from openai import OpenAI
import yt_dlp
import redis
import os


class Worker:

    def __init__(self):
        with open("/run/secrets/openai_api_key", "r") as secret_file:
            api_key = secret_file.read().strip()
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["WHISPER_INFERENCE_DEVICE"] = "cpu"
        os.environ["WHISPER_COMPUTE_TYPE"] = "int8"

        self.redis_client = redis.StrictRedis(
            host="redis",  # Hostname entspricht dem Servicenamen in docker-compose.yml
            port=6379,  # Standardport für Redis
            decode_responses=True
        )
        self.whisper_model = WhisperModel("tiny")
        self.client = OpenAI()
        with open("/prompts/standard.json", "r") as prompts_file:
            self.prompt = json.load(prompts_file)

    def summary(self, content):
        self.prompt[-1]["content"] = content

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.prompt
        )

        return completion.choices[0].message.content
    def transcribe(self):
        print('hello world.')
        while True:
            #get task from redis queue
            task = self.redis_client.brpop('tasks', timeout=10)
            print(task)
            if not task:
                print('waiting for task')
                continue
            task_id, url = task[1].split("|")

            print(f"Processing Task {task_id} for {url}...")

            ydl_opts = {
                'extract_audio': True,
                'format': 'bestaudio',
                'outtmpl': os.path.join('data/', '%(id)s.mp3')
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_title = info['id']
                ydl.download(url)
                segments, _ = self.whisper_model.transcribe(f'./data/{video_title}.mp3')

                segment_list = []
                for segment in segments:
                    segment_list.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text
                    })

                os.remove(f'./data/{video_title}.mp3')

                response = {
                    "video_info": {
                        "title": video_title,
                        "url": url
                    },
                    "transcription": segment_list,
                }

                audio_summary = self.summary(json.dumps(response))
                print(audio_summary)

                self.redis_client.setex(f"result:{task_id}", 3600, audio_summary)
                print(f"Task {task_id} completed successfully!")

if __name__ == "__main__":
    worker = Worker()
    worker.transcribe()