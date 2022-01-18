#!/usr/bin/env python3

# LIONTRON LX Smart BMS 12,8V 100Ah - bought 2021
# Get Values from BMS and print as JSON
#
# Issues:
# Sometimes the connections does not work "connect error: Function not implemented (38)" : dont know why
# Sometimes there are no values "Characteristic value was written successfully" : dont know why
# Sometimes the connections does not work without any error : there might be another client connected
# "Device or resource busy" : there might be still an open connection on the client, restart your bluetooth if you can't find it

import argparse
import pexpect
import time
import json

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

# Run gatttool interactively.
child = pexpect.spawn("gatttool -I -b {0}".format(args.device))

# Connect to the device
for attempt in range(10):
    try:
        if args.v: print("BMS connect (Try:", attempt+1, ")")
        child.sendline("connect")
        child.expect("Connection successful", timeout=1)
    except pexpect.TIMEOUT:
        if args.v==2: print(child.before)
        continue
    else:
        if args.v: print("BMS connection successful")
        break
else:
    if args.v: print ("BMS Connect timeout! Exit")
    child.sendline("exit")
    print ("{}")
    exit()    

# Request data until data is recieved or max attempt is reached
for attempt in range(10):
    try:
        resp=b''
        if args.v: print("BMS requesting data (Try:", attempt+1, ")")
        child.sendline("char-write-req 0x0015 dda50300fffd77")
        child.expect("Notification handle = 0x0011 value: ", timeout=1)
        child.expect("\r\n", timeout=0)
        if args.v: print("BMS received data")
        if args.v==2: print("BMS answering 1: ", child.before)
        resp+=child.before
        child.expect("Notification handle = 0x0011 value: ", timeout=1)
        child.expect("\r\n", timeout=0)
        if args.v==2: print("BMS answering 2: ", child.before)
        resp+=child.before
    except pexpect.TIMEOUT:
        continue
    else:
        break
else:
    resp=b''
    if args.v: print ("BMS Answering timeout!")
    if args.v==2: print(child.before)

# Close connection
if args.v: print("BMS disconnecting")
child.sendline("disconnect")
child.sendline("exit")

# Build JSON
#BMS answering 1:  b'dd 03 00 1b 05 28 00 00 1b b2 2a ef 00 02 29 0a 00 00 00 00 '
#BMS answering 2:  b'00 00 25 41 03 04 02 0b 74 0b 6b fc 39 77 '
#BMS answer: dd03001b052800001bb22aef0002290a00000000000025410304020b740b6bfc3977
rawdat={}
resp = resp[:-1]
response=bytearray.fromhex(resp.decode())
if args.v: print("BMS answer:", response.hex())
if (response.endswith(b'w')) and (response.startswith(b'\xdd\x03')):
    response=response[4:]
    rawdat['Vmain']=int.from_bytes(response[0:2], byteorder = 'big',signed=True)/100.0 #total voltage [V]
    rawdat['Imain']=int.from_bytes(response[2:4], byteorder = 'big',signed=True)/100.0 #current [A]
    rawdat['RemainCap']=int.from_bytes(response[4:6], byteorder = 'big',signed=True)/100.0 #remaining capacity [Ah]
    rawdat['NominalCap']=int.from_bytes(response[6:8], byteorder = 'big',signed=True)/100.0 #nominal capacity [Ah]
    rawdat['NumberCycles']=int.from_bytes(response[8:10], byteorder = 'big',signed=True) #number of cycles
    rawdat['ProtectState']=int.from_bytes(response[16:18],byteorder = 'big',signed=False) #protection state
    rawdat['ProtectStateBin']=format(rawdat['ProtectState'], '016b') #protection state binary
    rawdat['SoC']=int.from_bytes(response[19:20],byteorder = 'big',signed=False) #remaining capacity [%]

    if (rawdat['ProtectStateBin'][0:13]) == '0000000000000':
        rawdat['ProtectStateText']="ok";
    if (rawdat['ProtectStateBin'][0]) == "1":
        rawdat['ProtectStateText']="CellBlockOverVolt";
    if (rawdat['ProtectStateBin'][1]) == "1":
        rawdat['ProtectStateText']="CellBlockUnderVol";
    if (rawdat['ProtectStateBin'][2]) == "1":
        rawdat['ProtectStateText']="BatteryOverVol";
    if (rawdat['ProtectStateBin'][3]) == "1":
        rawdat['ProtectStateText']="BatteryUnderVol";
    if (rawdat['ProtectStateBin'][4]) == "1":
        rawdat['ProtectStateText']="ChargingOverTemp";
    if (rawdat['ProtectStateBin'][5]) == "1":
        rawdat['ProtectStateText']="ChargingLowTemp";
    if (rawdat['ProtectStateBin'][6]) == "1":
        rawdat['ProtectStateText']="DischargingOverTemp";
    if (rawdat['ProtectStateBin'][7]) == "1":
        rawdat['ProtectStateText']="DischargingLowTemp";
    if (rawdat['ProtectStateBin'][8]) == "1":
        rawdat['ProtectStateText']="ChargingOverCurrent";
    if (rawdat['ProtectStateBin'][9]) == "1":
        rawdat['ProtectStateText']="DischargingOverCurrent"; 
    if (rawdat['ProtectStateBin'][10]) == "1":
        rawdat['ProtectStateText']="ShortCircuit";
    if (rawdat['ProtectStateBin'][11]) == "1":
        rawdat['ProtectStateText']="ForeEndICError";
    if (rawdat['ProtectStateBin'][12]) == "1":
        rawdat['ProtectStateText']="MOSSoftwareLockIn";

# Print JSON
print (json.dumps(rawdat, indent=1, sort_keys=False))
