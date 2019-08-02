import asyncio
import bleak
import logging
import time
import random

logger = logging.getLogger("main")

SERVICE_ID = '49535343-fe7d-4ae5-8fa9-9fafd205e455'
WRITE_CHAR = '49535343-8841-43f4-a8d4-ecbe34729bb3'
#WRITE_CHAR = '49535343-aca3-481c-91ec-d85e28a60318'
NOTIFY_CHAR = '49535343-1e4d-4bd9-ba61-23c647249616'
HELLO_MSG = b'\x00\x05HELLO\x00'

async def select_device():
    devices = await bleak.discover()
    index = 0
    devs = {}
    for dev in devices:
        index += 1
        if dev.name == "TimeBox-mini-light":
            return dev
    for dev in devices:
        print(entry)
    selected = input("Device: ")
    if selected == '':
        return None
    dev_index = int(selected)
    return devices[dev_index]

def encode_msg(msg):
    checksum = 0
    for byte in msg:
        checksum += byte
    msg_with_checksum = msg + bytes((checksum % 256, checksum // 256))

    encoded = b'\x01'
    for byte in msg_with_checksum:
        if byte >= 1 and byte <= 3:
            encoded += bytes((3, byte + 3,))
        else:
            encoded += bytes((byte, ))
    encoded += b'\x02'
    print("encoded size:", len(encoded))
    print("encoded:", encoded)
    return encoded

def decode_msg(msg):
    if len(msg) < 5:
        return msg
    if msg[0] != 1 or msg[-1] != 2:
        return msg
    msg = msg[1:-1]
    decoded = b''
    escaping = False
    for byte in msg:
        if escaping:
            decoded += bytes((byte - 3, ))
            escaping = False
        elif byte == 3:
            escaping = True
        else:
            decoded += bytes((byte, ))

    checksum = decoded[-1] * 256 + decoded[-2]
    actual_checksum = 0
    for byte in decoded[:-2]:
        actual_checksum += byte
    if checksum == actual_checksum:
        logger.info("CHECKSUM OK")
    else:
        logger.warning("CHECKSUM ERR: %d != %d", checksum, actual_checksum)
    return decoded[:-2]

def notify_handler(char_uuid, data):
    logger.info("Got notification from %s: %r", char_uuid, data)
    if bytes(data) == HELLO_MSG:
        print("Got HELLO message")
    else:
        print("Got message:", end=' ')
        decoded = decode_msg(data)
        dump_byte_array(decoded)

def dump_byte_array(data):
    for byte in data:
        print("%02x" % byte, end=' ')
    print()

def gen_random_img(length):
    result = b''
    for i in range(length):
        result += bytes((random.randint(4, 255),))
    print(result)
    return result

def encode_cmd(cmd):
    cmd_len = len(cmd) + 2 # with the length
    return bytes((cmd_len % 256, cmd_len // 256)) + cmd

async def run(loop):
    dev = await select_device()
    if dev is None:
        return
    print("Selected: %s" % dev)

    client = bleak.BleakClient(dev.address, loop)
    while True:
        try:
            connected = await client.connect()
            if connected:
                break
        except:
            print("Connecting...")
        time.sleep(1)

    for service in client.services:
        if service.uuid != SERVICE_ID:
            continue
        logger.info("Service: %s %s", service.uuid, service.description)
        for char in service.characteristics:
            logger.info("\tCharacter: %s %s %s", char.uuid, char.description, char.properties)
            if 'read' in char.properties:
                value = bytes(await client.read_gatt_char(char.uuid))
                logger.info("\t\tcurrent value: %s", value)
            if 'notify' in char.properties and char.uuid == NOTIFY_CHAR:
                await client.start_notify(char.uuid, notify_handler)
                logger.info("Found 'notify' characteristic")
            if 'write' in char.properties and char.uuid == WRITE_CHAR:
                logger.info("Found 'write' characteristic")
            for desc in char.descriptors:
                value = await client.read_gatt_descriptor(desc.handle)
                logger.info("\t\tDescriptor: %s %s %s", desc.uuid, desc.handle, value)
    
    #await client.write_gatt_char(WRITE_CHAR, encode_msg(encode_cmd(b'\x44\x00\x0a\x0a\x04' + gen_random_img(116))), response=True) #b'\xbd\x00\x44\x00\x0a\x0a\x04' + gen_random_img()))
    #await asyncio.sleep(3)
    await client.write_gatt_char(WRITE_CHAR, encode_msg(encode_cmd(b'\x44\x00\x0a\x0a\x04' + gen_random_img(50))), response=True) #b'\xbd\x00\x44\x00\x0a\x0a\x04' + gen_random_img()))
    await client.write_gatt_char(WRITE_CHAR, encode_msg(encode_cmd(b'\x44\x00\x0a\x0a\x04' + gen_random_img(50))), response=True) #b'\xbd\x00\x44\x00\x0a\x0a\x04' + gen_random_img()))
    await asyncio.sleep(3)

        

#logging.basicConfig(level=logging.INFO)    

loop = asyncio.get_event_loop()
loop.run_until_complete(run(loop))
