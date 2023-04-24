import os
import subprocess
from flask import Flask, session, flash, json, request,jsonify
from rq import Queue, Retry
from rq.job import Job 
from worker import errorResponse
import rq_dashboard
import worker as myworker
import uuid
from app import *


#q = Queue(connection = myworker.connRedis(), default_timeout = 7200)
q = Queue('low',connection = myworker.connRedis(), default_timeout = 7200)

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
    try:
        arguments = request.json
        val=arguments['RTT']
        #print(arguments)
        dfd = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
        #dfd=df.copy()
        dfd.loc[dfd.index[-1],'RTT']=float(val)

        #df = pd.concat([df,pd.DataFrame(sample,columns=['Date','Uplink','Downlink','RTT'])])
        dfd.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)
        print(mytime(),df)


        return f'registerping: ok'
    except Exception as error:
        return errorResponse("Failed call to /registerping",error)


   
@app.route('/startiperf3', methods=['GET', 'POST'])
def startsiperf3():
   try:
    uid = uuid.uuid4().hex
    print("starting iperf3")
    job = Job.create(Start_sample,args=[uid],id=uid,connection=myworker.connRedis())

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
