#!/usr/bin/env python

from __future__ import print_function

from random import randint

import logging as log
import getopt, sys

import can
from can.bus import BusState


emu_ecu_can_id = 0x7e8

class globs:
    mil_on = 0
    confirmed_DTCs = 2
    dtcs = [0xc158, 0x0001]


def cansend(bus, msg: can.message):
    data =msg.data
    leng = len(data)
    if data[0] == 0:
        l = leng -1
        data[0] = l
    if len(data)!=8:    # padding
        data += b"\x00"*(8-len(data))
        # data += b"\xcc"*(8-len(data))
    bus.send(msg)

def service1(bus, msg :can.message):
    pid = msg.data[2]
    txmsg = can.Message(arbitration_id= emu_ecu_can_id,
          data=[0x00, 0x41, pid],
          is_extended_id=False)
    # print(hex(msg.arbitration_id),  msg.data, pid)
    if pid == 0x00:
        log.debug(">> Supported PIDs")
        # old: [0xBF, 0xDF, 0xB9, 0x91]
        if 0:
            p0= 0b10110000 # pids 1,3,4
            # p0 = 0b00001011
            p1, p2, p3 =0,0,0
            pids = [p0,p1,p2,p3]    # big endian
        pids = [0xBF, 0xDF, 0xB9, 0x91]
        txmsg.data[3:] = pids
        cansend(bus, txmsg)
    elif pid == 0x01:   # added by rundekugel
        log.debug(">> Status")
        txmsg.data[3:]= bytes([ (globs.mil_on <<7)|globs.confirmed_DTCs, 0,0,0,0])
        cansend(bus, txmsg)
    elif pid == 0x04:
        log.debug(">> Calculated engine load")
        txmsg.data[3:]= bytes([0x20])
        cansend(bus, txmsg)
    elif pid == 0x05:
        log.debug(">> Engine coolant temperature")
        txmsg.data[3:]= bytes([randint(88 + 40, 95 + 40)])
        cansend(bus, txmsg)
    elif pid == 0x0B:
        log.debug(">> Intake manifold absolute pressure")
        txmsg.data[3:]= bytes([randint(10, 40)])
        cansend(bus, txmsg)
    elif pid == 0x0C:
        log.debug(">> RPM")
        txmsg.data[3:]= bytes([ randint(18, 70), randint(0, 255)])
        cansend(bus, txmsg)
    elif pid == 0x0D:
        log.debug(">> Speed")
        txmsg.data[3:]= bytes([ randint(40, 60)])
        cansend(bus, txmsg)
    elif pid == 0x0F:
        log.debug(">> Intake air temperature")
        txmsg.data[3:]= bytes([ randint(60, 64)])
        cansend(bus, txmsg)
    elif pid == 0x10:
        log.debug(">> MAF air flow rate")
        txmsg.data[3:]= bytes([ 0x00, 0xFA])
        cansend(bus, txmsg)
    elif pid == 0x11:
        log.debug(">> Throttle position")
        txmsg.data[3:]= bytes([ randint(20, 60)])
        cansend(bus, txmsg)
    elif pid == 0x33:
        log.debug(">> Absolute Barometric Pressure")
        txmsg.data[3:]= bytes([ randint(20, 60)])
        cansend(bus, txmsg)
    else:
        log.warning("!!! Service 1, unknown code 0x%02x", pid)
        txmsg.data[3:]= bytes([0x02, 0x7f, 0x22, 0x31])
        cansend(bus, txmsg)

def service3(bus, msg :can.message): 
    """Show stored Diagnostic Trouble Codes (DTCs)"""
    dtc2bytes = [0xc1, 0x15, 0x00, 0x01]
    pid = msg.data[2]
    print(hex(msg.arbitration_id),  msg.data, pid)
    txmsg = can.Message(arbitration_id =emu_ecu_can_id,
        data=[0x00, 0x43, globs.confirmed_DTCs ] +dtc2bytes ,
        is_extended_id=False)    
    cansend(bus, txmsg)

def service7(bus, msg :can.message): 
    """Show pending Diagnostic Trouble Codes (detected during current or last driving cycle) """
    pid = msg.data[2]
    print(hex(msg.arbitration_id),  msg.data, pid)
    txmsg = can.Message(arbitration_id =emu_ecu_can_id,
        data=[0x00, 0x47, 0, 0,0,0,0],
        is_extended_id=False)    
    cansend(bus, txmsg)

def service10(bus, msg :can.message): 
    """send Permanent Diagnostic Trouble Codes (DTCs) (Cleared DTCs) """
    pid = msg.data[2]
    print(hex(msg.arbitration_id),  msg.data, pid)
    txmsg = can.Message(arbitration_id =emu_ecu_can_id,
        data=[0x00, 0x4a, 0, 0,0,0,0],
        is_extended_id=False)    
    cansend(bus, txmsg)


def service4(bus, msg :can.message):
    """ Clear DTCs"""
    log.debug(">> Clear DTCs")
    pid = msg.data[2]
    print(hex(msg.arbitration_id),  msg.data, pid)
    txmsg = can.Message(arbitration_id =emu_ecu_can_id,
        data=[0x00, 0x44, 0],
        is_extended_id=False)    
    cansend(bus, txmsg)
    globs.confirmed_DTCs = 0


def receive_all():

    bus = can.interface.Bus(interface='socketcan',channel='can0')
    #bus = can.interface.Bus(bustype='ixxat', channel=0, bitrate=250000)
    #bus = can.interface.Bus(bustype='vector', app_name='CANalyzer', channel=0, bitrate=250000)

    #bus.state = BusState.ACTIVE
    #bus.state = BusState.PASSIVE

    try:
        while True:
            msg = bus.recv(1)
            while 1:
                #print(msg)
                if msg is None:
                    break
                if msg.arbitration_id in [emu_ecu_can_id]:
                    log.warning("Other ECU is also responding!")
                    break
                if not msg.arbitration_id in [0x7df, 0x7e0]:
                    log.warning("Unknown ID %d (=0x%x) "%(msg.arbitration_id,msg.arbitration_id))
                    break
                if msg.data[1] == 0x01:
                    service1(bus, msg)
                    break
                if msg.data[1] == 0x03:
                    service3(bus, msg)
                    break
                if msg.data[1] == 0x04:
                    service4(bus, msg)
                    break
                if msg.data[1] == 0x07:
                    service7(bus, msg)
                    break
                if msg.data[1] == 0x0a:
                    service10(bus, msg)
                    break
                log.warning("Unknown service code 0x%02x", msg.data[1])
                break
    except KeyboardInterrupt:
        pass

def usage():
    # DOTO: implement
    pass

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "l:v", ["loglevel="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    loglevel = "INFO"

    for o, a in opts:
        if o == "-v":
            loglevel = "DEBUG"
        elif o in ("-l", "--loglevel"):
            loglevel = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    numeric_level = getattr(log, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    log.basicConfig(level=numeric_level)
    receive_all()

if __name__ == "__main__":
    main();
