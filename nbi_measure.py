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
from datetime import datetime,timedelta
from flask import jsonify
import redis
from rq import Worker, Queue, Connection
import iperf3 as ip3
from pathlib import Path
import shlex
from mmapp import Startsample,StartExp,rxtx

Logfile = "/home/tnor/5GMediahub/Measurements/Service/Logs"
ServerPort = os.getenv('IPERF_PORT')
try:
    if ord(ServerPort[0:1]) == 8220:
        ServerPort = ServerPort[1:-1]
except:
    pass

ServerAddress = os.getenv('IPERF_ADDRESS')
try:
    if ord(ServerAddress[0:1]) == 8220:
        ServerAddress = ServerAddress[1:-1]
except :
    pass

MeasurePort = os.getenv('MPORT')
try:
    if ord(MeasurePort[0:1]) == 8220:
        MeasurePort = MeasurePort[1:-1]
except:
    pass
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



@app.route('/registerping/<uid>',methods = ['GET','POST'])
def regping(uid):
    try:
        arguments = request.json
        val=arguments['RTT']
        if float(val)*1.0 == 0:
            print(mytime(),f'Error: we got a RTT = {val}')
            print(arguments)
        #print(arguments)
        dfd = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
        #dfd=df.copy()
        if len(dfd.loc[dfd['Id']==f'{uid}']):
            dfd.loc[dfd['Id']==f'{uid}','RTT'] = float(val)
            #dfd.loc[dfd.index[-1],'RTT']=float(val)

        #df = pd.concat([df,pd.DataFrame(sample,columns=['Date','Uplink','Downlink','RTT'])])
        dfd.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)
        print(mytime(),dfd)


        return f'registerping: ok'
    except Exception as error:
        return errorResponse("Failed call to /registerping",error)

@app.route('/startexperiment/',methods = ['GET','POST'])
def startexp():
    try:
        arguments = request.json
        explength=arguments['delta']
        id=arguments['id']
        uid = uuid.uuid4().hex


        job = Job.create(startexp,args=[uid,delta],id=uid,connection=connRedis())
        delta = timedelta(minutes = 5)
        at=datetime.now()+delta
        r=q.enqueue_job(job)
        return f'startexperiment: ok'
    except Exception as error:
        return errorResponse("Failed call to /startexperiment",error)

@app.route('/registerowamp/<uid>',methods = ['GET','POST'])
def regowamp(uid):
    try:
        arguments = request.json
        jitter=arguments['jitter']
        availebility=arguments['availebility']
        delay=arguments['delay']

        if float(jitter)*1.0 == 0:
            print(mytime(),f'Error: we got jitter = {jitter}')
            print(arguments)
        
        if float(availebility)*1.0 == 0:
            print(mytime(),f'Error: we got A = {availebility}')
            print(arguments)

        if float(delay)*1.0 == 0:
            print(mytime(),f'Error: we got delay = {delay}')
            print(arguments)


        #print(arguments)
        dfd = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
        #dfd=df.copy()
        if len(dfd.loc[dfd['Id']==f'{uid}']):
            dfd.loc[dfd['Id']==f'{uid}','Delay']=float(delay)
            dfd.loc[dfd['Id']==f'{uid}','Availebility']=float(availebility)
            dfd.loc[dfd['Id']==f'{uid}','Jitter']=float(jitter)
        else:
            print(mytime(),f'Failed to write data to pandas for uid:{uid}')

        #df = pd.concat([df,pd.DataFrame(sample,columns=['Date','Uplink','Downlink','RTT'])])
        dfd.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)
        print(mytime(),dfd)


        return f'registerowamp: ok'
    except Exception as error:
        return errorResponse("Failed call to /registerowamp",error)


#Reliability	The likelihood of a service failing, i.e. 	Mean time between failure (MTBF). 
@app.route('/getmtbf',methods=['GET','POST'])
def getmtbf():    
    df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
    a=df['Availebility'].tail(10)
    u=0
    d=0
    for i in a:
        if i>=1.0:
            u+=600
        else:
            d+=1
    if d:
        mtbf=u/d
    else:
        return 1.0

@app.route('/getdelay',methods=['GET','POST'])
def getdelay():
    df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
    return df['Delay'].tail(10).mean()

@app.route('/getjitter',methods=['GET','POST'])
def getjitter():
    df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
    return df['Jitter'].tail(10).mean()

@app.route('/getavailebility',methods=['GET','POST'])
def getavailebility():
    df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')   
    return df['Availebility'].tail(10).mean()

@app.route('/getdl',methods=['GET','POST'])
def getdl():
    df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')  
    return df['Downlink'].tail(10).mean()

@app.route('/getul',methods=['GET','POST'])
def getul():
    df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
    return df['Uplink'].tail(10).mean()




   
@app.route('/startiperf3', methods=['GET', 'POST'])
def startsiperf3():
   try:
       uid = uuid.uuid4().hex
       print("starting iperf3")
       job = Job.create(Startsample,args=[uid],id=uid,connection=connRedis())
       
       r=q.enqueue_job(job)

       job = Job.create(StartExp,args=[uid],id=uid,connection=connRedis())
       
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
