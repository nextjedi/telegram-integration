from telethon.sync import TelegramClient, events
import requests
import configparser
import datetime
print("started")
# Read the API credentials from config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

api_id = 23626680
api_hash = "1439cfbf90f01a34ac35a507bdf3052d"
phone_number = +918867375708

# Read the API endpoint URL from config.ini file
api_url = "http://localhost:8080/"

# Create a TelegramClient instance
client = TelegramClient('session_name', api_id, api_hash)

# Event handler for new messages
@client.on(events.NewMessage(chats=1752927494))
async def handle_new_message(m):
    trigger = 0
    today = datetime.date.today()
    date =today
    thursday = today + datetime.timedelta( (3-today.weekday()) % 7 )
    tuesday = today + datetime.timedelta( (1-today.weekday()) % 7 )
    instrument = "BANKNIFTY"
    fin ="FINNIFTY"
    t = m.text
    flag = False
    t = t.upper()
    pe = "PE" in t
    ce = "CE" in t
    porc = pe or ce
    instrumentType = ""
    # todo improve this fucking method
    if "ABOVE" in t and porc :
        t = t.replace("\n"," ")
        t = t.replace("-"," ")
        if fin in t:
            instrument = fin
            date = tuesday
        else:
            date = thursday
        # instrument+=str(date.day)+calendar.month_abbr[date.month].upper()

        if pe:
            instrumentType = "PE"
            strike =t.split("PE")[0].strip()
        else:
            instrumentType = "CE"
            strike =t.split("CE")[0].strip()
        
        t = t.split(" ")
        inFlag = False
        for n in t:
            if n=="ABOVE":
                inFlag = True
                continue
            if inFlag:
                trigger = int(n)
                break
        trigger = int(trigger)
        # print(t)
        
        flag = True
    
    if flag:
        print("send call")
        data = {"instrument": {
            "name":instrument,
            "strike":strike,
            "expiry":str(date),
            "instrumentType":instrumentType
        },"price": trigger}
        print (data)
        requests.post(url=ipport+"/tip",json=data)
        requests.post(url=ip+"tip",json=data)
        # utsav= await client.get_entity("@Urstrulyutsav29")
        # amit= await client.get_entity("@amitt0005")
        # robin= await client.get_entity("+917022557231")
        # await client.send_message(entity=utsav,message=instrument +" "+ str(trigger))
        # await client.send_message(entity=amit,message=str(data))
        # await client.send_message(entity=robin,message=str(data))
        # reset

# Start the TelegramClient
with client:
    # Run the event loop
    client.run_until_disconnected()
