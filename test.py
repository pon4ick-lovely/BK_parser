import asyncio
import aiohttp
import random
import json
import logging
import websockets
from form import *

conn = aiohttp.TCPConnector()
cs = aiohttp.ClientSession
cookie_jar = aiohttp.CookieJar(unsafe=True)

logger = logging.getLogger('websockets')
logger.setLevel(logging.INFO)
logger.addHandler(logging.FileHandler('log'))

def hshake_data(SESSION_ID):
    return ''.join([
    chr(HANDSHAKE_PROTOCOL),
    chr(HANDSHAKE_VERSION),
    chr(HANDSHAKE_CONNECTION_TYPE),
    chr(HANDSHAKE_CAPABILITIES_FLAG),
    TOPIC,
    ',',
    'S_',
    SESSION_ID,
    chr(0)])


sub_req = '\x16\x00OV_1_1_9\x01'
#sub_req = '\x16\x00OVInPlay_1_9\x01'

stamp = lambda: datetime.strftime(datetime.now(), '%Y%m%d%H%M%S%f')[:17]

async def websock(url, id, s, loop=None):
  url += str(random.random())[2:]
  async with websockets.connect(url,
                           loop=loop,
                           legacy_recv=True,
                           origin='https://mobile.bet365.com',
                           subprotocols=('zap-protocol-v1',),
                           extra_headers = {'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits'
                }) as ws:
    await ws.send(hshake_data(id))
    await ws.send(sub_req)
    msg = await ws.recv()
    while msg:
      if bounds(msg.encode()):
         await ws.send('\x16\x00%s\x01' % ','.join(list(subs())))
      msg = await ws.recv()
      for p in get_games():
         async with s.post(surl, params=p) as resp:
             print(await resp.text())
      with open('neurodump', 'a') as nd:
          nd.write(msg + '\n')
  await ws.close()

async def fetch(loop):
    async with cs(connector=conn, cookie_jar=cookie_jar) as s:
        async with s.get('https://mobile.bet365.com') as resp:
            html = await resp.text()
    host = re.search(r'wss:\/\/premws-pt\d{1,}.[a-z]{0,5}365[a-z]{0,6}\.\w{1,3}', html).group(0)
    id = re.search('[0-9A-Z]{38}', html).group(0)
    url = host + ':443' +'/zap/?uid='
    async with cs() as s:
        await websock(url, id, s, loop)

try:
    asyncio.run(fetch())
finally:
    with open('dump.json', 'w') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

loop = asyncio.get_event_loop()
loop.run_until_complete(fetch(loop))
loop.close()