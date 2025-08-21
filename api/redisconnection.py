import redis

host = "localhost"
password = ""

connection = redis.Redis(host=host, password=password, decode_responses=True)
