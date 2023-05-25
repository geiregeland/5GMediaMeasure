import time
from functools import wraps
import subprocess
import statistics
import shlex
#from worker import errorResponse
import iperf3 as ip3
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import requests


Logfile = "/home/tnor/5GMediahub/Measurements/Service/Logs"
ServerPort = os.getenv('IPERF_PORT')
ServerAddress = os.getenv('IPERF_ADDRESS')
MeasurePort = os.getenv('MPORT')
owping = os.getenv('OWPING')
nic = os.getenv("NIC")
duration = 5 #5s if iperf

def mytime():
  now = datetime.now()
  return(str(now.time()).split('.')[0])


def logged(func):
    @wraps(func)
    def with_logging(*args, **kwargs):
        print(mytime(),func.__name__ + " was called")
        return func(*args, **kwargs)
    return with_logging


@logged
def iperfclient():
    print(mytime(),"Starting iperf3 server")
    r= requests.get(f'http://{ServerAddress}:{MeasurePort}/startiperf3')
    
    uid = r.content.decode('utf-8').split(':')[1]

    if not 'starteiperf3: ok' in r.content:
        print(mytime(),"Could not start iperf3 server")
  
    time.sleep(1)

    client = ip3.Client()
    client.server_hostname = ServerAddress
    client.zerocopy = True
    client.verbose = False
    client.reverse = False
    client.duration = duration
    print(f'Serverport: {ServerPort}')
    client.port = ServerPort
    #client.num_streams = 10
    print(mytime(),"Starting iperf3 client run 1")
    client.run()
    
    time.sleep(1)
    client.reverse=True

    print(mytime(),"Starting iperf3 client run 2")

    client.run()

    time.sleep(2)
    print(mytime(),"Starting ping test")

    rtt=ping_addr(ServerAddress)

    print(mytime(),f'Registering RTT result: {rtt}')

    r = requests.get(f'http://{ServerAddress}:{MeasurePort}/registerping/{uid}', json={'RTT':f'{rtt}'})

    if not 'registerping: ok' in r.content:
        print(mytime(),"Could not register RTT")

    results = owamp(ServerAddress)

    print(mytime(),f'Registering OWAMP result: {results}')

    r = requests.get(f'http://{ServerAddress}:{MeasurePort}/registerowamp/{uid}', json={'availebility':f'{results["A"]}','delay':f'{results["mmedi"]}','jitter':f'{results["jitter"]}'})
    #register 
    #print(str(r.content.decode('utf-8')))
    #print('registerowamp: ok')
    if 'registerowamp: ok' != str(r.content.decode('utf-8')):
        print(mytime(),"Could not register OWAMP")



