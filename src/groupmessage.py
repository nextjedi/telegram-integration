import asyncio
import calendar
import requests
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
import requests
import pyotp
from telethon import TelegramClient, events
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
from telethon.tl import functions, types
import datetime
import json
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
api_id = "23626680"
api_hash = "1439cfbf90f01a34ac35a507bdf3052d"
# ip = "https://tip-based-trading.azurewebsites.net/"
client = TelegramClient('session_name', api_id, api_hash)
ip = "http://localhost:80/"
btst = -1001552501322
daytrade = -1001752927494

client.start()


async def handleMessages(m, group):
    # print(m.text)
    trigger = 0
    today = datetime.date.today()
    date = today
    thursday = today + datetime.timedelta((3 - today.weekday()) % 7)
    tuesday = today + datetime.timedelta((1 - today.weekday()) % 7)
    instrument = "BANKNIFTY"
    fin = "FINNIFTY"
    t = m.text
    flag = False
    t = t.upper()
    pe = "PE" in t
    ce = "CE" in t
    porc = pe or ce
    instrumentType = ""
    # todo improve this fucking method
    if "ABOVE" in t and porc:
        t = t.replace("\n", " ")
        t = t.replace("-", " ")
        if fin in t:
            instrument = fin
            date = tuesday
        else:
            date = thursday
        # instrument+=str(date.day)+calendar.month_abbr[date.month].upper()

        if pe:
            instrumentType = "PE"
            strike = t.split("PE")[0].strip()
        else:
            instrumentType = "CE"
            strike = t.split("CE")[0].strip()

        t = t.split(" ")
        inFlag = False
        for n in t:
            if n == "ABOVE":
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
            "name": instrument,
            "strike": strike,
            # "expiry":str(date),
            "instrumentType": instrumentType
        }, "price": trigger,
            "stopLoss": trigger - 100,
            "target": trigger + 100,
            "type": group}
        print(data)
        # res = requests.post(url=ip + "tip", json=data)
        # print(res.status_code)
        await send_message_forward(group, data)
        # amit= await client.get_entity("@amitt0005")
        # robin= await client.get_entity("+917022557231")
        # reset


@client.on(events.NewMessage(chats="@Nextjedi_algo_bot"))
async def getToken(event):
    print(event.message.message)
    await send_message_forward("bot", event.message.message)
    # sent token api


async def send_message_forward(group, text):
    # try:
    amit = await client.get_entity("@ImRajAmit")
    robin = await client.get_entity("@robinpd26")
    nishu = await client.get_entity("@Aapainashergil")
    await client.send_message(entity=nishu, message=str(group + " ->" + text))
    await client.send_message(entity=robin, message=str(group + " ->" + text))
    await client.send_message(entity=amit, message=str(group + " ->" + text))
    # except:
    #     print("something went wrongdd")


# get message from bank nifty
@client.on(events.NewMessage(chats=daytrade))
async def trade(event):
    print(event.message.text)
    await handleMessages(event.message, "DAY")


# get message from BTST
@client.on(events.NewMessage(chats=-btst))
async def trade(event):
    # call another method for btst
    await handleMessages(event.message, "BTST")


async def main():
    print("here")
    channel = await client.get_entity(PeerChannel(daytrade))
    messages = await client.get_messages(channel, limit=500)  # pass your own args
    d1 = datetime.datetime(2024, 5, 24)
    # then if you want to get all the messages text
    playmsg = []
    for x in messages:
        if x.date.date() == d1.date():
            print(x.date)
            print(x.message)  # return message.text
            playmsg.append(x)

    def dt(e):
        return e['date']

    # playmsg.sort(key=dt)
    playmsg.reverse()
    count = 0
    for m in playmsg:
        count = await handleMessages(m, "DAY")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())


client.run_until_disconnected()
