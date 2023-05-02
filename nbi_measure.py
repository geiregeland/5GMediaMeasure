import os
import subprocess
from flask import Flask, session, flash, json, request,jsonify
from rq import Queue
from rq.job import Job 
import rq_dashboard
#from mworker import connRedis
#import worker as myworker
import uuid
#from mmapp import mytime
import pandas as pd
from datetime import datetime
from flask import jsonify
import redis
from rq import Worker, Queue, Connection
import iperf3 as ip3
from pathlib import Path
from mmapp import Startsample

Logfile = "/home/tnor/5GMediahub/Measurements/Service/Logs"
ServerPort = os.getenv('IPERF_PORT')
ServerAddress = os.getenv('IPERF_ADDRESS')
MeasurePort = os.getenv('MPORT')

#q = Queue(connection = myworker.connRedis(), default_timeout = 7200)
def mytime():
  now = datetime.now()
  return(str(now.time()).split('.')[0])


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
        port = os.getenv('REDIS_PORT')

        redis_url = f'redis://{host}:{port}'
        print(redis_url)
        return connect_redis(redis_url)
    
    except Exception as error:
        return errorResponse("Failed main redis connection",error)



      
q = Queue('low',connection = connRedis(), default_timeout = 7200)

app = Flask(__name__)
# Configuration Variables
app.config["DEBUG"] = True
app.config["RQ_DASHBOARD_REDIS_PORT"] = os.getenv('REDIS_PORT')
app.config["RQ_DASHBOARD_REDIS_URL"] = f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}"

#pwd_get= subprocess.run(['pwd'],check=True,text=False,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#app.config['UPLOAD_FOLDER'] = pwd_get.stdout.decode('utf-8')[:-1]+"/uploades"

app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint,url_prefix='/rq')



@app.route('/registerping/',methods = ['GET','POST'])
def regping():
    #try:
        arguments = request.json
        val=arguments['RTT']
        if float(val)*1.0 == 0:
            print(mytime(),f'Error: we got a RTT = {val}')
            print(arguments)
        #print(arguments)
        dfd = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
        #dfd=df.copy()
        dfd.loc[dfd.index[-1],'RTT']=float(val)

        #df = pd.concat([df,pd.DataFrame(sample,columns=['Date','Uplink','Downlink','RTT'])])
        dfd.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)
        print(mytime(),dfd)


        return f'registerping: ok'
    #except Exception as error:
        return errorResponse("Failed call to /registerping",error)


   
@app.route('/startiperf3', methods=['GET', 'POST'])
def startsiperf3():
   try:
       uid = uuid.uuid4().hex
       print("starting iperf3")
       job = Job.create(Startsample,args=[uid],id=uid,connection=connRedis())
       
       r=q.enqueue_job(job)
       return f'starteiperf3: ok,  request_id:{uid}'
   except Exception as error:
       return errorResponse("Failed call to /startiperf3",error)


   
@app.route('/')
def home():
   try:
       print("jobs in Q: "+str(q.jobs))
       return "jobs in Q:"+str(len(q))
   except Exception as error:
       return errorResponse("Failed call to /",error)

   
   
if __name__ == '__main__':
  port = int(os.environ.get('PORT', 9055))
  app.run(host = '0.0.0.0', port = port)
