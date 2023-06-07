import os
import sys
from flask import jsonify
import redis
from rq import Worker, Queue, Connection



def errorResponse(message, error):
    print(f'{message}: {error}')
    return jsonify({'Status': 'Error', 'Message': message, 'Error': f'{error}'}), 403

    
def connect_redis(url):
    try:
        conn = redis.from_url(url)
        return conn
    except Exception as error:
        return errorResponse("Could not connect to redis",error)

def connRedis():
    try:
        #redisPort=get_redisport()
        #redis_url = os.getenv('REDIS_URL', 'redis://localhost:'+redisPort)
        host = os.getenv('REDIS_HOST')
        try:
            if ord(host[0:1]) == 8220:
                host = host[1:-1]
        except:
            pass
        port = os.getenv('REDIS_PORT')
        try:
            if ord(port[0:1]) == 8220:
                port = port[1:-1]
        except:
            pass
        
        redis_url = f'redis://{host}:{port}'
        print(redis_url)
        return connect_redis(redis_url)
    
    except Exception as error:
        return errorResponse("Failed main redis connection",error)

    
if __name__ == '__main__':

    conn = connRedis()
    listen = ['low']
    
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
