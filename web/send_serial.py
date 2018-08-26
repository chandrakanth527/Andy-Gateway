#!/usr/bin/python
import serial
import sys
import struct

def C( num ):
    return struct.pack('!B',num)

ser = serial.Serial("/dev/ttyAMA0", 19200)

for arg in sys.argv[1:]:
    ser.write(C(int(arg)))
