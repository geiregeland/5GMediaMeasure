import os

os_platform = os.getenv('5GPLATFORM')

def Merge(dict1, dict2):
    return dict1 | dict2


if os_platform == 'DOCKER':
    RedisConf = {'redishost':'172.240.20.3', 'redisport':6379}
    IperfConf = {'iperfhost':'172.240.20.2','iperfport':30955}

    LocalConf = {'Logpath':'/root/5GMediaMeasure-main/Logs','logfile1':'iperf.cvs','logfile2':'iperf2.cvs','nic':'eth0'}
    owampConf = {'owping':'/root/inst/bin/owping','owconf':'-c100 -i0.1 -L10 -s0 -t -AO -nm','owampdest':f'{IperfConf["iperfhost"]}'}


elif os_platform == 'INTEL1':
    RedisConf = {'redishost':'10.5.1.2', 'redisport':30379}
    IperfConf = {'iperfhost':'10.5.1.2','iperfport':30955}

    LocalConf = {'Logpath':'/home/tnor/5GMediahub/Measurements/Service/Logs','logfile1':'iperf.cvs','logfile2':'iperf2.cvs','nic':'ensf260c'}
    owampConf = {'owping':'/opt/bin/owping','owconf':'-c100 -i0.1 -L10 -s0 -t -AO -nm','owampdest':f'{IperfConf["iperfhost"]}'}



pingConf = {'clientcmd':'ping -c 12 -i 0.3','mport':9055}

G5Conf = Merge(RedisConf,IperfConf)
G5Conf = Merge(G5Conf,LocalConf)
G5Conf = Merge(G5Conf,owampConf)
G5Conf = Merge(G5Conf,pingConf)


    
    
