###demo code provided by Steve Cope at www.steves-internet-guide.com
##email steve@steves-internet-guide.com
###Free to use for any purpose
"""retained messages list and delete"""
import paho.mqtt.client as mqtt  #import the client
import time
QOS0=0
QOS1=0
QOS2=0
RETAIN=True
CLEAN_SESSION=True
cname="retained-script"
USERNAME=""
PASSWORD=""
port=1883
broker="192.168.1.206"
#broker="iot.eclipse.org"
port=1883
mqttclient_log=False #client logging
inputs={}
inputs["username"]=""
inputs["password"]=""
inputs["clear_retained"]=False
inputs["verbose"] =False
inputs["port"]=port
inputs["broker"]=broker
inputs["topic"]="house/#"
#List and optionally delete retained messages

retained_topics=[]
def on_log(client, userdata, level, buf):
    print("log: ",buf)
def Initialise_client_object():  
    mqtt.Client.bad_connection_flag=False
    mqtt.Client.suback_flag=False
    mqtt.Client.connected_flag=False
    mqtt.Client.disconnect_flag=False


def Initialise_clients(cname,clean_session=True):
    #flags set
    client= mqtt.Client(cname)
    if mqttclient_log: #enable mqqt client logging
        client.on_log=on_log
    client.on_connect= on_connect        #attach function to callback
    client.on_message=on_message        #attach function to callback
    client.on_subscribe=on_subscribe

    return client
def on_message(client, userdata, message):
    #time.sleep(1)
    topic=message.topic
    msg=str(message.payload.decode("utf-8"))
    if verbose:     
        print("message received  ",msg,"topic",topic,"retained ",message.retain)
    if message.retain==1:
        retained_topics.append((topic,msg))
    
def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True
    else:
        client.bad_connection_flag=True
        if rc==5:
            print("broker requires authentication")
def on_subscribe(client, userdata, mid, granted_qos):
    #print("subscribed ok ")
    client.suback_flag=True            
def on_publish(client, userdata, mid):
    print("message published "  )

def clear_retained(retained): #accepts single topic or list
    msg=""
    if isinstance(retained[0],str):
        client.publish(retained[0],msg,qos=QOS0,retain=RETAIN)
    else:
        try:
            for t in retained:
                client.publish(t[0],msg,qos=QOS0,retain=RETAIN)
                print ("Clearing retaind on ",msg,"topic -",t[0]," qos=",QOS0," retain=",RETAIN)
        except:
            Print("problems with topic")
            return -1
    
##############
def get_input(argv):

    try:
      opts, args = getopt.getopt(argv,"hb:p:t:cvu:P:")
    except getopt.GetoptError:
        print (sys.argv[0]," -b <broker> -p <port> -t <topic> -v \
<verbose True or False>, -c <clear retained True or False>," )
        sys.exit(2)
    for opt, arg in opts:

        if opt == '-h':
            print (sys.argv[0]," -b <broker> -p <port> -t <topic> -v \
<verbose True>, -c <clear retained True>," )
            sys.exit()
        elif opt == "-b":
            inputs["broker"] = str(arg)
        elif opt == "-u":
            inputs["USERNAME"] = str(arg)
        elif opt == "-P":
            inputs["PASSWORD"] = str(arg)
        elif opt =="-t":
            inputs["topic"]=str(arg)
            
        elif opt =="-p":
         inputs["port"] = int(arg)
        elif opt == "-v":
            inputs["verbose"] =True
                
        elif opt == "-c":
            inputs["clear_retained"] =True

    return(inputs)





if __name__ == "__main__":
    import sys, getopt
    if len(sys.argv)>=2:
        inputs=get_input(sys.argv[1:])

verbose=inputs["verbose"]

if inputs["topic"]=="":
    print("Topic required")
    sys.exit()
print("verbose is ",verbose)
print("Clear retained messages  is ",inputs["clear_retained"])

print("Creating client  with clean session set to ",CLEAN_SESSION)
Initialise_client_object()#create object flags
client= Initialise_clients(cname)

if inputs["username"]!="": #set username/password
    client.username_pw_set(username=inputs["username"],password=inputs["password"])

print("connecting to broker ",inputs["broker"],"on port ",inputs["port"],\
      " topic",inputs["topic"])
try:
    res=client.connect(inputs["broker"],inputs["port"])           #establish connection
except:
    print("can't connect to broker",inputs["broker"])
    sys.exit()

client.loop_start()

while not client.connected_flag and not client.bad_connection_flag:
    time.sleep(.25)
if client.bad_connection_flag:
    print("connection failure to broker ",inputs["broker"])
    client.loop_stop()
    sys.exit()
    
client.subscribe(inputs["topic"])
sleep_count=0
while not client.suback_flag: #wait for subscribe to be acknowledged
    time.sleep(.25)
    if sleep_count>40: #give up
        print("Subscribe failure quitting")
        client.loop_stop()
        sys.exit()
    sleep_count+=1
delay=10   
print("checking wait for ",delay," seconds")
time.sleep(delay)#wait for messages that indicate retianed message
if len(retained_topics)>0:
    print("Found these topics with possible retained messages")
    for t in retained_topics:
        print("topic =",t[0],"  Message= ",t[1])
else:
    print("No topics with retained messages found")
    
if inputs["clear_retained"]:
    if len(retained_topics)>0:
        verbose=False
        clear_retained(retained_topics)
time.sleep(2)
client.loop_stop()
client.disconnect()
print("disconnecting")
print("Ending")


