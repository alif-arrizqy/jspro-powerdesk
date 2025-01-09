import redis

host = "localhost"
connection = redis.Redis(host=host, password='', decode_responses=True)
