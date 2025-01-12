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
    task_key = f"result:{task_id}"
    redis_client.hset(task_key, mapping={
        "status": "processing"
    })

    return jsonify({'task_id': task_id}), 200

@api.route('/api/result/<task_id>', methods=['GET'])
def get_result(task_id):
    try:
        # Redis-Schlüssel
        task_key = f"result:{task_id}"

        # Ergebnis und Status aus Redis abrufen
        result = redis_client.hget(task_key, "result")
        status = redis_client.hget(task_key, "status")

        if status == "done" and result:
            return jsonify({
                "status": status,
                "result": result
            }), 200

        # Falls Status noch "processing" ist
        if status == "processing":
            return jsonify({"status": "processing"}), 202

        # Falls kein Ergebnis gefunden wurde, prüfe auf Fehler
        error = redis_client.hget(task_key, "error")
        if error:
            return jsonify({
                "status": "failed",
                "error": error
            }), 500

        # Falls kein Status oder Ergebnis existiert
        return jsonify({"status": "unknown"}), 404

    except redis.exceptions.RedisError as e:
        return jsonify({"error": f"Redis error: {str(e)}"}), 500
