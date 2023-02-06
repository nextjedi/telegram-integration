import asyncio
from telethon import TelegramClient,events
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
from telethon.tl import functions, types
import datetime
api_id = "23626680"
api_hash = "1439cfbf90f01a34ac35a507bdf3052d"
client = TelegramClient('session_name', api_id, api_hash)
client.start()

def handleMessages(m):
    print(m.text)
    trigger = 0
    sl =0
    target =0
    instrument = "Bank nifty"
    t = m.text
    # if sl
    if "Sl" in t:
        n=t.split("Sl")[1].split("\n")[0]
        sl = int(n)
    # if target
    if "TARGET" in t:
        n=t.split("TARGET")[1]
        target =[int(s.strip()) for s in n.split('-') if s.strip().isdigit()]

    # if trigger
    if "ABOVE" in t:
        n=t.split("Sl")[1].split("\n")[0]
        trigger = int(n)
    # instrument
    if "PE" in t or "CE" in t:
        n=t.split("PE")[0]
        instrument+=n+" PE"
        print("parse instrument")
    flag = trigger and target and sl and instrument
    if flag:
        print("send call")
        # reset

@client.on(events.NewMessage(chats="@Nextjedi_algo_bot"))
async def getToken(event):
    print(event.message.message)
    # sent token api

# get message from bank nifty
@client.on(events.NewMessage(chats=1752927494))
async def trade(event):
    handleMessages(event.message)

# get message from BTST
@client.on(events.NewMessage(chats=1752927494))
async def trade(event):
    # call another method for btst
    handleMessages(event.message)

async def main():
    channel = await client.get_entity(PeerChannel(1752927494))
    messages = await client.get_messages(channel, limit= 300) #pass your own args
    d1 = datetime.datetime(2023, 2, 3)
    #then if you want to get all the messages text
    playmsg=[]
    for x in messages:
        if(x.date.date()==d1.date()):
            print(x.date)
            print(x.message) #return message.text
            playmsg.append(x)
    def dt(e):
        return e['date']
    
    # playmsg.sort(key=dt)
    playmsg.reverse()
    for m in playmsg:
        handleMessages(m)
    
        


# loop = asyncio.get_event_loop()
# loop.run_until_complete(main())



client.run_until_disconnected()