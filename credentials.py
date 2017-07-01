import os
import redis
token = os.environ['TELEGRAM_TOKEN']
admins = [os.environ['ADMIN1'], os.environ['ADMIN2'], os.environ['ADMIN3'], os.environ['ADMIN4'], os.environ['ADMIN5']]
r = redis.from_url(os.environ.get("REDIS_URL"))
p = redis.from_url(os.environ.get("COBALT_URL"))
