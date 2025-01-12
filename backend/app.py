from app import create_app
import redis

redis_client = redis.StrictRedis(
    host="redis",  # Hostname entspricht dem Servicenamen in docker-compose.yml
    port=6379,     # Standardport für Redis
    decode_responses=True
)


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)