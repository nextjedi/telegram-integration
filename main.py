from telethon import TelegramClient, events, sync
from telethon.tl.types import PeerUser, PeerChat, PeerChannel
# These example values won't work. You must get your own api_id and
# api_hash from https://my.telegram.org, under API Development.
api_id = "23626680"
api_hash = "1439cfbf90f01a34ac35a507bdf3052d"

client = TelegramClient('session_name', api_id, api_hash)
client.start()

print(client.get_me().stringify())
channel = client.get_entity(PeerChannel(1752927494))

for dialog in client.iter_dialogs():
    print(dialog)

# client.send_message('username', 'Hello! Talking to you from Telethon')
# client.send_file('username', '/home/myself/Pictures/holidays.jpg')
from telethon.tl.types import InputPeerChat
# client.download_profile_photo('me')
# channel = await client.get_entity('1752927494')
messages = client.get_messages(channel.username,limit=20)
for m in messages:
    print(m.text)
len(messages)

@client.on(events.NewMessage(pattern='(?i)hi|hello'))
async def handler(event):
    await event.respond('Hey!')

