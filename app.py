import socket
import struct
import io
import time

from PIL import Image, ImageGrab, ImageOps
from cursor_overlay import CursorOverlay

#===============================================================================

PHONE_IS_CLIENT = False

HOST_LAPTOP = '192.168.1.153'
HOST_PHONE1 = '192.168.200.7'
HOST_PHONE2 = '192.168.1.73'

PORT = 5000

outputWidth1 = 1560
outputWidth2 = 1600
outputHeight =  720

cursor_overlay = CursorOverlay()

#===============================================================================

def listenForPhone(port):

    socket_io = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    socket_io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    socket_io.bind(("0.0.0.0", port))

    socket_io.listen(1)

    print(f"Waiting for Android client on port {port}...")

    return socket_io
#-------------------------------------------------------------------------------

def connectToPhone(ipAddress, port):

    print(f'connecting to {ipAddress}:{port}...')

    socket_io = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    socket_io.connect((ipAddress, port))

    print("connected")

    return socket_io
#-------------------------------------------------------------------------------

def getImage(outputWidth:int):
    ''' returns a buff of screen data '''

    # Capture PC screen
    eachImage = ImageGrab.grab().convert("RGB")

    cursor_overlay.overlay(eachImage)

    eachImage_scaled = ImageOps.contain(eachImage, (outputWidth // 2, outputHeight))

    output_image = Image.new("RGB", (outputWidth, outputHeight), "black")

    output_image.paste(eachImage_scaled, (0                , (outputHeight - eachImage_scaled.height) // 2))
    output_image.paste(eachImage_scaled, (outputWidth // 2, (outputHeight - eachImage_scaled.height) // 2))

    # Compress to JPEG
    buffer = io.BytesIO()
    output_image.save(buffer, format='JPEG', quality=75)

    return buffer.getvalue()
#-------------------------------------------------------------------------------

def loop_client(socket_io):

    print('initiating image capture loop...')

    try:

        while True:

            data = getImage(outputWidth1)

            socket_io.sendall(struct.pack('!I', len(data)) + data)

    except Exception as error:
        print("Streaming stopped:", error)

    finally:
        socket_io.close()

    print('image capture loop terminated')
#-------------------------------------------------------------------------------

def loop_server(socket_io):

    print('initiating image capture loop...')

    connection = None

    try:

        connection, address = socket_io.accept()

        print(f"Android client connected from {address[0]}:{address[1]}. Streaming...")

        while True:

            data = getImage(outputWidth2)

            # Send 4-byte big-endian length prefix + image data
            connection.sendall(struct.pack('!I', len(data)) + data)

    except Exception as error:
        print("Streaming stopped:", error)

    finally:

        if connection is not None:
            connection.close()

        socket_io.close()

    print('image capture loop terminated')
#-------------------------------------------------------------------------------

################################################################################

#region MAIN
if PHONE_IS_CLIENT:

    socket_io = listenForPhone(PORT)

    loop_server(socket_io)

else:

    socket_io = connectToPhone(HOST_PHONE1, PORT)

    loop_client(socket_io)

#endregion

################################################################################