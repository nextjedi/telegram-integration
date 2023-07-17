import asyncio
import calendar
import requests
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
import requests
import pyotp
from telethon import TelegramClient,events
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
from telethon.tl import functions, types
import datetime
api_id = "23626680"
api_hash = "1439cfbf90f01a34ac35a507bdf3052d"
ip = "http://13.233.83.163:8080/"
client = TelegramClient('session_name', api_id, api_hash)
ipport = "http://localhost:8080"
# ipport = "http://13.233.83.163:8080/"

def login_in_zerodha(api_key, api_secret, user_id, user_pwd, totp_key):
    driver = uc.Chrome()
    print("going to login")
    driver.get(f'https://kite.trade/connect/login?api_key={api_key}&v=3')
    login_id = WebDriverWait(driver, 10).until(
        lambda x: x.find_element(by=By.XPATH, value='//*[@id="userid"]'))
    login_id.send_keys(user_id)

    pwd = WebDriverWait(driver, 10).until(
        lambda x: x.find_element(by=By.XPATH, value='//*[@id="password"]'))
    pwd.send_keys(user_pwd)

    submit = WebDriverWait(driver, 10).until(lambda x: x.find_element(
        by=By.XPATH,
        value='//*[@id="container"]/div/div/div[2]/form/div[4]/button'))
    submit.click()

    time.sleep(1)

    totp = WebDriverWait(driver, 10).until(lambda x: x.find_element(
        by=By.XPATH,
        value='/html/body/div[1]/div/div[2]/div[1]/div[2]/div/div[2]/form/div[1]/input'))
    authkey = pyotp.TOTP(totp_key)
    totp.send_keys(authkey.now())

    # continue_btn = WebDriverWait(driver, 10).until(lambda x: x.find_element(
    #     by=By.XPATH,
    #     value='//*[@id="container"]/div/div/div[2]/form/div[3]/button'))
    # continue_btn.click()

    time.sleep(5)

    url = driver.current_url
    initial_token = url.split('request_token=')[1]
    request_token = initial_token.split('&')[0]

    driver.close()
    print("logged in successfully going to call api")
    kite = KiteConnect(api_key=api_key)
    #print(request_token)
    res =requests.post(url=ip+"toke",data=request_token)
    print(res.status_code)
    requests.post(url=ipport+"/toke",data=request_token)



client.start()
async def handleMessages(m):
    # print(m.text)
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

@client.on(events.NewMessage(chats="@Nextjedi_algo_bot"))
async def getToken(event):
    print(event.message.message)
    print(event.message.message)
    if event.message.message.lower() == "token":
        login_in_zerodha('2himf7a1ff5edpjy', '87mebxtvu3226igmjnkjfjfcrgiphfxb',
                               'LU2942', 'Ap@240392',
                               'KZHIZCXRM5OL3XJUFL7EAPJQOJ6H5HH2')
    # sent token api

# get message from bank nifty
@client.on(events.NewMessage(chats=1752927494))
async def trade(event):
    print(event.message.text)
    await handleMessages(event.message)

# # get message from BTST
# @client.on(events.NewMessage(chats=1752927494))
# async def trade(event):
#     # call another method for btst
#     handleMessages(event.message)

async def main():
    channel = await client.get_entity(PeerChannel(1752927494))
    messages = await client.get_messages(channel, limit= 300) #pass your own args
    d1 = datetime.datetime(2023, 7,14 )
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
    count =0
    for m in playmsg:
        count =await handleMessages(m)
        

loop = asyncio.get_event_loop()
loop.run_until_complete(main())



# client.run_until_disconnected()