@logged
def ping_addr(dest):
    results=[]
    try:
        process = subprocess.Popen(shlex.split(f"ping -c 12 -i 0.3 {dest}"),stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        pipe=process.stdout

        for line in pipe:
            line = line.decode('utf-8')
            if 'ttl' in line:
                line=line.split("time=")[1].split(" ms")[0]

                results.append(float(line))
        results.sort()
        return statistics.mean(results[1:-1])
    except Exception as error:
        print(mytime(),f"Error in process: {error}")
        return 0

@logged
def owamp(dest):
    results={}
    try:
        process = subprocess.Popen(shlex.split(f'{owping} -c100 -i0.1 -L10 -s0 -t -AO -nm {dest}'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

        pipe=process.stdout
        for line in pipe:
            line = line.decode('utf-8')
            if 'sent' in line:
                tmp=line.split(',')
                sent=tmp[0].split(' ')[0].strip()
                loss=tmp[1].split(' ')[1].strip()
                results['sent'] = sent
                results['loss'] = loss
            if 'delay' in line:
                tmp=line.split('max =')[1]
                mmin=tmp.split('/')[0].strip()
                mmedi=tmp.split('/')[1].strip()
                mmax=tmp.split('/')[2].split(' ms')[0].strip()
                results['mmedi'] = mmedi
            if 'jitter' in line:
                tmp=line.split(' = ')[1]
                jitter=tmp.split(' ms')[0].strip()
                results['jitter'] = jitter

    except Exception as error:
        print(mytime(),f"Error in owping process: {error}")
        return 0
    #calculate awailebility
    A  = (float(sent)-float(loss))/float(sent)
    results['A'] = A

    return results


        
@logged
def iperf3Throughput(uid):
    time.sleep(1)
    s = ip3.Server()
    s.port = ServerPort
    print("starting iperfserver at:",ServerAddress)
    s.bind_address = ServerAddress
    s.json_output = True

    results=s.run()
    l=results.json
    uplink=l['end']['streams'][0]['receiver']['bits_per_second']

    print(mytime(),f"uplink:{uplink}")

    results=s.run()
    l=results.json
    downlink=l['end']['streams'][0]['sender']['bits_per_second']

    print(mytime(),f"downlink:{downlink}")
    return {'Date':[datetime.now().strftime("%Y-%d-%m %H:%M:%S")],'Uplink':[uplink],'Downlink':[downlink],'Id':uid}



@logged
def StartExp(uid,delta=5):
    time.sleep(1)
    interval = delta/25
    m = delta
    rx_data = []
    tx_data = []
    results = {}

    while m>0:
      process = subprocess.Popen(shlex.split(f'cat /sys/class/net/{nic}/statistics/tx_bytes'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      pipe = process.stdout
      for line in pipe:
        tx = int(line)
        if len(tx_data):
            d = tx-tx_data[-1][1]/interval
            tx_data.append((tx,d))
        else:
            tx_data.append((tx,0))

      process = subprocess.Popen(shlex.split(f'cat /sys/class/net/{nic}/statistics/rx_bytes'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
      pipe = process.stdout
      for line in pipe:
        rx = int(line)
        if len(rx_data):
            d = rx-rx_data[-1][1]/interval
            rx_data.append((rx,d))
        else:
            rx_data.append((rx,0))

      m -= interval
      time.sleep(interval)

    # rx_data=[(s1,0),(s2,s2-s1/interval),....]
    # tx_data=[(s1,0),(s2,s2-s1/interval),....]

    average_rx = (rx_data[-1][0] - rx_data[0][0])/delta
    average_tx = (tx_data[-1][0] - tx_data[0][0])/delta

    results['peak_rx'] = max([i[1] for i in rx_data[1:]])
    results['peak_tx'] = max([i[1] for i in tx_data[1:]])
    results['rx_var'] = sum((i[1] - average_rx) ** 2 for i in rx_data[1:]) / len(rx_data[1:])
    results['tx_var'] = sum((i[1] - average_tx) ** 2 for i in tx_data[1:]) / len(tx_data[1:])
    results['average_rx'] = average_rx
    results['average_tx'] = average_tx

    dfd = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')

    if len(dfd.loc[dfd['Id']==f'{uid}']):
        dfd.loc[dfd['Id']==f'{uid}','peak_rx']=results['peak_rx']
        dfd.loc[dfd['Id']==f'{uid}','peak_tx']=results['peak_tx']
        dfd.loc[dfd['Id']==f'{uid}','rx_var']=results['rx_var']
        dfd.loc[dfd['Id']==f'{uid}','tx_var']=results['tx_var']
        dfd.loc[dfd['Id']==f'{uid}','average_rx']=results['average_rx']
        dfd.loc[dfd['Id']==f'{uid}','average_tx']=results['average_tx']

    else:
        print(mytime(),f'Failed to write data to pandas for uid:{uid}')
        dfd.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)
 
    return results

def rxtx(uid):
    return 0

def getLogfile():
    try:
        os.makedirs(Logfile,exist_ok=True)
    except Exception as error:
        print(mytime(),f'Directory {Logfile} can not be created')

    if not os.path.exists(f'{Logfile}/iperf.csv'):
        df = pd.DataFrame({'Date': pd.Series(dtype='str'),
                           'Id':pd.Series(dtype=str),
                   'Uplink': pd.Series(dtype='float'),
                   'Downlink': pd.Series(dtype='float'),
                   'peak_tx': pd.Series(dtype='float'),
                   'peak_rx': pd.Series(dtype='float'),
                   'rx_var': pd.Series(dtype='float'),
                   'tx_var': pd.Series(dtype='float'),
                   'average_rx': pd.Series(dtype='float'),
                   'average_tx': pd.Series(dtype='float'),
                   'RTT':pd.Series(dtype='float')})
        df['Date']=pd.to_datetime(df.Date)
        df.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)

    else:
        df = pd.read_csv(f'{Logfile}/iperf.csv',sep=',')
        print(mytime(),f'Reading file {Logfile}/iperf.csv')



def Startsample(uid):
    df = getLogfile()

    sample = iperf3Throughput(uid)
    #s = ip3.Server()
    #s.port = ServerPort
    #print("starting iperfserver at:",ServerAddress)
    #s.bind_address = ServerAddress
    #s.json_output = True

    #results=s.run()
    #l=results.json
    #uplink=l['end']['streams'][0]['receiver']['bits_per_second']

    #print(mytime(),f"uplink:{uplink}")

    #results=s.run()
    #l=results.json
    #downlink=l['end']['streams'][0]['sender']['bits_per_second']

    #print(mytime(),f"downlink:{downlink}")
    #sample= {'Date':[datetime.now().strftime("%Y-%d-%m %H:%M:%S")],'Uplink':[uplink],'Downlink':[downlink]}

    df = pd.concat([df,pd.DataFrame(sample,columns=['Date','Uplink','Downlink','RTT','Id'])])
    df.to_csv(f'{Logfile}/iperf.csv', sep=',', encoding='utf-8',index=False)
    print(mytime(),df)

    #df.loc[df['sample_id'] == 'uuid','jitter']=jitter
    #df.loc[df['sample_id'] == 'uuid','RTT']=RTT

def getjitter():
        df = pd.read_csv(f'Logs/iperf2.csv',sep=';')
        jitter = 0
        print(df['Jitter'].tail(10).mean())

        return jitter


if __name__=='__main__':
   #owamp(ServerAddress)
    getjitter()
