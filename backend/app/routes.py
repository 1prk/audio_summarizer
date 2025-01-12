from flask import Blueprint, request, jsonify
import redis
import uuid

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
api = Blueprint('api', __name__)

@api.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'message': 'pong'})

@api.route('/api/get_audio', methods=['GET'])
def handle_data():
    url = request.args.get('url', 'No message provided')
    task_id = str(uuid.uuid4())

    redis_client.lpush('tasks', f"{task_id}|{url}")
    return jsonify({'task_id': task_id}), 200

@api.route('/api/result/<task_id>', methods=['GET'])
def get_result(task_id):
    result = redis_client.get(f"result:{task_id}")
    if result:
        return jsonify(result), 200

    error = redis_client.get(f"result:{task_id}:error")
    if error:
        return jsonify({'error': error}), 500

    return jsonify({'status': 'processing'}), 202

