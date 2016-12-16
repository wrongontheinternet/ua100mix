#!/usr/bin/python ~devel/ua100mix/main.py

"""
ua100mix is just a try for creating a tool to control the Roland/Edirol UA-100,
an USB Audio & MIDI processing Unit.
"""

# define authorship information
__authors__ = ['Alberto "wishmehill" Azzalini']
__author__ = ','.join(__authors__)
__credits__ = []
__copyright__ = 'Copyright (c) 2014'
__license__ = 'GPL'

# maintanence information
__maintainer__ = 'Alberto Azzalini'
__email__ = 'alberto.azzalini@gmail.com'

# ********************************
# ***** DEBUG MODE CONTROL *******
# SET:
# 1: debug messages on stdout ON
# 0: debug messages on stdout OFF

DEBUG_MODE = 1

# ********************************
# ***** UA MODE CONTROL **********
#
# SET:
#      0: No UA-100 present, for test purposes on other machines
#      1: UA-100 present and working
# NOTE: Could (and will) be automatically set to 0 if no UA-100 is found.
#       The UA-100 discovery routine is based on ALSA - **** 
#       ******* TO DO *******
#       Let the discovery be usb id based?
#       Well: actually, ALSA discovery could be better, as we have more information about the device.
#       On the other hand, USB discovery will still need ALSA to get the device id to be used by portmidi.
#       So: we stick on ALSA discovery.

REAL_UA_MODE = 1

# ********************************

#       Just for the records:
#
#       install pyusb (first of all!)
#       
#       import sys
#       import usb.core as u
#       dev = u.find(idVendor=0x0582, idProduct=0x0000)
#       if dev is None:
#           print('sorry, no UA-100 found!')
#       else:
#       print('Well done! UA-100 is there to rock!')

import sys
import functools

import numpy as np

#
# **************************************************************************************
# **************************************************************************************
# **************************************************************************************
# **************************************************************************************
# NEW IN BRANCH: trying to implement something better than pyPortMidi,
#                which revealed itself to be broken and not maintained anymore.
#
#                From now on, we will rely on MIDO (https://github.com/olemb/mido)
#
#                MIDO itself CAN work with portmidi (which is default), but we move
#                to rtmidi, which looks better.
#
#                Time to rewrite A LOT of the code. I hope to manage it.
#                
#
# try:
#     import pyportmidi as pm
# except ImportError:
#     if (DEBUG_MODE):
#         print('*** Warning *** pypm not found - still trying with pyPortMidi  ***')
#     try:
#         import pypm as pm
#         
#     except ImportError:
#         if (DEBUG_MODE):
#             print('*** Warning *** neither pypm nor pyPortmidi found - Switching to testing mode (REAL_UA_MODE = 0) ***')
#         REAL_UA_MODE = 0
# if not (REAL_UA_MODE) and (DEBUG_MODE):
#     print('No portmidi implementation available! Running just in test mode')
# elif (REAL_UA_MODE) and (DEBUG_MODE):
#     print('Ok - We have a portmidi implementation. It is known as pm')

try:
    import mido
    import rtmidi
except ImportError:
    if (DEBUG_MODE):
        print('*** Warning *** mido and/or rtmidi not found - Switching to testing mode (REAL_UA_MODE = 0) ***')
        REAL_UA_MODE = 0
import PyQt4.uic
from PyQt4 import QtGui
# from PyQt4 import QtCore
# from types import MethodType
import signal
import time
import res.tools as tools

if (DEBUG_MODE):
    np.set_printoptions(formatter={'int': hex})

# Defining constants (taken from UA-100 documentation)
# and copying some useful documentation excerts

if (DEBUG_MODE):
    print('Reading some MANY constants...')

# just for convenience in code writing and editing
# in DEFINING CONSTANTS
if (True):
    # **************** this will and should be replaced with the real values obtained with sysex messages...
    CC_0127_DEFAULT = 64
    CC_PAN_MIDDLE = 64
    # I think 'in media stat virtus'


    #
    # The following comes from the UA-100 manual
    # ***************************************************************
    # *** 1. RECEIVE DATA
    # ***************************************************************
    # *************************
    # ** Channel Voice Messages
    # *************************
    #
    #         Status         |       2nd byte         |     3rd byte
    #          9nH           |          kkH           |       vvH
    #
    #
    # n = MIDI channel number: 0H-FH (ch.1-ch.16)
    # kk = note number : 00H-7FH (0-127)
    # NOTE: Used for pitch changes when using VT effect
    #
    # **********************************
    # Channel Voice Change STATUS Values
    # **********************************
    CV_MIC1_CH = 0x90
    CV_MIC2_CH = 0x91
    CV_WAVE1_CH = 0x92
    CV_WAVE2_CH = 0x93
    CV_SYSRET_CH = 0x94
    CV_SYSSUB_CH = 0x95
    CV_WAVEREC_CH = 0x9E
    CV_LINE_MASTER_CH = 0x9F
    #
    # ************************* 
    # ** Pitch Bend Change
    # *************************
    #
    #         Status         |       2nd byte         |     3rd byte
    #          EnH           |         llH            |       mmH
    #
    #
    # n = MIDI channel number: 0H-FH (ch.1-ch.16)
    # mm, ll = Pitch Bend value: 00 00H-40 00H-7F 7FH (-8192-0- +8191)
    # NOTE: Used for pitch changes when using VT effect
    #
    # *******************************
    # Pitch Bend Change STATUS Values
    # *******************************
    PB_MIC1_CH = 0xE0
    PB_MIC2_CH = 0xE1
    PB_WAVE1_CH = 0xE2
    PB_WAVE2_CH = 0xE3
    PB_SYSRET_CH = 0xE4
    PB_SYSSUB_CH = 0xe5
    PB_WAVEREC_CH = 0xEE
    PB_LINE_MASTER_CH = 0xEF
    #
    # *************************
    # ** Control Change
    # *************************
    #
    #         Status         |       2nd byte         |     3rd byte
    #          BnH                       mmH                   llH
    #
    # n = MIDI channel number: 0H-FH (ch. 1 to ch. 16:Refer to the correspondence chart)
    # mm = Mixer parameter number:Refer to the correspondence chart
    # ll = Mixer parameter value: 00H - 7FH (0 - 127)
    # ****************************
    # Control Change STATUS Values
    # ****************************
    CC_MIC1_CH = 0xB0
    CC_MIC2_CH = 0xB1
    CC_WAVE1_CH = 0xB2
    CC_WAVE2_CH = 0xB3
    CC_SYSRET_CH = 0xB4
    CC_SYSSUB_CH = 0xB5
    CC_WAVEREC_CH = 0xBE
    CC_LINE_MASTER_CH = 0xBF
    #
    # *********************************************************
    # * Correspondences Between MIDI Channels and Mixer Signals
    # *********************************************************
    #
    #      MIDI channel      |           Signal
    #           1Ch.         |  LINE (Line Mode), MIC1/GUITAR (Mic Mode), MIC1+MIC2 (MIC1+MIC2 Mode)
    #           2Ch.         |  MIC2 (Mic mode only)
    #           3Ch.         |  WAVE1
    #           4Ch.         |  WAVE2
    #           5Ch.         |  SysRET(system effect return Main bus)
    #           6Ch.         |  SysSUB(system effect return Sub bus)
    #           15Ch.        |  WAVE (Rec)
    #           16Ch.        |  LINE (Master)
    #
    # **********************************************************
    # * Mixer parameters and setting ranges
    # **********************************************************
    #
    # Parameter              |           mm           |             ll (setting range)
    # MIC/LINE Selector      |        21 (15H)        |     0: Mic Mode, 1: Line Mode, 2: MIC1+MIC2 Mode
    # Pan                    |        10 (0AH)        |     0 (left) - 64 (center) - 127 (right)
    # Send 1                 |        16 (10H)        |     0 - 127: Full/Compact Effect mode only
    # Send 2                 |        17 (11H)        |     0 - 127: Full/Compact Effect mode only
    # Mute                   |        18 (12H)        |     0 (OFF), 1 (ON: Mute)
    # Solo                   |        19 (13H)        |     0 (OFF), 1 (ON: Solo)
    # Sub Fader              |        20 (14H)        |     0 - 127
    # Main Fader             |         7 (07H)        |     0 - 127
    # Selector               |        22 (16H)        |     <Full/Compact Effect mode> 
    #                                                        0: MIC1 (Mic Mode), LINE (Line Mode), MIC1+MIC2 (MIC1+MIC2 Mode),
    #                                                        1: MIC2 (Mic Mode only), 
    #                                                        2: WAVE1,
    #                                                        3: WAVE2,
    #                                                        4 to 7: CH1 to 4,
    #                                                        8: SUB,
    #                                                        9: MAIN 
    #                                                       <VT Effect mode>
    #                                                        0: MIC1 (Mic Mode), LINE (Line Mode),
    #                                                        1: MIC2 (Mic Mode only),
    #                                                        2: WAVE1,
    #                                                        3: WAVE2,
    #                                                        4: VT_OUT,
    #                                                        5: MAIN
    # Effect Switch          |        23 (17H)        |      0 (OFF), 1 (ON: Apply effect)

    CC_MICLINESELECTOR_PAR = 21  # 0x15
    # CC_MICLINESELECTOR_RANGE = { 'Mic Mode': 0, 'Line Mode': 1, 'MIC1+MIC2 Mode': 2}
    CC_PAN_PAR = 10  # 0x0A - 0 - 64 - 127 (LEFT - CENTER - RIGHT)
    CC_SEND1_PAR = 16  # 0x10
    CC_SEND2_PAR = 17  # 0x11
    CC_MUTE_PAR = 18  # 0x12
    CC_SOLO_PAR = 19  # 0x13
    CC_SUB_FADER_PAR = 20  # 0x14
    CC_MAIN_FADER_PAR = 7  # 0x70
    CC_SELECTOR_PAR = 22  # 0x16
    CC_EFFECTSWITHC_PAR = 23  # 0x23

    # ******************************************************
    # * Correspondences Between Mixer Signals and Parameters
    # ******************************************************
    #
    #                   |  MIC1/LINE/ | MIC2 | WAVE1 | WAVE2 | SysRET |  SysSUB | WAVE  | LINE 
    #    Parameter      |  MIC1MIC2   | 2Ch. |  3Ch. |  4Ch. |   5Ch. |    6Ch. | 15Ch. | 16Ch.
    #                   |    1Ch.     |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    # MIC/LINE Selector |     O       |   -  |   -   |   -   |    -   |    -    |   -   |   -
    #    21 (15H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #       Pan         |     O       |   O  |   -   |   -   |    -   |    -    |   -   |   -
    #    10 (0AH)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #     Send 1        |     O       |   O  |   O   |   O   |    O   |    O    |   -   |   -
    #    16 (10H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #     Send 2        |     O       |   O  |   O   |   O   |    O   |    O    |   -   |   -
    #    17 (11H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #      Mute         |     O       |   O  |   O   |   O   |    -   |    -    |   -   |   -
    #    18 (12H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #      Solo         |     O       |   O  |   O   |   O   |    -   |    -    |   -   |   -
    #    19 (13H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #    Sub Fader      |     O       |   O  |   O   |   O   |    -   |    -    |   -   |   -
    #    20 (14H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #    Main Fader     |     O       |   O  |   O   |   O   |    -   |    -    |   O   |   O
    #     7 (07H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #     Selector      |     -       |   -  |   -   |   -   |    -   |    -    |   O   |   O
    #    22 (16H)       |             |      |       |       |        |         |       |
    #                   |             |      |       |       |        |         |       |
    #   Effect Switch   |     O       |   O  |   O   |   O   |    O   |    O    |   -   |   -
    #    23 (17H)       |             |      |       |       |        |         |       |
    # **********************************************************************************************
    #
    # Omitting the RPN MSB/LSB and Data Entry part. TODO in a near future, at least for documentation purposes
    # 
    # MIDI EXCLUSIVE
    # ********** I SHALL PUT SOME CONSTANTS FOR THE SYSEXs AND PASTE THE DOCUMENTATION AS WELL **********
    # LET'S START
    #
    # let's set the sleep time between SYSEXex (in seconds)
    SLEEP_TIME = 0.05

    # This should be common for all SYSEXes
    UA_SYSEX_ID = [0x41, 0x10, 0x00, 0x11]

    # Request data 1 RQ1 (0x11)
    RQ1_STATUS = [0xF0]
    RQ1_COMMAND = [0x11]

    # Data set 1 (DT1)
    DT1_STATUS = [0xF0]
    DT1_COMMAND = [0x12]

    # Address map (one last 0xnn is the actual parameter)

    # Mixer Parameters


    # UA-100 Control

    UA100_CONTROL = [0x00, 0x40, 0x00]

    # MODE
    UA100_MODE = [0x00]
    UA100_MODE_SIZE = [0x00, 0x00, 0x00, 0x01]
    # UA100_MODE_DATARANGE = range(0x01,10)
    # 1: PC Mode(VT Effect Mode)
    # 3: PC Mode(Compact Effect Mode)
    # 4: PC Mode(Full Effect Mode)
    # 5: VT Mode
    # 6: Vocal Mode
    # 7: Guitar Mode
    # 8: GAME Mode
    # 9: BYPASS Mode
    # * Send only (sent when the Effect Type Selector is switched or when a requested by Data Request 1)

    # COPYRIGHT
    COPYRIGHT = [0x01]
    COPYRIGHT_SIZE = [0x00, 0x00, 0x00, 0x01]

    # Mixer Input Control
    MIXER_INPUT_CONTROL = [0x00, 0x40, 0x10]

    MIXER_INPUT_MODE = [0x00]
    MIXER_INPUT_MODE_SIZE = [0x00, 0x00, 0x00, 0x01]
    MIXER_INPUT_MODE_VALUES = {0x00: 'Mic Mode', 0x01: 'Line Mode', 0x02: 'MIC1 + MIC2 Mode'}

    MIXER_INPUT_PAN1 = [0x01]
    MIXER_INPUT_PAN1_SIZE = [0x00, 0x00, 0x00, 0x01]
    MIXER_INPUT_PAN2 = [0x02]
    MIXER_INPUT_PAN2_SIZE = [0x00, 0x00, 0x00, 0x01]
    MIXER_INPUT_MONITOR_SW = [0x03]
    MIXER_INPUT_MONITOR_SW_SIZE = [0x00, 0x00, 0x00, 0x01]

    # ...
    MIC1_FADER = [0x00, 0x40, 0x11, 0x05]
    MIC1_FADER_SIZE = [0x00, 0x00, 0x00, 0x01]
    MIC2_FADER = [0x00, 0x40, 0x12, 0x05]
    MIC2_FADER_SIZE = [0x00, 0x00, 0x00, 0x01]
    WAVE1_FADER = [0x00, 0x40, 0x13, 0x05]
    WAVE1_FADER_SIZE = [0x00, 0x00, 0x00, 0x01]
    # WAVE1_FADER_RANGErange(0x00, 0x80)
    WAVE2_FADER = [0x00, 0x40, 0x14, 0x05]
    WAVE2_FADER_SIZE = [0x00, 0x00, 0x00, 0x01]
    # ...

    EFFECT_PARAMETERS = [0x00, 0x40, 0x01]

    MIXER_EFFECT_CONTROL = [0x00, 0x40, 0x40]

    MIXER_EFFECT_MODE = [0x00]
    MIXER_EFFECT_MODE_SIZE = [0x00, 0x00, 0x00, 0x01]
    MIXER_EFFECT_MODE_PAR = ({
        # 0x01: 'VT Effect Mode',
        0x03: 'Compact Effect Mode',
        0x04: 'Full Effect Mode'}
    )

    # Mixer Output Control
    MIXER_OUTPUT_CONTROL = [0x00, 0x40, 0x50]
    #
    MASTER_SELECT_MIXERMODE = ({0x00: 'LINE/MIC1/MIC1+MIC2',
                                0x01: 'MIC2',
                                0x02: 'WAVE1',
                                0x03: 'WAVE2',
                                0x04: 'CH1',
                                0x05: 'CH2',
                                0x06: 'CH3',
                                0x07: 'CH4',
                                0x08: 'SUB',
                                0x09: 'MAIN',
                                0x0A: 'WAVE(REC)OUT'})
    MASTER_SELECT_VTMIXERMODE = ({0x00: 'LINE/MIC1',
                                  0x01: 'MIC2',
                                  0x02: 'WAVE1',
                                  0x03: 'WAVE2',
                                  0x04: 'VT_OUT',
                                  0x05: 'MAIN',
                                  0x06: 'WAVE(REC)OUT'})
    WAVE_SELECT_MIXERMODE = ({0x00: 'LINE/MIC1/MIC1+MIC2',
                              0x01: 'MIC2',
                              0x02: 'WAVE1',
                              0x03: 'WAVE2',
                              0x04: 'CH1',
                              0x05: 'CH2',
                              0x06: 'CH3',
                              0x07: 'CH4',
                              0x08: 'SUB',
                              0x09: 'MAIN'})
    WAVE_SELECT_VTMIXERMODE = ({0x00: 'LINE/MIC1',
                                0x01: 'MIC2',
                                0x02: 'WAVE1',
                                0x03: 'WAVE2',
                                0x04: 'VT_OUT',
                                0x05: 'MAIN'})

    # Mixer Output Mode:
    # 0: VT MIXER MODE
    # 1: MIXER MODE
    MIXER_OUTPUT_MODE = 1

    # ...
    MIXER_OUTPUT_MASTERLEVEL = [0x03]
    MIXER_OUTPUT_MASTERLEVEL_SIZE = [0x00, 0x00, 0x00, 0x01]
    # MIXER_OUTPUT_MASTERLEVEL_RANGE = range(0x00, 0x80)
    MIXER_OUTPUT_WAVEREC = [0x02]
    MIXER_OUTPUT_WAVEREC_SIZE = [0x00, 0x00, 0x00, 0x01]
    # ...


    PRESET_EFFECT_CONTROL = [0x00, 0x40, 0x60]

    # PARAMETER CONVERSION TABLES

    # Parameters 10 to 18 are numbered and named wrongly the manual: count starts back from 1 and the names are just copied.
    # The right list can be found on page 66.


    # *1 : Pre Delay Time
    # *2 : Delay Time 1
    # *3 : Delay Time 2
    # *4 : Delay Time 3
    # *5 : Delay Time 4
    # *6 : Rate 1
    # *7 : Rate 2
    # *8 : HF Damp
    # *9 : Cutoff Freq
    # *10 : EQ Freq
    # *11 : LPF
    # *12 : Manual
    # *13 : Azimuth
    # *14 : Accl
    # *15 : Bass Cut Freq
    # *16 : Reverb Time
    # *17 : Distance
    # *18 : Boost Freq

    # so Parameter 10 is actually the 1 on pages 76-77)

    # PRE DELAY TIME [ms] (1)
    # It is not a regular parameters as it has different steps. Must be built in steps...
    # PARAM_CONV_1 = tools.mergeRanges(range(0x00,0x33),tools.ulist(0,5,0.1,'ms'))
    # PARAM_CONV_1_B = tools.mergeRanges(range(0x33,0x3D),tools.ulist(5.5,10,0.5))
    # PARAM_CONV_1_C = tools.mergeRanges(range(0x3D,0x65),tools.ulist(11,50,1))
    # PARAM_CONV_1_D = tools.mergeRanges(range(0x65,0x7E),tools.ulist(52,100,2))
    # PARAM_CONV_1_E = {0x7E: '100', 0x7F: '100'}
    # PARAM_CONV_1.update(PARAM_CONV_1_B)
    # PARAM_CONV_1.update(PARAM_CONV_1_C)
    # PARAM_CONV_1.update(PARAM_CONV_1_D)
    # PARAM_CONV_1.update(PARAM_CONV_1_E)
    # to save CPU and time, I put THEM ALL already built...
    # Pre Delay Time (ms)
    PARAM_TYPE_1 = ({0: '0ms', 1: '0.1ms', 2: '0.2ms', 3: '0.3ms', 4: '0.4ms', 5: '0.5ms',
                     6: '0.6ms', 7: '0.7ms', 8: '0.8ms', 9: '0.9ms', 10: '1.0ms', 11: '1.1ms',
                     12: '1.2ms', 13: '1.3ms', 14: '1.4ms', 15: '1.5ms', 16: '1.6ms', 17: '1.7ms',
                     18: '1.8ms', 19: '1.9ms', 20: '2.0ms', 21: '2.1ms', 22: '2.2ms', 23: '2.3ms',
                     24: '2.4ms', 25: '2.5ms', 26: '2.6ms', 27: '2.7ms', 28: '2.8ms', 29: '2.9ms',
                     30: '3.0ms', 31: '3.1ms', 32: '3.2ms', 33: '3.3ms', 34: '3.4ms', 35: '3.5ms',
                     36: '3.6ms', 37: '3.7ms', 38: '3.8ms', 39: '3.9ms', 40: '4.0ms', 41: '4.1ms',
                     42: '4.2ms', 43: '4.3ms', 44: '4.4ms', 45: '4.5ms', 46: '4.6ms', 47: '4.7ms',
                     48: '4.8ms', 49: '4.9ms', 50: '5.0ms', 51: '5.5ms', 52: '6.0ms', 53: '6.5ms', 54: '7.0ms',
                     55: '7.5ms', 56: '8.0ms', 57: '8.5ms', 58: '9.0ms', 59: '9.5ms', 60: '10.0ms', 61: '11msms',
                     62: '12msms',
                     63: '13msms', 64: '14ms', 65: '15ms', 66: '16ms', 67: '17ms', 68: '18ms', 69: '19ms', 70: '20ms',
                     71: '21ms',
                     72: '22ms', 73: '23ms', 74: '24ms', 75: '25ms', 76: '26ms', 77: '27ms', 78: '28ms', 79: '29ms',
                     80: '30ms',
                     81: '31ms', 82: '32ms', 83: '33ms', 84: '34ms', 85: '35ms', 86: '36ms', 87: '37ms', 88: '38ms',
                     89: '39ms',
                     90: '40ms', 91: '41ms', 92: '42ms', 93: '43ms', 94: '44ms', 95: '45ms', 96: '46ms', 97: '47ms',
                     98: '48ms',
                     99: '49ms', 100: '50ms', 101: '52ms', 102: '54ms', 103: '56ms', 104: '58ms', 105: '60ms',
                     106: '62ms',
                     107: '64ms', 108: '66ms', 109: '68ms', 110: '70ms', 111: '72ms', 112: '74ms', 113: '76ms',
                     114: '78ms',
                     115: '80ms', 116: '82ms', 117: '84ms', 118: '86ms', 119: '88ms', 120: '90ms', 121: '92ms',
                     122: '94ms',
                     123: '96ms', 124: '98ms', 125: '100ms', 126: '100ms', 127: '100ms'})

    # Delay Time 2 (ms)
    PARAM_TYPE_2 = ({0: '200ms', 1: '205ms', 2: '210ms', 3: '215ms', 4: '220ms', 5: '225ms',
                    6: '230ms', 7: '235ms', 8: '240ms', 9: '245ms', 10: '250ms', 11: '255ms',
                    12: '260ms', 13: '265ms', 14: '270ms', 15: '275ms', 16: '280ms', 17: '285ms',
                    18: '290ms', 19: '295ms', 20: '300ms', 21: '305ms', 22: '310ms', 23: '315ms',
                    24: '320ms', 25: '325ms', 26: '330ms', 27: '335ms', 28: '340ms', 29: '345ms',
                    30: '350ms', 31: '355ms', 32: '360ms', 33: '365ms', 34: '370ms', 35: '375ms',
                    36: '380ms', 37: '385ms', 38: '390ms', 39: '395ms', 40: '400ms', 41: '405ms',
                    42: '410ms', 43: '415ms', 44: '420ms', 45: '425ms', 46: '430ms', 47: '435ms',
                    48: '440ms', 49: '445ms', 50: '450ms', 51: '455ms', 52: '460ms', 53: '465ms',
                    54: '470ms', 55: '475ms', 56: '480ms', 57: '485ms', 58: '490ms', 59: '495ms',
                    60: '500ms', 61: '505ms', 62: '510ms', 63: '515ms', 64: '520ms', 65: '525ms',
                    66: '530ms', 67: '535ms', 68: '540ms', 69: '545ms', 70: '550ms', 71: '560ms',
                    72: '570ms', 73: '580ms', 74: '590ms', 75: '600ms', 76: '610ms', 77: '620ms',
                    78: '630ms', 79: '640ms', 80: '650ms', 81: '660ms', 82: '670ms', 83: '680ms',
                    84: '690ms', 85: '700ms', 86: '710ms', 87: '720ms', 88: '730ms', 89: '740ms',
                    90: '750ms', 91: '760ms', 92: '770ms', 93: '780ms', 94: '790ms', 95: '800ms',
                    96: '810ms', 97: '820ms', 98: '830ms', 99: '840ms', 100: '850ms', 101: '860ms',
                    102: '870ms', 103: '880ms', 104: '890ms', 105: '900ms', 106: '910ms',
                    107: '920ms', 108: '930ms', 109: '940ms', 110: '950ms', 111: '960ms',
                    112: '970ms', 113: '980ms', 114: '990ms', 115: '1000ms'})

    # Delay Time 2 (ms)
    PARAM_TYPE_3 = ({0: '200ms', 1: '205ms', 2: '210ms', 3: '215ms', 4: '220ms', 5: '225ms',
                     6: '230ms', 7: '235ms', 8: '240ms', 9: '245ms', 10: '250ms', 11: '255ms',
                     12: '260ms', 13: '265ms', 14: '270ms', 15: '275ms', 16: '280ms', 17: '285ms',
                     18: '290ms', 19: '295ms', 20: '300ms', 21: '305ms', 22: '310ms', 23: '315ms',
                     24: '320ms', 25: '325ms', 26: '330ms', 27: '335ms', 28: '340ms', 29: '345ms',
                     30: '350ms', 31: '355ms', 32: '360ms', 33: '365ms', 34: '370ms', 35: '375ms',
                     36: '380ms', 37: '385ms', 38: '390ms', 39: '395ms', 40: '400ms', 41: '405ms',
                     42: '410ms', 43: '415ms', 44: '420ms', 45: '425ms', 46: '430ms', 47: '435ms',
                     48: '440ms', 49: '445ms', 50: '450ms', 51: '455ms', 52: '460ms', 53: '465ms',
                     54: '470ms', 55: '475ms', 56: '480ms', 57: '485ms', 58: '490ms', 59: '495ms',
                     60: '500ms', 61: '505ms', 62: '510ms', 63: '515ms', 64: '520ms', 65: '525ms',
                     66: '530ms', 67: '535ms', 68: '540ms', 69: '545ms', 70: '550ms', 71: '555ms',
                     72: '560ms', 73: '565ms', 74: '570ms', 75: '575ms', 76: '580ms', 77: '585ms',
                     78: '590ms', 79: '595ms', 80: '600ms', 81: '610ms', 82: '620ms', 83: '630ms',
                     84: '640ms', 85: '650ms', 86: '660ms', 87: '670ms', 88: '680ms', 89: '690ms',
                     90: '700ms', 91: '710ms', 92: '720ms', 93: '730ms', 94: '740ms', 95: '750ms',
                     96: '760ms', 97: '770ms', 98: '780ms', 99: '790ms', 100: '800ms', 101: '810ms',
                     102: '820ms', 103: '830ms', 104: '840ms', 105: '850ms', 106: '860ms',
                     107: '870ms', 108: '880ms', 109: '890ms', 110: '900ms', 111: '910ms',
                     112: '920ms', 113: '930ms', 114: '940ms', 115: '950ms', 116: '960ms',
                     117: '970ms', 118: '980ms', 119: '990ms', 120: '1000ms', 121: '1000',
                     122: '1000', 123: '1000', 124: '1000', 125: '1000', 126: '1000', 127: '1000'})



    # Delay Time 3 (ms)
    PARAM_TYPE_4 = ({0: '0ms', 1: '0.1ms', 2: '0.2ms', 3: '0.3ms', 4: '0.4ms', 5: '0.5ms', 6: '0.6ms',
                     7: '0.7ms', 8: '0.8ms', 9: '0.9ms', 10: '1.0ms', 11: '1.1ms', 12: '1.2ms',
                     13: '1.3ms', 14: '1.4ms', 15: '1.5ms', 16: '1.6ms', 17: '1.7ms', 18: '1.8ms',
                     19: '1.9ms', 20: '2.0ms', 21: '2.1ms', 22: '2.2ms', 23: '2.3ms', 24: '2.4ms',
                     25: '2.5ms', 26: '2.6ms', 27: '2.7ms', 28: '2.8ms', 29: '2.9ms', 30: '3.0ms',
                     31: '3.1ms', 32: '3.2ms', 33: '3.3ms', 34: '3.4ms', 35: '3.5ms', 36: '3.6ms',
                     37: '3.7ms', 38: '3.8ms', 39: '3.9ms', 40: '4.0ms', 41: '4.1ms', 42: '4.2ms',
                     43: '4.3ms', 44: '4.4ms', 45: '4.5ms', 46: '4.6ms', 47: '4.7ms', 48: '4.8ms',
                     49: '4.9ms', 50: '5.0ms', 51: '5.5ms', 52: '6.0ms', 53: '6.5ms', 54: '7.0ms',
                     55: '7.5ms', 56: '8.0ms', 57: '8.5ms', 58: '9.0ms', 59: '9.5ms', 60: '10.0ms',
                     61: '11ms', 62: '12ms', 63: '13ms', 64: '14ms', 65: '15ms', 66: '16ms', 67: '17ms',
                     68: '18ms', 69: '19ms', 70: '20ms', 71: '21ms', 72: '22ms', 73: '23ms', 74: '24ms',
                     75: '25ms', 76: '26ms', 77: '27ms', 78: '28ms', 79: '29ms', 80: '30ms', 81: '31ms',
                     82: '32ms', 83: '33ms', 84: '34ms', 85: '35ms', 86: '36ms', 87: '37ms', 88: '38ms',
                     89: '39ms', 90: '40ms', 91: '50ms', 92: '60ms', 93: '70ms', 94: '80ms', 95: '90ms',
                     96: '100ms', 97: '110ms', 98: '120ms', 99: '130ms', 100: '140ms', 101: '150ms',
                     102: '160ms', 103: '170ms', 104: '180ms', 105: '190ms', 106: '200ms', 107: '210ms',
                     108: '220ms', 109: '230ms', 110: '240ms', 111: '250ms', 112: '260ms', 113: '270ms',
                     114: '280ms', 115: '290ms', 116: '300ms', 117: '320ms', 118: '340ms', 119: '360ms',
                     120: '380ms', 121: '400ms', 122: '420ms', 123: '440ms', 124: '460ms', 125: '480ms',
                     126: '500ms', 127: '500ms'}
                    )
    # Some effects require a shorter version of *Delay Time 3*
    PARAM_TYPE_4_SHORT = ({0: '0ms', 1: '0.1ms', 2: '0.2ms', 3: '0.3ms', 4: '0.4ms', 5: '0.5ms', 6: '0.6ms',
                           7: '0.7ms', 8: '0.8ms', 9: '0.9ms', 10: '1.0ms', 11: '1.1ms', 12: '1.2ms',
                           13: '1.3ms', 14: '1.4ms', 15: '1.5ms', 16: '1.6ms', 17: '1.7ms', 18: '1.8ms',
                           19: '1.9ms', 20: '2.0ms', 21: '2.1ms', 22: '2.2ms', 23: '2.3ms', 24: '2.4ms',
                           25: '2.5ms', 26: '2.6ms', 27: '2.7ms', 28: '2.8ms', 29: '2.9ms', 30: '3.0ms',
                           31: '3.1ms', 32: '3.2ms', 33: '3.3ms', 34: '3.4ms', 35: '3.5ms', 36: '3.6ms',
                           37: '3.7ms', 38: '3.8ms', 39: '3.9ms', 40: '4.0ms', 41: '4.1ms', 42: '4.2ms',
                           43: '4.3ms', 44: '4.4ms', 45: '4.5ms', 46: '4.6ms', 47: '4.7ms', 48: '4.8ms',
                           49: '4.9ms', 50: '5.0ms', 51: '5.5ms', 52: '6.0ms', 53: '6.5ms', 54: '7.0ms',
                           55: '7.5ms', 56: '8.0ms', 57: '8.5ms', 58: '9.0ms', 59: '9.5ms', 60: '10.0ms',
                           61: '11ms', 62: '12ms', 63: '13ms', 64: '14ms', 65: '15ms', 66: '16ms', 67: '17ms',
                           68: '18ms', 69: '19ms', 70: '20ms', 71: '21ms', 72: '22ms', 73: '23ms', 74: '24ms',
                           75: '25ms', 76: '26ms', 77: '27ms', 78: '28ms', 79: '29ms', 80: '30ms', 81: '31ms',
                           82: '32ms', 83: '33ms', 84: '34ms', 85: '35ms', 86: '36ms', 87: '37ms', 88: '38ms',
                           89: '39ms', 90: '40ms', 91: '50ms', 92: '60ms', 93: '70ms', 94: '80ms', 95: '90ms',
                           96: '100ms', 97: '110ms', 98: '120ms', 99: '130ms', 100: '140ms', 101: '150ms',
                           102: '160ms', 103: '170ms', 104: '180ms', 105: '190ms', 106: '200ms', 107: '210ms',
                           108: '220ms', 109: '230ms', 110: '240ms', 111: '250ms', 112: '260ms', 113: '270ms',
                           114: '280ms', 115: '290ms', 116: '300ms', 117: '320ms', 118: '340ms', 119: '360ms'}
                          )

    # PARAM_TYPE_5 = tools.mergeRanges(range(0x00,0x80),tools.ulist(0,635,5,'ms'))
    # Delay Time 4
    PARAM_TYPE_5 = ({0: '0ms', 1: '5ms', 2: '10ms', 3: '15ms', 4: '20ms', 5: '25ms', 6: '30ms', 7: '35ms',
                     8: '40ms', 9: '45ms', 10: '50ms', 11: '55ms', 12: '60ms', 13: '65ms', 14: '70ms',
                     15: '75ms', 16: '80ms', 17: '85ms', 18: '90ms', 19: '95ms', 20: '100ms', 21: '105ms',
                     22: '110ms', 23: '115ms', 24: '120ms', 25: '125ms', 26: '130ms', 27: '135ms', 28: '140ms',
                     29: '145ms', 30: '150ms', 31: '155ms', 32: '160ms', 33: '165ms', 34: '170ms', 35: '175ms',
                     36: '180ms', 37: '185ms', 38: '190ms', 39: '195ms', 40: '200ms', 41: '205ms', 42: '210ms',
                     43: '215ms', 44: '220ms', 45: '225ms', 46: '230ms', 47: '235ms', 48: '240ms', 49: '245ms',
                     50: '250ms', 51: '255ms', 52: '260ms', 53: '265ms', 54: '270ms', 55: '275ms', 56: '280ms',
                     57: '285ms', 58: '290ms', 59: '295ms', 60: '300ms', 61: '305ms', 62: '310ms', 63: '315ms',
                     64: '320ms', 65: '325ms', 66: '330ms', 67: '335ms', 68: '340ms', 69: '345ms', 70: '350ms',
                     71: '355ms', 72: '360ms', 73: '365ms', 74: '370ms', 75: '375ms', 76: '380ms', 77: '385ms',
                     78: '390ms', 79: '395ms', 80: '400ms', 81: '405ms', 82: '410ms', 83: '415ms', 84: '420ms',
                     85: '425ms', 86: '430ms', 87: '435ms', 88: '440ms', 89: '445ms', 90: '450ms', 91: '455ms',
                     92: '460ms', 93: '465ms', 94: '470ms', 95: '475ms', 96: '480ms', 97: '485ms', 98: '490ms',
                     99: '495ms', 100: '500ms', 101: '505ms', 102: '510ms', 103: '515ms', 104: '520ms', 105: '525ms',
                     106: '530ms', 107: '535ms', 108: '540ms', 109: '545ms', 110: '550ms', 111: '555ms', 112: '560ms',
                     113: '565ms', 114: '570ms', 115: '575ms', 116: '580ms', 117: '585ms', 118: '590ms', 119: '595ms',
                     120: '600ms', 121: '605ms', 122: '610ms', 123: '615ms', 124: '620ms', 125: '625ms', 126: '630ms',
                     127: '635ms'})
    # Rate1 (Hz)
    PARAM_TYPE_6 = ({0: '0.05Hz', 1: '0.1Hz', 2: '0.15Hz', 3: '0.2Hz', 4: '0.25Hz', 5: '0.3Hz', 6: '0.35Hz',
                     7: '0.4Hz', 8: '0.45Hz', 9: '0.5Hz', 10: '0.55Hz', 11: '0.6Hz', 12: '0.65Hz', 13: '0.7Hz',
                     14: '0.75Hz', 15: '0.8Hz', 16: '0.85Hz', 17: '0.9Hz', 18: '0.95Hz', 19: '1.0Hz', 20: '1.05Hz',
                     21: '1.1Hz', 22: '1.15Hz', 23: '1.2Hz', 24: '1.25Hz', 25: '1.3Hz', 26: '1.35Hz', 27: '1.4Hz',
                     28: '1.45Hz', 29: '1.5Hz', 30: '1.55Hz', 31: '1.6Hz', 32: '1.65Hz', 33: '1.7Hz', 34: '1.75Hz',
                     35: '1.8Hz', 36: '1.85Hz', 37: '1.9Hz', 38: '1.95Hz', 39: '2.0Hz', 40: '2.05Hz', 41: '2.1Hz',
                     42: '2.15Hz', 43: '2.2Hz', 44: '2.25Hz', 45: '2.3Hz', 46: '2.35Hz', 47: '2.4Hz', 48: '2.45Hz',
                     49: '2.5Hz', 50: '2.55Hz', 51: '2.6Hz', 52: '2.65Hz', 53: '2.7Hz', 54: '2.75Hz', 55: '2.8Hz',
                     56: '2.85Hz', 57: '2.9Hz', 58: '2.95Hz', 59: '3.0Hz', 60: '3.05Hz', 61: '3.1Hz', 62: '3.15Hz',
                     63: '3.2Hz', 64: '3.25Hz', 65: '3.3Hz', 66: '3.35Hz', 67: '3.4Hz', 68: '3.45Hz', 69: '3.5Hz',
                     70: '3.55Hz', 71: '3.6Hz', 72: '3.65Hz', 73: '3.7Hz', 74: '3.75Hz', 75: '3.8Hz', 76: '3.85Hz',
                     77: '3.9Hz', 78: '3.95Hz', 79: '4.0Hz', 80: '4.05Hz', 81: '4.1Hz', 82: '4.15Hz', 83: '4.2Hz',
                     84: '4.25Hz', 85: '4.3Hz', 86: '4.35Hz', 87: '4.4Hz', 88: '4.45Hz', 89: '4.5Hz', 90: '4.55Hz',
                     91: '4.6Hz', 92: '4.65Hz', 93: '4.7Hz', 94: '4.75Hz', 95: '4.8Hz', 96: '4.85Hz', 97: '4.9Hz',
                     98: '4.95Hz', 99: '5.0Hz', 100: '5.1Hz', 101: '5.2Hz', 102: '5.3Hz', 103: '5.4Hz', 104: '5.5Hz',
                     105: '5.6Hz', 106: '5.7Hz', 107: '5.8Hz', 108: '5.9Hz', 109: '6.0Hz', 110: '6.1Hz',
                     111: '6.2Hz', 112: '6.3Hz', 113: '6.4Hz', 114: '6.5Hz', 115: '6.6Hz', 116: '6.7Hz',
                     117: '6.8Hz', 118: '6.9Hz', 119: '7.0Hz', 120: '7.5Hz', 121: '8.0Hz', 122: '8.5Hz',
                     123: '9.0Hz', 124: '9.5Hz', 125: '10.0Hz', 126: '10Hz', 127: '10Hz'}
                    )

    # Rate2 (Hz)
    PARAM_TYPE_7 =  ({0: '0.05Hz', 1: '0.1Hz', 2: '0.15Hz', 3: '0.2Hz', 4: '0.25Hz', 5: '0.3Hz',
                      6: '0.35Hz', 7: '0.4Hz', 8: '0.45Hz', 9: '0.5Hz', 10: '0.55Hz', 11: '0.6Hz',
                      12: '0.65Hz', 13: '0.7Hz', 14: '0.75Hz', 15: '0.8Hz', 16: '0.85Hz', 17: '0.9Hz',
                      18: '0.95Hz', 19: '1.0Hz', 20: '1.05Hz', 21: '1.1Hz', 22: '1.15Hz', 23: '1.2Hz',
                      24: '1.25Hz', 25: '1.3Hz', 26: '1.35Hz', 27: '1.4Hz', 28: '1.45Hz', 29: '1.5Hz',
                      30: '1.55Hz', 31: '1.6Hz', 32: '1.65Hz', 33: '1.7Hz', 34: '1.75Hz', 35: '1.8Hz',
                      36: '1.85Hz', 37: '1.9Hz', 38: '1.95Hz', 39: '2.0Hz', 40: '2.05Hz', 41: '2.1Hz',
                      42: '2.15Hz', 43: '2.2Hz', 44: '2.25Hz', 45: '2.3Hz', 46: '2.35Hz', 47: '2.4Hz',
                      48: '2.45Hz', 49: '2.5Hz', 50: '2.55Hz', 51: '2.6Hz', 52: '2.65Hz', 53: '2.7Hz',
                      54: '2.75Hz', 55: '2.8Hz', 56: '2.85Hz', 57: '2.9Hz', 58: '2.95Hz', 59: '3.0Hz',
                      60: '3.05Hz', 61: '3.1Hz', 62: '3.15Hz', 63: '3.2Hz', 64: '3.25Hz', 65: '3.3Hz',
                      66: '3.35Hz', 67: '3.4Hz', 68: '3.45Hz', 69: '3.5Hz', 70: '3.55Hz', 71: '3.6Hz',
                      72: '3.65Hz', 73: '3.7Hz', 74: '3.75Hz', 75: '3.8Hz', 76: '3.85Hz', 77: '3.9Hz',
                      78: '3.95Hz', 79: '4.0Hz', 80: '4.05Hz', 81: '4.1Hz', 82: '4.15Hz', 83: '4.2Hz',
                      84: '4.25Hz', 85: '4.3Hz', 86: '4.35Hz', 87: '4.4Hz', 88: '4.45Hz', 89: '4.5Hz',
                      90: '4.55Hz', 91: '4.6Hz', 92: '4.65Hz', 93: '4.7Hz', 94: '4.75Hz', 95: '4.8Hz',
                      96: '4.85Hz', 97: '4.9Hz', 98: '4.95Hz', 99: '5.0Hz', 100: '5.05Hz', 101: '5.1Hz',
                      102: '5.15Hz', 103: '5.2Hz', 104: '5.25Hz', 105: '5.3Hz', 106: '5.35Hz',
                      107: '5.4Hz', 108: '5.45Hz', 109: '5.5Hz', 110: '5.55Hz', 111: '5.6Hz',
                      112: '5.65Hz', 113: '5.7Hz', 114: '5.75Hz', 115: '5.8Hz', 116: '5.85Hz',
                      117: '5.9Hz', 118: '5.95Hz', 119: '6.0Hz', 120: '6.05Hz', 121: '6.1Hz',
                      122: '6.15Hz', 123: '6.2Hz', 124: '6.25Hz', 125: '6.3Hz', 126: '6.35Hz',
                      127: '6.4Hz'})


    # HF Damp (HZ)
    PARAM_TYPE_8 = (
        {0: '315Hz', 1: '315Hz', 2: '315Hz', 3: '315Hz', 4: '315Hz', 5: '315Hz', 6: '315Hz', 7: '315Hz', 8: '400Hz',
         9: '400Hz', 10: '400Hz', 11: '400Hz', 12: '400Hz', 13: '400Hz', 14: '400Hz', 15: '400Hz', 16: '500Hz',
         17: '500Hz', 18: '500Hz', 19: '500Hz', 20: '500Hz', 21: '500Hz', 22: '500Hz', 23: '500Hz', 24: '630Hz',
         25: '630Hz', 26: '630Hz', 27: '630Hz', 28: '630Hz', 29: '630Hz', 30: '630Hz', 31: '630Hz', 32: '800Hz',
         33: '800Hz', 34: '800Hz', 35: '800Hz', 36: '800Hz', 37: '800Hz', 38: '800Hz', 39: '800Hz', 40: '1000Hz',
         41: '1000Hz', 42: '1000Hz', 43: '1000Hz', 44: '1000Hz', 45: '1000Hz', 46: '1000Hz', 47: '1000Hz',
         48: '1250Hz', 49: '1250Hz', 50: '1250Hz', 51: '1250Hz', 52: '1250Hz', 53: '1250Hz', 54: '1250Hz',
         55: '1250Hz', 56: '1600Hz', 57: '1600Hz', 58: '1600Hz', 59: '1600Hz', 60: '1600Hz', 61: '1600Hz',
         62: '1600Hz', 63: '1600Hz', 64: '2000Hz', 65: '2000Hz', 66: '2000Hz', 67: '2000Hz', 68: '2000Hz',
         69: '2000Hz', 70: '2000Hz', 71: '2000Hz', 72: '2500Hz', 73: '2500Hz', 74: '2500Hz', 75: '2500Hz',
         76: '2500Hz', 77: '2500Hz', 78: '2500Hz', 79: '2500Hz', 80: '3150Hz', 81: '3150Hz', 82: '3150Hz',
         83: '3150Hz', 84: '3150Hz', 85: '3150Hz', 86: '3150Hz', 87: '3150Hz', 88: '4000Hz', 89: '4000Hz',
         90: '4000Hz', 91: '4000Hz', 92: '4000Hz', 93: '4000Hz', 94: '4000Hz', 95: '4000Hz', 96: '5000Hz',
         97: '5000Hz', 98: '5000Hz', 99: '5000Hz', 100: '5000Hz', 101: '5000Hz', 102: '5000Hz', 103: '5000Hz',
         104: '6300Hz', 105: '6300Hz', 106: '6300Hz', 107: '6300Hz', 108: '6300Hz', 109: '6300Hz',
         110: '6300Hz', 111: '6300Hz', 112: '8000Hz', 113: '8000Hz', 114: '8000Hz', 115: '8000Hz',
         116: '8000Hz', 117: '8000Hz', 118: '8000Hz', 119: '8000Hz', 120: 'Bypass', 121: 'Bypass',
         122: 'Bypass', 123: 'Bypass', 124: 'Bypass', 125: 'Bypass', 126: 'Bypass', 127: 'Bypass'}
    )

    # Cutoff Freq (Hz)
    PARAM_TYPE_9 = (
        {0: '250Hz', 1: '250Hz', 2: '250Hz', 3: '250Hz', 4: '250Hz', 5: '250Hz', 6: '250Hz',
         7: '250Hz', 8: '315Hz', 9: '315Hz', 10: '315Hz', 11: '315Hz', 12: '315Hz', 13: '315Hz',
         14: '315Hz', 15: '315Hz', 16: '400Hz', 17: '400Hz', 18: '400Hz', 19: '400Hz', 20: '400Hz',
         21: '400Hz', 22: '400Hz', 23: '400Hz', 24: '500Hz', 25: '500Hz', 26: '500Hz', 27: '500Hz',
         28: '500Hz', 29: '500Hz', 30: '500Hz', 31: '500Hz', 32: '630Hz', 33: '630Hz', 34: '630Hz',
         35: '630Hz', 36: '630Hz', 37: '630Hz', 38: '630Hz', 39: '630Hz', 40: '800Hz', 41: '800Hz',
         42: '800Hz', 43: '800Hz', 44: '800Hz', 45: '800Hz', 46: '800Hz', 47: '800Hz', 48: '1000Hz',
         49: '1000Hz', 50: '1000Hz', 51: '1000Hz', 52: '1000Hz', 53: '1000Hz', 54: '1000Hz',
         55: '1000Hz', 56: '1250Hz', 57: '1250Hz', 58: '1250Hz', 59: '1250Hz', 60: '1250Hz',
         61: '1250Hz', 62: '1250Hz', 63: '1250Hz', 64: '1600Hz', 65: '1600Hz', 66: '1600Hz',
         67: '1600Hz', 68: '1600Hz', 69: '1600Hz', 70: '1600Hz', 71: '1600Hz', 72: '2000Hz',
         73: '2000Hz', 74: '2000Hz', 75: '2000Hz', 76: '2000Hz', 77: '2000Hz', 78: '2000Hz',
         79: '2000Hz', 80: '2500Hz', 81: '2500Hz', 82: '2500Hz', 83: '2500Hz', 84: '2500Hz',
         85: '2500Hz', 86: '2500Hz', 87: '2500Hz', 88: '3150Hz', 89: '3150Hz', 90: '3150Hz',
         91: '3150Hz', 92: '3150Hz', 93: '3150Hz', 94: '3150Hz', 95: '3150Hz', 96: '4000Hz',
         97: '4000Hz', 98: '4000Hz', 99: '4000Hz', 100: '4000Hz', 101: '4000Hz', 102: '4000Hz',
         103: '4000Hz', 104: '5000Hz', 105: '5000Hz', 106: '5000Hz', 107: '5000Hz', 108: '5000Hz',
         109: '5000Hz', 110: '5000Hz', 111: '5000Hz', 112: '6300Hz', 113: '6300Hz', 114: '6300Hz',
         115: '6300Hz', 116: '6300Hz', 117: '6300Hz', 118: '6300Hz', 119: '6300Hz', 120: '8000Hz',
         121: '8000Hz', 122: '8000Hz', 123: '8000Hz', 124: '8000Hz', 125: '8000Hz', 126: '8000Hz',
         127: '8000Hz'})

    # SEMIPAR_10=[]
    # for hz in [200,250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300]:
    #   for pippo in range(1,9):
    #      SEMIPAR_10.append(str(hz)+'Hz')
    # print(SEMIPAR_10)
    #
    # PAR_10= tools.mergeRanges(range(0x00,0x80),SEMIPAR_10)
    # print(PAR_10)

    # EQ Freq
    PARAM_TYPE_10 = (
        {0: '200Hz', 1: '200Hz', 2: '200Hz', 3: '200Hz', 4: '200Hz', 5: '200Hz', 6: '200Hz', 7: '200Hz',
         8: '250Hz', 9: '250Hz', 10: '250Hz', 11: '250Hz', 12: '250Hz', 13: '250Hz', 14: '250Hz', 15: '250Hz',
         16: '315Hz', 17: '315Hz', 18: '315Hz', 19: '315Hz', 20: '315Hz', 21: '315Hz', 22: '315Hz', 23: '315Hz',
         24: '400Hz', 25: '400Hz', 26: '400Hz', 27: '400Hz', 28: '400Hz', 29: '400Hz', 30: '400Hz', 31: '400Hz',
         32: '500Hz', 33: '500Hz', 34: '500Hz', 35: '500Hz', 36: '500Hz', 37: '500Hz', 38: '500Hz', 39: '500Hz',
         40: '630Hz', 41: '630Hz', 42: '630Hz', 43: '630Hz', 44: '630Hz', 45: '630Hz', 46: '630Hz', 47: '630Hz',
         48: '800Hz', 49: '800Hz', 50: '800Hz', 51: '800Hz', 52: '800Hz', 53: '800Hz', 54: '800Hz', 55: '800Hz',
         56: '1000Hz', 57: '1000Hz', 58: '1000Hz', 59: '1000Hz', 60: '1000Hz', 61: '1000Hz', 62: '1000Hz',
         63: '1000Hz', 64: '1250Hz', 65: '1250Hz', 66: '1250Hz', 67: '1250Hz', 68: '1250Hz', 69: '1250Hz',
         70: '1250Hz', 71: '1250Hz', 72: '1600Hz', 73: '1600Hz', 74: '1600Hz', 75: '1600Hz', 76: '1600Hz',
         77: '1600Hz', 78: '1600Hz', 79: '1600Hz', 80: '2000Hz', 81: '2000Hz', 82: '2000Hz', 83: '2000Hz',
         84: '2000Hz', 85: '2000Hz', 86: '2000Hz', 87: '2000Hz', 88: '2500Hz', 89: '2500Hz', 90: '2500Hz',
         91: '2500Hz', 92: '2500Hz', 93: '2500Hz', 94: '2500Hz', 95: '2500Hz', 96: '3150Hz', 97: '3150Hz',
         98: '3150Hz', 99: '3150Hz', 100: '3150Hz', 101: '3150Hz', 102: '3150Hz', 103: '3150Hz', 104: '4000Hz',
         105: '4000Hz', 106: '4000Hz', 107: '4000Hz', 108: '4000Hz', 109: '4000Hz', 110: '4000Hz', 111: '4000Hz',
         112: '5000Hz', 113: '5000Hz', 114: '5000Hz', 115: '5000Hz', 116: '5000Hz', 117: '5000Hz', 118: '5000Hz',
         119: '5000Hz', 120: '6300Hz', 121: '6300Hz', 122: '6300Hz', 123: '6300Hz', 124: '6300Hz', 125: '6300Hz',
         126: '6300Hz', 127: '6300Hz'}
    )

    # LPF

    # SEMIPAR_11=[]
    # for hz in [250,315,400,500,630,800,1000,1250,1600,2000,2500,3150,4000,5000,6300,'Bypass']:
    #     for pippo in range(1,9):
    #         SEMIPAR_11.append(str(hz)+'{}'.format("Hz" if hz != "Bypass" else ""))
    # print(SEMIPAR_11)
    #
    # PAR_10= tools.mergeRanges(range(0x00,0x80),SEMIPAR_11)
    # print(PAR_11)

    PARAM_TYPE_11 = ({0: '250Hz', 1: '250Hz', 2: '250Hz', 3: '250Hz', 4: '250Hz', 5: '250Hz',
                      6: '250Hz', 7: '250Hz', 8: '315Hz', 9: '315Hz', 10: '315Hz', 11: '315Hz',
                      12: '315Hz', 13: '315Hz', 14: '315Hz', 15: '315Hz', 16: '400Hz', 17: '400Hz',
                      18: '400Hz', 19: '400Hz', 20: '400Hz', 21: '400Hz', 22: '400Hz', 23: '400Hz',
                      24: '500Hz', 25: '500Hz', 26: '500Hz', 27: '500Hz', 28: '500Hz', 29: '500Hz',
                      30: '500Hz', 31: '500Hz', 32: '630Hz', 33: '630Hz', 34: '630Hz', 35: '630Hz',
                      36: '630Hz', 37: '630Hz', 38: '630Hz', 39: '630Hz', 40: '800Hz', 41: '800Hz',
                      42: '800Hz', 43: '800Hz', 44: '800Hz', 45: '800Hz', 46: '800Hz', 47: '800Hz',
                      48: '1000Hz', 49: '1000Hz', 50: '1000Hz', 51: '1000Hz', 52: '1000Hz',
                      53: '1000Hz', 54: '1000Hz', 55: '1000Hz', 56: '1250Hz', 57: '1250Hz',
                      58: '1250Hz', 59: '1250Hz', 60: '1250Hz', 61: '1250Hz', 62: '1250Hz',
                      63: '1250Hz', 64: '1600Hz', 65: '1600Hz', 66: '1600Hz', 67: '1600Hz',
                      68: '1600Hz', 69: '1600Hz', 70: '1600Hz', 71: '1600Hz', 72: '2000Hz',
                      73: '2000Hz', 74: '2000Hz', 75: '2000Hz', 76: '2000Hz', 77: '2000Hz',
                      78: '2000Hz', 79: '2000Hz', 80: '2500Hz', 81: '2500Hz', 82: '2500Hz',
                      83: '2500Hz', 84: '2500Hz', 85: '2500Hz', 86: '2500Hz', 87: '2500Hz',
                      88: '3150Hz', 89: '3150Hz', 90: '3150Hz', 91: '3150Hz', 92: '3150Hz',
                      93: '3150Hz', 94: '3150Hz', 95: '3150Hz', 96: '4000Hz', 97: '4000Hz',
                      98: '4000Hz', 99: '4000Hz', 100: '4000Hz', 101: '4000Hz', 102: '4000Hz',
                      103: '4000Hz', 104: '5000Hz', 105: '5000Hz', 106: '5000Hz', 107: '5000Hz',
                      108: '5000Hz', 109: '5000Hz', 110: '5000Hz', 111: '5000Hz', 112: '6300Hz',
                      113: '6300Hz', 114: '6300Hz', 115: '6300Hz', 116: '6300Hz', 117: '6300Hz',
                      118: '6300Hz', 119: '6300Hz', 120: 'Bypass', 121: 'Bypass', 122: 'Bypass',
                      123: 'Bypass', 124: 'Bypass', 125: 'Bypass', 126: 'Bypass', 127: 'Bypass'})

    # Manual

    # PARAM_TYPE_12
    # p = tools.ulist(100,300,10,'Hz')
    # print(len(p))
    # s = tools.ulist(320,1000,20,'Hz')
    # print(len(s))
    # t = tools.ulist(1100,8000,100,'Hz')
    # print(len(t))
    # q = 2 * ['8000Hz']
    #
    # p.extend(s)
    # print(len(p))
    # p.extend(t)
    # print(len(p))
    # p.extend(q)
    # z = tools.mergeRanges(range(0x00,0x80),p)

    # print(z)

    PARAM_TYPE_12 = ({0: '100Hz', 1: '110Hz', 2: '120Hz', 3: '130Hz', 4: '140Hz', 5: '150Hz', 6: '160Hz',
                      7: '170Hz', 8: '180Hz', 9: '190Hz', 10: '200Hz', 11: '210Hz', 12: '220Hz',
                      13: '230Hz', 14: '240Hz', 15: '250Hz', 16: '260Hz', 17: '270Hz', 18: '280Hz',
                      19: '290Hz', 20: '300Hz', 21: '320Hz', 22: '340Hz', 23: '360Hz', 24: '380Hz',
                      25: '400Hz', 26: '420Hz', 27: '440Hz', 28: '460Hz', 29: '480Hz', 30: '500Hz',
                      31: '520Hz', 32: '540Hz', 33: '560Hz', 34: '580Hz', 35: '600Hz', 36: '620Hz',
                      37: '640Hz', 38: '660Hz', 39: '680Hz', 40: '700Hz', 41: '720Hz', 42: '740Hz',
                      43: '760Hz', 44: '780Hz', 45: '800Hz', 46: '820Hz', 47: '840Hz', 48: '860Hz',
                      49: '880Hz', 50: '900Hz', 51: '920Hz', 52: '940Hz', 53: '960Hz', 54: '980Hz',
                      55: '1000Hz', 56: '1100Hz', 57: '1200Hz', 58: '1300Hz', 59: '1400Hz',
                      60: '1500Hz', 61: '1600Hz', 62: '1700Hz', 63: '1800Hz', 64: '1900Hz',
                      65: '2000Hz', 66: '2100Hz', 67: '2200Hz', 68: '2300Hz', 69: '2400Hz',
                      70: '2500Hz', 71: '2600Hz', 72: '2700Hz', 73: '2800Hz', 74: '2900Hz',
                      75: '3000Hz', 76: '3100Hz', 77: '3200Hz', 78: '3300Hz', 79: '3400Hz',
                      80: '3500Hz', 81: '3600Hz', 82: '3700Hz', 83: '3800Hz', 84: '3900Hz',
                      85: '4000Hz', 86: '4100Hz', 87: '4200Hz', 88: '4300Hz', 89: '4400Hz',
                      90: '4500Hz', 91: '4600Hz', 92: '4700Hz', 93: '4800Hz', 94: '4900Hz',
                      95: '5000Hz', 96: '5100Hz', 97: '5200Hz', 98: '5300Hz', 99: '5400Hz',
                      100: '5500Hz', 101: '5600Hz', 102: '5700Hz', 103: '5800Hz', 104: '5900Hz',
                      105: '6000Hz', 106: '6100Hz', 107: '6200Hz', 108: '6300Hz', 109: '6400Hz',
                      110: '6500Hz', 111: '6600Hz', 112: '6700Hz', 113: '6800Hz', 114: '6900Hz',
                      115: '7000Hz', 116: '7100Hz', 117: '7200Hz', 118: '7300Hz', 119: '7400Hz',
                      120: '7500Hz', 121: '7600Hz', 122: '7700Hz', 123: '7800Hz', 124: '7900Hz',
                      125: '8000Hz', 126: '8000Hz', 127: '8000Hz'})

    # Azimuth

    # PARAM_TYPE_13
    # c = 6 * ['L180(=R180)']
    # l = tools.rlist(168,1,-12,'L',4)
    #
    # print(len(l))
    # m = 4 * ['0']
    # print(len(m))
    # r = tools.rlist(12,179,12,'R',4)
    # print(len(r))
    # f = 6 * ['R180(=L180)']
    # print(len(f))
    #
    # c.extend(l)
    # c.extend(m)
    # c.extend(r)
    # c.extend(f)
    # base_range = range(0x00,0x80)
    # PARAM_TYPE_13 = tools.mergeRanges(base_range, c)
    # print(PARAM_TYPE_13)

    PARAM_TYPE_13 = ({0: 'L180(=R180)', 1: 'L180(=R180)', 2: 'L180(=R180)', 3: 'L180(=R180)',
                      4: 'L180(=R180)', 5: 'L180(=R180)', 6: 'L168', 7: 'L168', 8: 'L168', 9: 'L168',
                      10: 'L156', 11: 'L156', 12: 'L156', 13: 'L156', 14: 'L144', 15: 'L144',
                      16: 'L144', 17: 'L144', 18: 'L132', 19: 'L132', 20: 'L132', 21: 'L132', 22: 'L120',
                      23: 'L120', 24: 'L120', 25: 'L120', 26: 'L108', 27: 'L108', 28: 'L108', 29: 'L108',
                      30: 'L96', 31: 'L96', 32: 'L96', 33: 'L96', 34: 'L84', 35: 'L84', 36: 'L84',
                      37: 'L84', 38: 'L72', 39: 'L72', 40: 'L72', 41: 'L72', 42: 'L60', 43: 'L60',
                      44: 'L60', 45: 'L60', 46: 'L48', 47: 'L48', 48: 'L48', 49: 'L48', 50: 'L36',
                      51: 'L36', 52: 'L36', 53: 'L36', 54: 'L24', 55: 'L24', 56: 'L24', 57: 'L24',
                      58: 'L12', 59: 'L12', 60: 'L12', 61: 'L12', 62: '0', 63: '0', 64: '0', 65: '0',
                      66: 'R12', 67: 'R12', 68: 'R12', 69: 'R12', 70: 'R24', 71: 'R24', 72: 'R24',
                      73: 'R24', 74: 'R36', 75: 'R36', 76: 'R36', 77: 'R36', 78: 'R48', 79: 'R48',
                      80: 'R48', 81: 'R48', 82: 'R60', 83: 'R60', 84: 'R60', 85: 'R60', 86: 'R72',
                      87: 'R72', 88: 'R72', 89: 'R72', 90: 'R84', 91: 'R84', 92: 'R84', 93: 'R84',
                      94: 'R96', 95: 'R96', 96: 'R96', 97: 'R96', 98: 'R108', 99: 'R108', 100: 'R108',
                      101: 'R108', 102: 'R120', 103: 'R120', 104: 'R120', 105: 'R120', 106: 'R132',
                      107: 'R132', 108: 'R132', 109: 'R132', 110: 'R144', 111: 'R144', 112: 'R144',
                      113: 'R144', 114: 'R156', 115: 'R156', 116: 'R156', 117: 'R156', 118: 'R168',
                      119: 'R168', 120: 'R168', 121: 'R168', 122: 'R180(=L180)', 123: 'R180(=L180)',
                      124: 'R180(=L180)', 125: 'R180(=L180)', 126: 'R180(=L180)', 127: 'R180(=L180)'}
)

    # Accl

    # PARAM_TYPE_14
    # d = tools.rlist(0,15,1,factor = 8)
    # p = tools.mergeRanges(base_range,d)
    # print(p)

    PARAM_TYPE_14 = ({0: '0', 1: '0', 2: '0', 3: '0', 4: '0', 5: '0', 6: '0', 7: '0', 8: '1', 9: '1',
                      10: '1', 11: '1', 12: '1', 13: '1', 14: '1', 15: '1', 16: '2', 17: '2', 18: '2',
                      19: '2', 20: '2', 21: '2', 22: '2', 23: '2', 24: '3', 25: '3', 26: '3', 27: '3',
                      28: '3', 29: '3', 30: '3', 31: '3', 32: '4', 33: '4', 34: '4', 35: '4', 36: '4',
                      37: '4', 38: '4', 39: '4', 40: '5', 41: '5', 42: '5', 43: '5', 44: '5', 45: '5',
                      46: '5', 47: '5', 48: '6', 49: '6', 50: '6', 51: '6', 52: '6', 53: '6', 54: '6',
                      55: '6', 56: '7', 57: '7', 58: '7', 59: '7', 60: '7', 61: '7', 62: '7', 63: '7',
                      64: '8', 65: '8', 66: '8', 67: '8', 68: '8', 69: '8', 70: '8', 71: '8', 72: '9',
                      73: '9', 74: '9', 75: '9', 76: '9', 77: '9', 78: '9', 79: '9', 80: '10', 81: '10',
                      82: '10', 83: '10', 84: '10', 85: '10', 86: '10', 87: '10', 88: '11', 89: '11',
                      90: '11', 91: '11', 92: '11', 93: '11', 94: '11', 95: '11', 96: '12', 97: '12',
                      98: '12', 99: '12', 100: '12', 101: '12', 102: '12', 103: '12', 104: '13',
                      105: '13', 106: '13', 107: '13', 108: '13', 109: '13', 110: '13', 111: '13',
                      112: '14', 113: '14', 114: '14', 115: '14', 116: '14', 117: '14', 118: '14',
                      119: '14', 120: '15', 121: '15', 122: '15', 123: '15', 124: '15', 125: '15',
                      126: '15', 127: '15'}
                     )

    # *15 : Bass Cut Freq
    PARAM_TYPE_15 = (
        {0: '20', 1: '20', 2: '20', 3: '20', 4: '20', 5: '20', 6: '20', 7: '20', 8: '25', 9: '25',
         10: '25', 11: '25', 12: '25', 13: '25', 14: '25', 15: '25', 16: '35', 17: '35', 18: '35',
         19: '35', 20: '35', 21: '35', 22: '35', 23: '35', 24: '50', 25: '50', 26: '50', 27: '50',
         28: '50', 29: '50', 30: '50', 31: '50', 32: '85', 33: '85', 34: '85', 35: '85', 36: '85',
         37: '85', 38: '85', 39: '85', 40: '115', 41: '115', 42: '115', 43: '115', 44: '115', 45: '115',
         46: '115', 47: '115', 48: '150', 49: '150', 50: '150', 51: '150', 52: '150', 53: '150',
         54: '150', 55: '150', 56: '200', 57: '200', 58: '200', 59: '200', 60: '200', 61: '200',
         62: '200', 63: '200', 64: '250', 65: '250', 66: '250', 67: '250', 68: '250', 69: '250',
         70: '250', 71: '250', 72: '350', 73: '350', 74: '350', 75: '350', 76: '350', 77: '350',
         78: '350', 79: '350', 80: '500', 81: '500', 82: '500', 83: '500', 84: '500', 85: '500',
         86: '500', 87: '500', 88: '650', 89: '650', 90: '650', 91: '650', 92: '650', 93: '650',
         94: '650', 95: '650', 96: '850', 97: '850', 98: '850', 99: '850', 100: '850', 101: '850',
         102: '850', 103: '850', 104: '1000', 105: '1000', 106: '1000', 107: '1000', 108: '1000',
         109: '1000', 110: '1000', 111: '1000', 112: '1500', 113: '1500', 114: '1500', 115: '1500',
         116: '1500', 117: '1500', 118: '1500', 119: '1500', 120: '2000', 121: '2000', 122: '2000',
         123: '2000', 124: '2000', 125: '2000', 126: '2000', 127: '2000'}
    )

    # Reverb Time

    # PARAM_TYPE_16 = tools.mergeRanges(range(0x00,0x64),tools.ulist(0.1,10,0.1,'s'))
    # PARAM_TYPE_16_B = tools.mergeRanges(range(0x64,0x80),tools.ulist(11,38,1,'s'))
    # PARAM_TYPE_16.update(PARAM_TYPE_16_B)


    PARAM_TYPE_16 = ({0: '0.1s', 1: '0.2s', 2: '0.3s', 3: '0.4s', 4: '0.5s', 5: '0.6s', 6: '0.7s', 7: '0.8s',
                      8: '0.9s', 9: '1.0s', 10: '1.1s', 11: '1.2s', 12: '1.3s', 13: '1.4s', 14: '1.5s',
                      15: '1.6s', 16: '1.7s', 17: '1.8s', 18: '1.9s', 19: '2.0s', 20: '2.1s', 21: '2.2s',
                      22: '2.3s', 23: '2.4s', 24: '2.5s', 25: '2.6s', 26: '2.7s', 27: '2.8s', 28: '2.9s',
                      29: '3.0s', 30: '3.1s', 31: '3.2s', 32: '3.3s', 33: '3.4s', 34: '3.5s', 35: '3.6s',
                      36: '3.7s', 37: '3.8s', 38: '3.9s', 39: '4.0s', 40: '4.1s', 41: '4.2s', 42: '4.3s',
                      43: '4.4s', 44: '4.5s', 45: '4.6s', 46: '4.7s', 47: '4.8s', 48: '4.9s', 49: '5.0s',
                      50: '5.1s', 51: '5.2s', 52: '5.3s', 53: '5.4s', 54: '5.5s', 55: '5.6s', 56: '5.7s',
                      57: '5.8s', 58: '5.9s', 59: '6.0s', 60: '6.1s', 61: '6.2s', 62: '6.3s', 63: '6.4s',
                      64: '6.5s', 65: '6.6s', 66: '6.7s', 67: '6.8s', 68: '6.9s', 69: '7.0s', 70: '7.1s',
                      71: '7.2s', 72: '7.3s', 73: '7.4s', 74: '7.5s', 75: '7.6s', 76: '7.7s', 77: '7.8s',
                      78: '7.9s', 79: '8.0s', 80: '8.1s', 81: '8.2s', 82: '8.3s', 83: '8.4s', 84: '8.5s',
                      85: '8.6s', 86: '8.7s', 87: '8.8s', 88: '8.9s', 89: '9.0s', 90: '9.1s', 91: '9.2s',
                      92: '9.3s', 93: '9.4s', 94: '9.5s', 95: '9.6s', 96: '9.7s', 97: '9.8s', 98: '9.9s',
                      99: '10.0s', 100: '11s', 101: '12s', 102: '13s', 103: '14s', 104: '15s', 105: '16s',
                      106: '17s', 107: '18s', 108: '19s', 109: '20s', 110: '21s', 111: '22s', 112: '23s',
                      113: '24s', 114: '25s', 115: '26s', 116: '27s', 117: '28s', 118: '29s', 119: '30s',
                      120: '31s', 121: '32s', 122: '33s', 123: '34s', 124: '35s', 125: '36s', 126: '37s', 127: '38s'}
                     )
    # Distance

    # PARAM_TYPE_17
    # d1 = tools.rlist(0.1,10,0.1,'Hz')
    # print(d1)
    # d2 = tools.rlist(11.0,38,1,'Hz')
    # print(d2)
    # d1.extend(d2)
    # print(len(d1))
    # p = tools.mergeRanges(base_range, d1)
    # print(p)

    PARAM_TYPE_17 = ({0: '0.1Hz', 1: '0.2Hz', 2: '0.3Hz', 3: '0.4Hz', 4: '0.5Hz', 5: '0.6Hz', 6: '0.7Hz',
                      7: '0.8Hz', 8: '0.9Hz', 9: '1.0Hz', 10: '1.1Hz', 11: '1.2Hz', 12: '1.3Hz',
                      13: '1.4Hz', 14: '1.5Hz', 15: '1.6Hz', 16: '1.7Hz', 17: '1.8Hz', 18: '1.9Hz',
                      19: '2.0Hz', 20: '2.1Hz', 21: '2.2Hz', 22: '2.3Hz', 23: '2.4Hz', 24: '2.5Hz',
                      25: '2.6Hz', 26: '2.7Hz', 27: '2.8Hz', 28: '2.9Hz', 29: '3.0Hz', 30: '3.1Hz',
                      31: '3.2Hz', 32: '3.3Hz', 33: '3.4Hz', 34: '3.5Hz', 35: '3.6Hz', 36: '3.7Hz',
                      37: '3.8Hz', 38: '3.9Hz', 39: '4.0Hz', 40: '4.1Hz', 41: '4.2Hz', 42: '4.3Hz',
                      43: '4.4Hz', 44: '4.5Hz', 45: '4.6Hz', 46: '4.7Hz', 47: '4.8Hz', 48: '4.9Hz',
                      49: '5.0Hz', 50: '5.1Hz', 51: '5.2Hz', 52: '5.3Hz', 53: '5.4Hz', 54: '5.5Hz',
                      55: '5.6Hz', 56: '5.7Hz', 57: '5.8Hz', 58: '5.9Hz', 59: '6.0Hz', 60: '6.1Hz',
                      61: '6.2Hz', 62: '6.3Hz', 63: '6.4Hz', 64: '6.5Hz', 65: '6.6Hz', 66: '6.7Hz',
                      67: '6.8Hz', 68: '6.9Hz', 69: '7.0Hz', 70: '7.1Hz', 71: '7.2Hz', 72: '7.3Hz',
                      73: '7.4Hz', 74: '7.5Hz', 75: '7.6Hz', 76: '7.7Hz', 77: '7.8Hz', 78: '7.9Hz',
                      79: '8.0Hz', 80: '8.1Hz', 81: '8.2Hz', 82: '8.3Hz', 83: '8.4Hz', 84: '8.5Hz',
                      85: '8.6Hz', 86: '8.7Hz', 87: '8.8Hz', 88: '8.9Hz', 89: '9.0Hz', 90: '9.1Hz',
                      91: '9.2Hz', 92: '9.3Hz', 93: '9.4Hz', 94: '9.5Hz', 95: '9.6Hz', 96: '9.7Hz',
                      97: '9.8Hz', 98: '9.9Hz', 99: '10.0Hz', 100: '11.0Hz', 101: '12.0Hz',
                      102: '13.0Hz', 103: '14.0Hz', 104: '15.0Hz', 105: '16.0Hz', 106: '17.0Hz',
                      107: '18.0Hz', 108: '19.0Hz', 109: '20.0Hz', 110: '21.0Hz', 111: '22.0Hz',
                      112: '23.0Hz', 113: '24.0Hz', 114: '25.0Hz', 115: '26.0Hz', 116: '27.0Hz',
                      117: '28.0Hz', 118: '29.0Hz', 119: '30.0Hz', 120: '31.0Hz', 121: '32.0Hz',
                      122: '33.0Hz', 123: '34.0Hz', 124: '35.0Hz', 125: '36.0Hz', 126: '37.0Hz', 127: '38.0Hz'})

    # Boost Freq

    # PARAM_TYPE_18
    # this is shortissimo - and it's not used anywhere!!
    # d1 = tools.rlist(60,200,20)
    # d2 = tools.rlist(300,400,100)
    # d1.extend(d2)
    # p = tools.mergeRanges(range(0x00,0x0A), d1)
    # print(p)

    PARAM_TYPE_18 = ({0: '60', 1: '80', 2: '100', 3: '120', 4: '140',
                      5: '160', 6: '180', 7: '200', 8: '300', 9: '400'})

    # Those are funny. Non capire O~O
    BALANCE_VALUES = ({0: 'D>0E', 1: 'D>0E', 2: 'D>1E', 3: 'D>3E', 4: 'D>4E', 5: 'D>6E', 6: 'D>7E',
                       7: 'D>9E', 8: 'D>11E', 9: 'D>12E', 10: 'D>14E', 11: 'D>15E', 12: 'D>17E',
                       13: 'D>19E', 14: 'D>20E', 15: 'D>22E', 16: 'D>23E', 17: 'D>25E', 18: 'D>26E',
                       19: 'D>28E', 20: 'D>30E', 21: 'D>31E', 22: 'D>33E', 23: 'D>34E', 24: 'D>36E',
                       25: 'D>38E', 26: 'D>39E', 27: 'D>41E', 28: 'D>42E', 29: 'D>44E', 30: 'D>46E',
                       31: 'D>47E', 32: 'D>49E', 33: 'D>50E', 34: 'D>52E', 35: 'D>53E', 36: 'D>55E',
                       37: 'D>57E', 38: 'D>58E', 39: 'D>60E', 40: 'D>61E', 41: 'D>63E', 42: 'D>65E',
                       43: 'D>66E', 44: 'D>68E', 45: 'D>69E', 46: 'D>71E', 47: 'D>73E', 48: 'D>74E',
                       49: 'D>76E', 50: 'D>77E', 51: 'D>79E', 52: 'D>80E', 53: 'D>82E', 54: 'D>84E',
                       55: 'D>85E', 56: 'D>87E', 57: 'D>88E', 58: 'D>90E', 59: 'D>92E', 60: 'D>93E',
                       61: 'D>95E', 62: 'D>96E', 63: 'D>98E', 64: 'D=E', 65: 'D98<E', 66: 'D96<E',
                       67: 'D95<E', 68: 'D93<E', 69: 'D92<E', 70: 'D90<E', 71: 'D88<E', 72: 'D87<E',
                       73: 'D85<E', 74: 'D84<E', 75: 'D82<E', 76: 'D80<E', 77: 'D79<E', 78: 'D77<E',
                       79: 'D76<E', 80: 'D74<E', 81: 'D73<E', 82: 'D71<E', 83: 'D69<E', 84: 'D68<E',
                       85: 'D66<E', 86: 'D65<E', 87: 'D63<E', 88: 'D61<E', 89: 'D60<E', 90: 'D58<E',
                       91: 'D57<E', 92: 'D55<E', 93: 'D53<E', 94: 'D52<E', 95: 'D50<E', 96: 'D49<E',
                       97: 'D47<E', 98: 'D46<E', 99: 'D44<E', 100: 'D42<E', 101: 'D41<E', 102: 'D39<E',
                       103: 'D38<E', 104: 'D36<E', 105: 'D34<E', 106: 'D33<E', 107: 'D31<E',
                       108: 'D30<E', 109: 'D28<E', 110: 'D26<E', 111: 'D25<E', 112: 'D23<E',
                       113: 'D22<E', 114: 'D20<E', 115: 'D19<E', 116: 'D17<E', 117: 'D15<E',
                       118: 'D14<E', 119: 'D12<E', 120: 'D11<E', 121: 'D9<E', 122: 'D7<E',
                       123: 'D6<E', 124: 'D4<E', 125: 'D3<E', 126: 'D1<E', 127: 'D0<E'})



    PARAM_ON_OFF = {0: 'Off', 1: 'On'}
    PARAM_UP_DOWN = {0: 'Down', 1: 'Up'}

    # -12dB - +12dB
    # PARAM_12DB = tools.mergeRanges(range(0x34,0x4D), tools.ulist(-12,+12,1,'dB'))
    PARAM_12DB = ({52: '-12dB', 53: '-11dB', 54: '-10dB', 55: '-9dB', 56: '-8dB', 57: '-7dB', 58: '-6dB',
                   59: '-5dB', 60: '-4dB', 61: '-3dB', 62: '-2dB', 63: '-1dB', 64: '0dB', 65: '1dB',
                   66: '2dB', 67: '3dB', 68: '4dB', 69: '5dB', 70: '6dB', 71: '7dB', 72: '8dB', 73: '9dB',
                   74: '10dB', 75: '11dB', 76: '12dB'}
                  )

    # 0 - 18 dB - well, actually is 0 - 22 (as for the documentation there is a range problem...)
    # Low Boost Level....0dB - +8dB - 18dB....40 - 56....04 the two ranges are different...
    # PARAM_0_18DB = tools.mergeRanges(range(0x40, 0x57), tools.ulist(0, +22, 1,'dB'))
    PARAM_0_18DB = ({64: '0dB', 65: '1dB', 66: '2dB', 67: '3dB', 68: '4dB', 69: '5dB', 70: '6dB', 71: '7dB',
                     72: '8dB', 73: '9dB', 74: '10dB', 75: '11dB', 76: '12dB', 77: '13dB', 78: '14dB', 79: '15dB',
                     80: '16dB', 81: '17dB', 82: '18dB', 83: '19dB', 84: '20dB', 85: '21dB', 86: '22dB'}
                    )

    # -24 - +12 
    # PARAM_2412 = tools.mergeRanges(range(0x28, 0x4D), tools.ulist(-24, +12, 1))
    PARAM_2412 = ({40: '-24', 41: '-23', 42: '-22', 43: '-21', 44: '-20', 45: '-19', 46: '-18',
                   47: '-17', 48: '-16', 49: '-15', 50: '-14', 51: '-13', 52: '-12', 53: '-11',
                   54: '-10', 55: '-9', 56: '-8', 57: '-7', 58: '-6', 59: '-5', 60: '-4', 61: '-3',
                   62: '-2', 63: '-1', 64: '0', 65: '1', 66: '2', 67: '3', 68: '4', 69: '5',
                   70: '6', 71: '7', 72: '8', 73: '9', 74: '10', 75: '11', 76: '12'})


    # 0-127
    # PARAM_0127 = tools.mergeRanges(range(0x00, 0x80), tools.ulist(0, 127, 1))

    PARAM_0127 = ({0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8',
                   9: '9', 10: '10', 11: '11', 12: '12', 13: '13', 14: '14', 15: '15', 16: '16',
                   17: '17', 18: '18', 19: '19', 20: '20', 21: '21', 22: '22', 23: '23', 24: '24',
                   25: '25', 26: '26', 27: '27', 28: '28', 29: '29', 30: '30', 31: '31', 32: '32',
                   33: '33', 34: '34', 35: '35', 36: '36', 37: '37', 38: '38', 39: '39', 40: '40',
                   41: '41', 42: '42', 43: '43', 44: '44', 45: '45', 46: '46', 47: '47', 48: '48',
                   49: '49', 50: '50', 51: '51', 52: '52', 53: '53', 54: '54', 55: '55', 56: '56',
                   57: '57', 58: '58', 59: '59', 60: '60', 61: '61', 62: '62', 63: '63', 64: '64',
                   65: '65', 66: '66', 67: '67', 68: '68', 69: '69', 70: '70', 71: '71', 72: '72',
                   73: '73', 74: '74', 75: '75', 76: '76', 77: '77', 78: '78', 79: '79', 80: '80',
                   81: '81', 82: '82', 83: '83', 84: '84', 85: '85', 86: '86', 87: '87', 88: '88',
                   89: '89', 90: '90', 91: '91', 92: '92', 93: '93', 94: '94', 95: '95', 96: '96',
                   97: '97', 98: '98', 99: '99', 100: '100', 101: '101', 102: '102', 103: '103',
                   104: '104', 105: '105', 106: '106', 107: '107', 108: '108', 109: '109', 110: '110',
                   111: '111', 112: '112', 113: '113', 114: '114', 115: '115', 116: '116', 117: '117',
                   118: '118', 119: '119', 120: '120', 121: '121', 122: '122', 123: '123', 124: '124',
                   125: '125', 126: '126', 127: '127'})



    # -98% - +98%
    # PARAM_9898 = tools.mergeRanges(range(0x0F, 0x72), tools.ulist(-98, +98, 2, '%'))
    PARAM_9898 = ({15: '-98%', 16: '-96%', 17: '-94%', 18: '-92%', 19: '-90%', 20: '-88%',
                   21: '-86%', 22: '-84%', 23: '-82%', 24: '-80%', 25: '-78%', 26: '-76%',
                   27: '-74%', 28: '-72%', 29: '-70%', 30: '-68%', 31: '-66%', 32: '-64%',
                   33: '-62%', 34: '-60%', 35: '-58%', 36: '-56%', 37: '-54%', 38: '-52%',
                   39: '-50%', 40: '-48%', 41: '-46%', 42: '-44%', 43: '-42%', 44: '-40%',
                   45: '-38%', 46: '-36%', 47: '-34%', 48: '-32%', 49: '-30%', 50: '-28%',
                   51: '-26%', 52: '-24%', 53: '-22%', 54: '-20%', 55: '-18%', 56: '-16%',
                   57: '-14%', 58: '-12%', 59: '-10%', 60: '-8%', 61: '-6%', 62: '-4%',
                   63: '-2%', 64: '0%', 65: '2%', 66: '4%', 67: '6%', 68: '8%', 69: '10%',
                   70: '12%', 71: '14%', 72: '16%', 73: '18%', 74: '20%', 75: '22%', 76: '24%',
                   77: '26%', 78: '28%', 79: '30%', 80: '32%', 81: '34%', 82: '36%', 83: '38%',
                   84: '40%', 85: '42%', 86: '44%', 87: '46%', 88: '48%', 89: '50%', 90: '52%',
                   91: '54%', 92: '56%', 93: '58%', 94: '60%', 95: '62%', 96: '64%', 97: '66%',
                   98: '68%', 99: '70%', 100: '72%', 101: '74%', 102: '76%', 103: '78%',
                   104: '80%', 105: '82%', 106: '84%', 107: '86%', 108: '88%', 109: '90%',
                   110: '92%', 111: '94%', 112: '96%', 113: '98%'})

    # -100 - +100
    # PARAM_100100 = tools.mergeRanges(range(0x0E, 0x73), tools.ulist(-100, +100, 2))
    PARAM_100100 = ({14: '-100', 15: '-98', 16: '-96', 17: '-94', 18: '-92', 19: '-90',
                     20: '-88', 21: '-86', 22: '-84', 23: '-82', 24: '-80', 25: '-78',
                     26: '-76', 27: '-74', 28: '-72', 29: '-70', 30: '-68', 31: '-66',
                     32: '-64', 33: '-62', 34: '-60', 35: '-58', 36: '-56', 37: '-54',
                     38: '-52', 39: '-50', 40: '-48', 41: '-46', 42: '-44', 43: '-42',
                     44: '-40', 45: '-38', 46: '-36', 47: '-34', 48: '-32', 49: '-30',
                     50: '-28', 51: '-26', 52: '-24', 53: '-22', 54: '-20', 55: '-18',
                     56: '-16', 57: '-14', 58: '-12', 59: '-10', 60: '-8', 61: '-6',
                     62: '-4', 63: '-2', 64: '0', 65: '2', 66: '4', 67: '6', 68: '8',
                     69: '10', 70: '12', 71: '14', 72: '16', 73: '18', 74: '20', 75: '22',
                     76: '24', 77: '26', 78: '28', 79: '30', 80: '32', 81: '34', 82: '36',
                     83: '38', 84: '40', 85: '42', 86: '44', 87: '46', 88: '48', 89: '50',
                     90: '52', 91: '54', 92: '56', 93: '58', 94: '60', 95: '62', 96: '64',
                     97: '66', 98: '68', 99: '70', 100: '72', 101: '74', 102: '76',
                     103: '78', 104: '80', 105: '82', 106: '84', 107: '86', 108: '88',
                     109: '90', 110: '92', 111: '94', 112: '96', 113: '98', 114: '100'})

    # TODO: Finish to add all necessary PARAM constants to complete the effects...

    # Let's initialise the dictionaries with the parameters.
    FULL_EFX_TYPE = {}
    FULL_EFX_PARAMETERS = {}

    # FULL_EFX_PARAMETERS[]: How to build them (brainstorming)
    # I need ranges in human form, bisides the HEX one for the SYSEX, so that the SPINBOX can show the human value and apply
    # the HEX value (whereas the decimal value would be fine too)
    # By now, if FULL_EFX_PARAMETERS[x] = par, we have
    # par[0]: parameter name (i.e. 'Reverb Time');
    # par[1]: range in "human" form
    # par[2]: complete hex range -> the single values must be passed through SYSEX
    # **** par[2] is a dictionaru where keys are hex values to pass and argument is the human value
    # **** **** like: {0: '0ms', 1: '1ms'}
    # par[3]: LSB/MSB of the parameter -> to pass to SYSEX
    # par[4]: default value (hex or decimal)
    #


    # FULL EFFECT MODE
    FULL_EFX_TYPE[1] = ('High Quality Reverb', [0x00, 0x11])
    FULL_EFX_PARAMETERS[1] = (
        ('Type', 'Room1/2/Plate1/2/Hall1/2', tools.mergeRanges(range(0x00, 0x06), ['Room1', 'Room2', 'Plate1', 'Plate2', 'Hall1', 'Hall2']), [0x03],
         0x03),
        ('Pre Dly', '0ms - 80ms - 635ms', PARAM_TYPE_5, [0x04], 0x10),
        ('Reverb Time', '0.1s - 2s - 38s', PARAM_TYPE_16, [0x05], 0x13),
        ('HF Damp', '-10 - -4 -0', tools.mergeRanges(range(0x00, 0x0B), tools.ulist(-10, 0, 1)), [0x06], 0x06),
        ('ER Pre Dly', '0 - 40ms - 635 ms', PARAM_TYPE_5, [0x07], 0x08),
        ('ER Mix', '0 - 15 - 127', PARAM_0127, [0x08], 0x0f),
        ('Diffusion', '0 - 9 - 10', tools.mergeRanges(range(0x00, 0x0B), tools.ulist(0, 10, 1)), [0x09], 0x09),
        ('Tone Low', '-12dB - 0dB - +12dB', PARAM_12DB, [0x0A], 0x40),
        ('Tone High', '-12dB - 0dB - +12dB', PARAM_12DB, [0x0B], 0x40),
        ('Balance', 'D > 0E - D0 < E', BALANCE_VALUES, [0x0C], 0x7f),
        ('EQ Low Freq', '200/400Hz', {0: '200Hz', 1: '400Hz'}, [0x0D], 0x00),
        ('EQ Low Gain', '-12dB - 0dB - +12dB', PARAM_12DB, [0x0E], 0x40),
        ('EQ Mid1 Freq', '200Hz - 315Hz - 6300 Hz', PARAM_TYPE_10, [0x0F], 16),
        ('EQ Mid1 Q', '0.5/1.0/2.0/4.0/9.0', {0: '0.5', 1: '1.0', 2: '2.0', 3: '4.0', 4: '9.0'}, [0x10], 0),
        ('EQ Mid1 Gain', '-12dB - 0dB - +12dB', PARAM_12DB, [0x11], 0x40),
        ('EQ Mid2 Freq', '200Hz - 800Hz - 6300 Hz', PARAM_TYPE_10, [0X12], 48),
        ('EQ Mid2 Q', '0.5/1.0/2.0/4.0/9.0', {0: '0.5', 1: '1.0', 2: '2.0', 3: '4.0', 4: '9.0'}, [0x13], 1),
        ('EQ Mid2 Gain', '-12dB - 0dB - +12dB', PARAM_12DB, [0x14], 0x40),
        ('EQ High Freq', '4k/8kHz', {0: '4kHz', 1: '8kHz'}, [0x15], 0),
        ('EQ High Gain', '-12dB - 0dB - +12dB', PARAM_12DB, [0x16], 0x40)
    )

    FULL_EFX_TYPE[2] = ('Mic Simulator', [0x00, 0x12])
    FULL_EFX_PARAMETERS[2] = (
        ('Mic Conv', 'Off/On', PARAM_ON_OFF, [0x03], 1),
        ('Input', 'DR-20/Sml.Dy/Hed.Dy/Flat', {0: 'DR-20', 1: 'Sml.Dy', 2: 'Hed.Dy', 3: 'Flat'}, [0x04], 3),
        ('Output', 'Sml.Dy/Voc.Dy/Lrg.Dy/Sml.Cn/Lrg.Cn/Vnt.C/Flat',
         {0: 'Sml.Dy', 1: 'Voc.Dy', 2: 'Lrg.Dy', 3: 'Sml.Cn', 4: 'Lrg.Cn', 5: 'Vnt.C', 6: 'Flat'}, [0x05], 4),
        ('Phase', '+/-', {0: '-', 1: '+'}, [0x06], 1),
        ('Bass Cut Switch', 'Off/On', PARAM_ON_OFF, [0x07], 0),
        ('Bass Cut Freq', '20Hz-2000Hz', PARAM_TYPE_15, [0x08], 0),
        ('Distance Switch', 'Off/On', PARAM_ON_OFF, [0x09], 0),
        ('Prox. Fx', '-12dB - 0dB - +12dB', PARAM_12DB, [0x0A], 0x40),
        ('Distance', '0-127', PARAM_0127, [0x0B], 0),
        ('Limiter Switch', 'Off/On', PARAM_ON_OFF, [0x0C], 0),
        ('Lm Freq', '20Hz - 115Hz - 2000Hz', PARAM_TYPE_15, [0x0D], 40),
        ('Lm Gain', '-60dB - +2dB - +24dB', tools.mergeRanges(range(0x04, 0x59), tools.ulist(-60, +24, 1, 'dB')), [0x0E], 66),
        ('Lm Threshold', '-60db - 0dB', tools.mergeRanges(range(0x04, 0x041), tools.ulist(-60, 0, 1, 'dB')), [0x0F],
         0x40),
        ('Lm Attack', '0 - 20 - 127', PARAM_0127, [0x10], 20),
        ('Lm Release', '0 - 30 - 127', PARAM_0127, [0x11], 30)
    )

    FULL_EFX_TYPE[3] = ('Vocoder', [0x00, 0x13])
    FULL_EFX_PARAMETERS[3] = (
        ('Speech Input', 'Mic1/2/Wave1/2', {0: 'Mic1', 1: 'Mic2', 2: 'Wave1', 3: 'Wave2'}, [0x03], 0x00),
        ('Mode Select', '1 - 3 - 6', tools.mergeRanges(range(0x00, 0x06), tools.ulist(1, 6, 1)), [0x04], 0x02),
        ('Speech Gain', '0 - 100 - 127', PARAM_0127, [0x05], 100),
        ('Speech Cutoff', '250Hz - 630Hz - 800Hz', PARAM_TYPE_9, [0x06], 32),
        ('Speech Mix Level', '0 - 25 -127', PARAM_0127, [0x07], 25),
        ('Response Time', 'Slow/Normal/Fast', {0: 'Slow', 1: 'Normal', 3: 'Fast'}, [0x08], 0x01),
        ('Level', '0 - 127', PARAM_0127, [0x09], 0x7F)
    )

    FULL_EFX_TYPE[4] = ('Vocal Multi', [0x00, 0x14])
    FULL_EFX_PARAMETERS[4] = (
        ('Ns Threshold', '0 - 127', PARAM_0127, [0x03], 0x00),
        ('Lm Threshol', '0 - 127', PARAM_0127, [0x04], 0x7F),
        ('De-esser Level', '0 - 127', PARAM_0127, [0x05], 0x08),
        ('Enhancer Level', '-64 - +5 - +63', tools.mergeRanges(range(0x00, 0x80), tools.ulist(-64, 63, 1)), [0x06], 69),
        ('EQ Low Gain', '-12dB - 0dB - +12dB', PARAM_12DB, [0x07], 0x41),
        ('EQ Mid Freq', '200Hz - 800Hz - 6300 Hz', PARAM_TYPE_10, [0x08], 48),
        ('EQ Mid Q', '0.5/1.0/2.0/4.0/9.0', {0: '0.5', 1: '1.0', 2: '2.0', 3: '4.0', 4: '9.0'}, [0x09], 1),
        ('EQ Mid Gain', '-12dB - +2dB - +12dB', PARAM_12DB, [0x0A], 0x42),
        ('EQ High Gain', '-12dB - -4dB - +12dB', PARAM_12DB, [0x0B], 0x3C),
        ('Ps P.Coarse', '-24  -0 - +12', PARAM_2412, [0x0C], 0x40),
        ('Ps P.Fine', '-100 -48 - +100', PARAM_100100, [0x0D], 40),
        ('Ps Balance', 'D > 0E - D > 42E - D0 <E', BALANCE_VALUES, [0x0E], 28),
        ('Dly Time', '0ms - 260ms - 500ms', PARAM_TYPE_4, [0x0F], 112),
        ('Dly Feedback', '-98% - -10% - +98%', PARAM_9898, [0x10], 59),
        ('Dly Balance', 'D > 0E - D > 22E - D0 < E', BALANCE_VALUES, [0x11], 15),
        ('Cho Rate', '0.05 - 0.65 - 10.0', PARAM_TYPE_6, [0x12], 12),
        ('Cho Depth', '0 - 30 - 127', PARAM_0127, [0x13], 30),
        ('Cho Balance', 'D > 0 E - D=E - D0 < E', BALANCE_VALUES, [0x14], 0)
    )

    FULL_EFX_TYPE[5] = ('Game', [0x00, 0x16])
    FULL_EFX_PARAMETERS[5] = (
        ('Enhancer Level', '-64 - +35 - +63', tools.mergeRanges(range(0x00, 0x80), tools.ulist(-64, 63, 1)), [0x03], 69),
        ('Low Boost Level', '0dB - +8dB - 18dB', PARAM_0_18DB, [0x04], 72),
        # ('Low Boost Freq','', {}, [], ),
        # ('Lm Mix Level','', {}, [], ),
        # ('GtRv Mix Level','', {}, [], ),
        # ('Rv Mix Level','', {}, [], ),
        # ('3D Switch','', {}, [], ),
        # ('3D Range','', {}, [], ),
        # ('Out','', {}, [], ),
        # ('Lm Threshold','', {}, [], ),
        # ('GtRv Pre Dly','', {}, [], ),
        # ('GtRv Time','', {}, [], ),
        # ('Rv Type','', {}, [], ),
        # ('Rv Pre Delay','', {}, [], ),
        # ('Rv Time','', {}, [], ),
        # ('Rv HF Damp','', {}, [], ),
        # ('Rv Low Gain','', {}, [], ),
        # ('Rv High Gain','', {}, [], ),
        # ('Low Gain','', {}, [], ),
        # ('High Gain','', {}, [], ),
        # ('Level','', {}, [], )
    )

    # this is the same as COMPACT_INS_EFX_PARAMETERS[47] defines later (the other way round as described in the documentation)
    FULL_EFX_TYPE[6] = ('Rotary Multi', [0x03, 0x00])
    FULL_EFX_PARAMETERS[6] = (
        ('OD Drive', '0 - 40 - 127', PARAM_0127, [0x03], 40),
        ('OD Sw', 'Off/*On', PARAM_ON_OFF, [0x04], 1),
        ('EQ L Gain', '-12dB - 0dB - +12dB', PARAM_12DB, [0x05], 0x41),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_)
    )
    # this is the same as COMPACT_INS_EFX_PARAMETERS[48] defines later (the other way round as described in the documentation)
    FULL_EFX_TYPE[7] = ('GTR Multi', [0x04, 0x00])
    FULL_EFX_PARAMETERS[7] = (
        ('Cmp Atk', '0 - 8 - 127', PARAM_0127, [0x03], 80),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_)
    )

    # TODO: fill up the missing FULL EFFECTS with their PARAMETERS

    # ***********************************************************
    # COMPACT EFFECTS MODE
    # Let's define the SYS first. They are actually a bit easier.

    # REMEMBER: SYS1 only has DELAY and CHORUS
    #           SYS2 only has DELAY and REVERB
    # THIS MEANS: we must differentiate the two of them somehow. Fuck.

    COMPACT_SYS1_EFX_TYPE = ({1: ('Delay', [0x00, 0x21]),
                              2: ('Chorus', [0x00, 0x22])})
    COMPACT_SYS2_EFX_TYPE = ({1: ('Delay', [0x00, 0x31]),
                              2: ('Reverb', [0x00, 0x32])})

    COMPACT_SYS1_EFX_PARAMETERS = {}

    COMPACT_SYS1_EFX_PARAMETERS[1] = (
        ('Dly Tm LtoL', '0.0ms - 110ms - 360ms', PARAM_TYPE_4_SHORT, [0x03], 97),
        ('Dly Tm LtoR', '0.0ms - 13.0ms - 360ms', PARAM_TYPE_4_SHORT, [0x04], 63),
        ('Dly Tm RtoR', '0.0ms - 100ms - 360ms', PARAM_TYPE_4_SHORT, [0x05], 96),
        ('Dly Tm RtoL', '0.0ms - 8.0ms - 360ms', PARAM_TYPE_4_SHORT, [0x06], 56),
        ('Feedback Level', '-48% - -34% - +48%', tools.mergeRanges(range(0x28, 0x59), tools.ulist(-48, +48, 2, '%')),
         [0x07], 0x36),
        ('Cross Fd Level', '-48% - -34% - +48%', tools.mergeRanges(range(0x28, 0x59), tools.ulist(-48, +48, 2, '%')),
         [0x08], 0x4A),
        ('HF Damp', '315Hz - 8kHz/Bypass', PARAM_TYPE_8, [0x09], 120),
        ('Cross HF Damp', '315Hz - 6.3kHz - 8kHz/Bypass', PARAM_TYPE_8, [0x0A], 104),
        ('Cross Balance', '0-98-127', PARAM_0127, [0x0B], 0x62),
        ('Balance', 'D > 0E - D0 < E', BALANCE_VALUES, [0x0C], 0x7F)
    )

    COMPACT_SYS1_EFX_PARAMETERS[2] = (
        ('Type', 'Mode1 -2 -4', tools.mergeRanges(range(0x00, 0x04), ['Mode1', 'Mode2', 'Mode3', 'Mode4']), [0x03],
         0x01),
        ('Pre Filter', 'Off/LPF/HPF', tools.mergeRanges(range(0x00, 0x03), ['Off', 'LPF', 'HPF']), [0x04], 0x02),
        ('Cutoff', '250Hz - 630Hz - 8000Hz', PARAM_TYPE_9, [0x05], 32),
        ('Pre Dly', '0ms - 100ms', PARAM_TYPE_1, [0x06], 80),
        ('Rate', '0.05 - 0.35 - 10.0', PARAM_TYPE_6, [0x07], 6),
        ('Depth', '0-116-127', PARAM_0127, [0x08], 0x74),
        ('Balance', 'D > 0E - D0 < E', BALANCE_VALUES, [0x09], 0x7F)
    )
    COMPACT_SYS2_EFX_PARAMETERS = {}

    COMPACT_SYS2_EFX_PARAMETERS[1] = (
        ('Dly Tm LtoL', '0.0ms - 110ms - 360ms', PARAM_TYPE_4_SHORT, [0x03], 97),
        ('Dly Tm LtoR', '0.0ms - 13.0ms - 360ms', PARAM_TYPE_4_SHORT, [0x04], 63),
        ('Dly Tm RtoR', '0.0ms - 100ms - 360ms', PARAM_TYPE_4_SHORT, [0x05], 96),
        ('Dly Tm RtoL', '0.0ms - 8.0ms - 360ms', PARAM_TYPE_4_SHORT, [0x06], 56),
        ('Feedback Level', '-48% - -34% - +48%', tools.mergeRanges(range(0x28, 0x59), tools.ulist(-48, +48, 2, '%')),
         [0x07], 0x36),
        ('Cross Fd Level', '-48% - -34% - +48%', tools.mergeRanges(range(0x28, 0x59), tools.ulist(-48, +48, 2, '%')),
         [0x08], 0x4A),
        ('HF Damp', '315Hz - 8kHz/Bypass', PARAM_TYPE_8, [0x09], 120),
        ('Cross HF Damp', '315Hz - 6.3kHz - 8kHz/Bypass', PARAM_TYPE_8, [0x0A], 104),
        ('Cross Balance', '0-98-127', PARAM_0127, [0x0B], 0x62),
        ('Balance', 'D > 0E - D0 < E', BALANCE_VALUES, [0x0C], 0x7F)
    )

    COMPACT_SYS2_EFX_PARAMETERS[2] = (
        ('Type', 'Room1/2/Plate1/2/Hall1/2',
         tools.mergeRanges(range(0x00, 0x06), ['Room1', 'Room2', 'Plate1', 'Plate2', 'Hall1', 'Hall2']), [0x03], 0x05),
        ('Pre Dly', '0ms - 100ms', PARAM_TYPE_1, [0x04], 0x7F),
        ('Reverb Time', '0 - 23 - 127', PARAM_0127, [0x05], 0x17),
        # ('HF Damp'),
        ('Low Gain', '-12dB - +2dB - +12dB', PARAM_12DB, 66),
        ('High Gain', '-12dB - -6dB - +12dB', PARAM_12DB, 58),
        ('Balance', 'D > 0E - D0 < E', BALANCE_VALUES, [0x09], 0x7F)
    )

    # Now we must define the COMPACT INSERTION EFFECT.
    # Remember: they are grouped, as in the documentation

    COMPACT_INS_EFX_GROUP = ({
        # Effects that modify the tone (filter type)
        0: ('Filter', range(0, 5)),
        # Effects that distort the sound (distortion type)
        1: ('Distorsion', range(5, 7)),
        # Effects that modulate the sound (modulation type)
        2: ('Modulation', range(7, 14)),
        # Effects that affect the level (compressor type)
        3: ('Compressor', range(14, 16)),
        # Effects that broaden the sound (chorus type)
        4: ('Chorus', range(16, 21)),
        # Effects that reverberate the sound (delay/reverb type)
        5: ('Delay/Reverb', range(21, 29)),
        # Effects that modify the pitch (pitch shift type)
        6: ('Pitch', range(29, 31)),
        #  Other Effects
        7: ('Other', range(31, 35)),
        # Effects that connect two types of effect in series (series 2)
        8: ('Connect 2 effects (series)', range(35, 47)),
        # Effects that connect three or more types of effecs in series (series 3/series 4/series 5)
        9: ('Connect 3 or more effects (series)', range(47, 56)),
        # Effects that connect two types of effect in parallel (parallel 2)
        10: ('Connect 2 effects (parallel)', range(56, 65))}
    )

    COMPACT_INS_EFX_TYPE = ({
        # Effects that modify the tone (filter type)
        0: ('Noise Suppressor', [0x00, 0x00]),
        1: ('Stereo Eq', [0x01, 0x00]),
        2: ('Spectrum', [0x01, 0x01]),
        3: ('Enhancer', [0x01, 0x02]),
        4: ('Humanizer', [0x01, 0x03]),
        # Effects that distort the sound (distortion type)
        5: ('Overdrive', [0x01, 0x10]),
        6: ('Distorsion', [0x01, 0x11]),
        # Effects that modulate the sound (modulation type)
        7: ('Phaser', [0x01, 0x20]),
        8: ('Auto Wah', [0x01, 0x21]),
        9: ('Rotary', [0x01, 0x22]),
        10: ('Stereo Flanger', [0x01, 0x23]),
        11: ('Step Flanger', [0x01, 0x24]),
        12: ('Tremolo', [0x01, 0x25]),
        13: ('Auto Pan', [0x01, 0x26]),
        # Effects that affect the level (compressor type)
        14: ('Compressor', [0x01, 0x30]),
        15: ('Limiter', [0x01, 0x31]),
        16: ('Hexa Chorus', [0x01, 0x40]),
        # Effects that broaden the sound (chorus type)
        17: ('Tremolo Chorus', [0x01, 0x41]),
        18: ('Stereo Chorus', [0x01, 0x42]),
        19: ('Space D', [0x01, 0x43]),
        20: ('3D Chorus', [0x01, 0x44]),
        # Effects that reverberate the sound (delay/reverb type)
        21: ('Stereo Delay', [0x01, 0x50]),
        22: ('Mod Delay', [0x01, 0x51]),
        23: ('3 Tap Delay', [0x01, 0x52]),
        24: ('4 Tap Delay', [0x01, 0x53]),
        25: ('Tm Ctrl Delay', [0x01, 0x54]),
        26: ('Reverb', [0x01, 0x55]),
        27: ('Gate Reverb', [0x01, 0x56]),
        28: ('3D Delay', [0x01, 0x57]),
        # Effects that modify the pitch (pitch shift type)
        29: ('Pitch Shifter', [0x01, 0x60]),
        30: ('Fb P, Shifter', [0x01, 0x61]),
        #  Other Effects
        31: ('3D Auto', [0x01, 0x70]),
        32: ('3D Manual', [0x01, 0x71]),
        33: ('Lo-Fi 1', [0x01, 0x72]),
        34: ('Lo-Fi 2', [0x01, 0x73]),
        # Effects that connect two types of effect in series (series 2)
        35: ('OD -> Chorus', [0x02, 0x00]),
        36: ('OD -> Flanger', [0x02, 0x01]),
        37: ('OD -> Delay', [0x02, 0x02]),
        38: ('DS -> Chorus', [0x02, 0x03]),
        39: ('DS -> Flanger', [0x02, 0x04]),
        40: ('DS -> Delay', [0x02, 0x05]),
        41: ('EH -> Choru', [0x02, 0x06]),
        42: ('EH -> Flanger', [0x02, 0x07]),
        43: ('EH -> Delay', [0x02, 0x08]),
        44: ('Cho -> Delay', [0x02, 0x09]),
        45: ('FL -> Delay', [0x02, 0x0A]),
        46: ('Cho -> Flanger', [0x02, 0x0B]),
        # Effects that connect three or more types of effecs in series (series 3/series 4/series 5)
        47: ('Rotary Multi', [0x03, 0x00]),
        48: ('GTR Multi 1', [0x04, 0x00]),
        49: ('GTR Multi 2', [0x04, 0x01]),
        50: ('GTR Multi 3', [0x04, 0x02]),
        51: ('Clean Gt Multi 1', [0x04, 0x03]),
        52: ('Clean Gt Multi 2', [0x04, 0x04]),
        53: ('Bass Multi', [0x04, 0x05]),
        54: ('E. Piano Multi', [0x04, 0x06]),
        55: ('Keyboard Multi', [0x05, 0x00]),
        # Effects that connect two types of effect in parallel (parallel 2)
        56: ('Cho / Delay', [0x11, 0x00]),
        57: ('FL / Delay', [0x11, 0x01]),
        58: ('Cho / Flanger', [0x11, 0x02]),
        59: ('OD1 / OD2', [0x11, 0x03]),
        60: ('OD / Rotary', [0x11, 0x04]),
        61: ('OD / Phaser', [0x11, 0x05]),
        62: ('OD / AutoWah', [0x11, 0x06]),
        63: ('PH / Rotary', [0x11, 0x07]),
        64: ('PH / AutoWah', [0x11, 0x08])
    })

    COMPACT_INS_EFX_PARAMETERS = {}

    # Noise suppressor

    COMPACT_INS_EFX_PARAMETERS[0] = (
        ('Noise Suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10),
    )

    # Stereo Eq

    COMPACT_INS_EFX_PARAMETERS[1] = (
        ('Low Freq', '200/400Hz', {0: '200Hz', 1: '400Hz'}, [0x03], 0x00),
        ('Low Gain', '-12dB - +6dB - +12dB', PARAM_12DB, [0x04], 0x46),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise Suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Spectrum

    COMPACT_INS_EFX_PARAMETERS[2] = (
        ('Band 1', '-12dB - +5dB - +12dB', PARAM_12DB, [0x03], 0x45),
        ('Band 2', '-12dB - +2dB - +12dB', PARAM_12DB, [0x04], 0x42),
        ('Band 3', '-12dB - -2dB - +12dB', PARAM_12DB, [0x05], 0x3E),
        ('Band 4', '-12dB - -1dB - +12dB', PARAM_12DB, [0x06], 0x3F),
        ('Band 5', '-12dB - +3dB - +12dB', PARAM_12DB, [0x07], 0x43),
        ('Band 6', '-12dB - +5dB - +12dB', PARAM_12DB, [0x08], 0x45),
        ('Band 7', '-12dB - +6dB - +12dB', PARAM_12DB, [0x09], 0x46),
        ('Band 8', '-12dB - -6dB - +12dB', PARAM_12DB, [0x0A], 0x3A),
        ('Width', '0.5/1.0/*2.0*/4.0/9.0', {0: '0.5', 1: '1.0', 2: '2.0', 3: '4.0', 4: '9.0'}, [0x0B], 2),
        # ('Pan', 'L63 - 0 - R63', PARAM_PAN, [0x15], _default_),
        ('Level', '0 - *127*', PARAM_0127, [0x16], 0x7f),
        ('Noise Suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)

    )

    # TODo: Complete the definitions which lack some parameters...

    # Enhancer

    COMPACT_INS_EFX_PARAMETERS[3] = (
        ('Sens', '0 - 64 - 127', PARAM_0127, [0x03], 64),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_)
    )

    # Humanizer

    COMPACT_INS_EFX_PARAMETERS[4] = (
        ('Drive', '0 - 90 - 127', PARAM_0127, [0x03], 90),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_)
    )

    # Effects that distort the sound (distortion type)

    # Overdrive

    COMPACT_INS_EFX_PARAMETERS[5] = (
        ('Drive', '0 - 90 - 127', PARAM_0127, [0x03], 90),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_)
    )

    # Distorsion

    COMPACT_INS_EFX_PARAMETERS[6] = (
        ('Drive', '0 - 127', PARAM_0127, [0x03], 127),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 70)
    )

    # Effects that modulate the sound (modulation type)

    # Phaser

    COMPACT_INS_EFX_PARAMETERS[7] = (
        # ('Manual', '100Hz - 860Hz - 8kHz', PARAM_TYPE_12 *to be defined!* , [0x03], default),
        ('Rate', '0.05Hz - 0.40Hz - 10.0Hz', PARAM_TYPE_6, [0x04], 7),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Level', '0 - 90 - 127', PARAM_0127, [0x16], 90),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Auto Wah

    COMPACT_INS_EFX_PARAMETERS[8] = (
        ('Fil Type', 'LPF/BOF', {0: 'LPF', 1: 'BOF'}, [0x03], 127),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Rotary

    COMPACT_INS_EFX_PARAMETERS[9] = (
        ('Low Slow', '0.05Hz - 0.35Hz - 10.0Hz', PARAM_TYPE_6, [0x03], 6),
        ('Low Fast', '0.05Hz - 6.40Hz - 10.0H', PARAM_TYPE_6, [0x04], 113),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Stereo Flanger

    COMPACT_INS_EFX_PARAMETERS[10] = (
        ('Pre Filter', 'Off/LPF/HPF', {0: 'Off', 1: 'LPF', 2: 'HPF'}, [0x03], 2),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Step Flanger

    COMPACT_INS_EFX_PARAMETERS[11] = (
        ('Pre Dly', '0.0ms - 1.0ms - 100ms', PARAM_TYPE_1, [0x03], 2),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Tremolo

    COMPACT_INS_EFX_PARAMETERS[12] = (
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Mod Rate', '0.05Hz - 6.00Hz - 10.0Hz', PARAM_TYPE_6, [0x04], 109),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # Auto Pan

    COMPACT_INS_EFX_PARAMETERS[13] = (
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Mod Depth', '0 - 60 - 127', PARAM_0127, [0x05], 60),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        # ('Name', 'description', mergedRange, [0xXX], _default_),
        ('Noise suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    #
    # TODO: Fill up the filter definitions
    #

    # rotary multi

    COMPACT_INS_EFX_PARAMETERS[47] = FULL_EFX_PARAMETERS[6]

    #
    # TODO: Fill up the filter definitions
    #

    COMPACT_INS_EFX_PARAMETERS[64] = (
        # ('PH Man', 'description', mergedRange, [0xXX], _default_),
        # ('PH Rate', 'description', mergedRange, [0xXX], _default_),
        ('PH Depth', '0 - 70 - 127', PARAM_0127, [0x05], 70),
        ('PH Reso', '0 - *127*', PARAM_0127, [0x06], 127),
        ('PH Mix', '0 - *127*', PARAM_0127, [0x07], 127),
        # ('PH Pan', 'description', mergedRange, [0xXX], _default_),
        ('PH Level', '0 - 90 - 127', PARAM_0127, [0x13], 90),
        # ('AW Filter', 'description', mergedRange, [0xXX], _default_),
        ('AW Sens', '0 - 40 - 127', PARAM_0127, [0x09], 40),
        ('AW Man', '0 - 10 - 127', PARAM_0127, [0x0A], 10),
        ('AW Peak', '0 - 20 - 127', PARAM_0127, [0x0B], 20),
        ('AW Rate', '0.05Hz - 2.00Hz - 10.0Hz', PARAM_TYPE_6, [0x0C], 39),
        ('AW Depth', '0 - 90 - 127', PARAM_0127, [0x0D], 90),
        ('AW Pol', 'Down/*Up*', PARAM_UP_DOWN, [0x0E], 1),
        # ('AW Pan', 'L63 - 0 - R63', PARAM_PAN, [0x14], 0),
        ('AW Level', '0 - *127*', PARAM_0127, [0x15], 0x7f),
        ('Level', '0 - *127*', PARAM_0127, [0x16], 0x7f),
        ('Noise Suppressor', '0 - 10 - 127', PARAM_0127, [0x25], 10)
    )

    # The VT Effect Mode

    VT_EFFECT = ('VT Effect', [0x00, 0x01])

    VT_EFFECT_PARAMETERS = (
        ('Direct Level', '0 - 127', PARAM_0127, [0x03], 0x00),
    )

    # End of exclusive (EOX)
    EOX = [0xF7]

# More documentation (*stolen* from michel minn's web page http://michaelminn.com/linux/mmusbaudio/)

# A listing of the UA-100 SYSEX messages (derived from Roland's documentation) is given below:
#
# Data Transmission
#
# 	F0: Start SysEx
# 	41: Manufacturer (Roland)
# 	10: Device ID
# 	00: Model ID 1
# 	11: Model ID 2
# 	12: Command (Transmit data)
# 	aa: Address
# 	aa
#     aa:
#     aa:
# 	dd: Data
# 	dd:
#     ck: checksum = 128 - ((sum of address & data bytes) & 0x3f);
# 	f7: end of SysEx
#
#     Examples: F0 41 10 00 11 12   00 40 02 00   01 00  3D F7
#               (select Stereo-EQ as Mic2 insertion effect)
#
#               f0 41 10 00 11 12   00 40 50 03   64     09 f7
#               (master level of 64)
#
# In URB buffer, the message is split into 3 byte chunks with
# a 24h is placed before every chunk except for a  25h before the
# final chunk.
#
#     24 f0 41 10    24 00 11 12   24 00 40 02   24 00 01 00   25 f7
#
# Note that for messages with multiple data bytes (length > 1),
# the first data byte (usually the significant one) comes first.
#
#
# ------------------------------------------------------------------------
# 00 40 00 00  01      PC Mode (VT Effect Mode) - sent by UA-100?
# 00 40 00 00  03      PC Mode (Compact Effect Mode)
# 00 40 00 00  04      PC Mode (Full Effect Mode)
# 00 40 00 00  05      VT Mode
# 00 40 00 00  06      Vocal Mode
# 00 40 00 00  07      Guitar Mode
# 00 40 00 00  08      GAME Mode
# 00 40 00 00  09      BYPASS Mode
#
# 00 40 00 01  0x      Copyright (0 off, 1 on)
#
#     n = 1 (line, mic1, mic1+2), 2 (mic2), 3 (wave1), 4 (wave2), 5 (sys effect 1), 6 (sys effect 2)
#
# 00 40 0n 00  xx 00   Effect type (listed below)
# 00 40 0n 03  xx      Effect parameter 1
# 00 40 0n 04  xx      Effect parameter 2
# 00 40 0n 05  xx      Effect parameter 3
# 00 40 0n 06  xx      Effect parameter 4
# 00 40 0n 07  xx      Effect parameter 5
# 00 40 0n 08  xx      Effect parameter 6
# 00 40 0n 09  xx      Effect parameter 7
# 00 40 0n 0A  xx      Effect parameter 8
# 00 40 0n 0B  xx      Effect parameter 9
# 00 40 0n 0C  xx      Effect parameter 10
# 00 40 0n 0D  xx      Effect parameter 11
# 00 40 0n 0E  xx      Effect parameter 12
# 00 40 0n 0F  xx      Effect parameter 13
# 00 40 0n 10  xx      Effect parameter 14
# 00 40 0n 11  xx      Effect parameter 15
# 00 40 0n 12  xx      Effect parameter 16
# 00 40 0n 13  xx      Effect parameter 17
# 00 40 0n 14  xx      Effect parameter 18
# 00 40 0n 15  xx      Effect parameter 19
# 00 40 0n 16  xx      Effect parameter 20
# 00 40 0n 17  xx      Effect parameter 21
# 00 40 0n 18  xx      Effect parameter 22
# 00 40 0n 19  xx      Effect parameter 23
# 00 40 0n 1A  xx      Effect parameter 24
# 00 40 0n 1B  xx      Effect parameter 25
# 00 40 0n 1C  xx      Effect parameter 26
# 00 40 0n 1D  xx      Effect parameter 27
# 00 40 0n 1E  xx      Effect parameter 28
# 00 40 0n 1F  xx      Effect parameter 29
# 00 40 0n 20  xx      Effect parameter 30
# 00 40 0n 21  xx      Effect parameter 31
# 00 40 0n 22  xx      Effect parameter 32
# 00 40 0n 23  xx      Effect parameter 33
# 00 40 0n 24  xx      Effect parameter 34
# 00 40 0n 25  xx      Effect parameter 35
# 00 40 0n 26  xx      Effect parameter 36
# 00 40 0n 27  xx      Effect parameter 37
# 00 40 0n 28  xx      Effect parameter 38
# 00 40 0n 29  xx      Effect parameter 39
# 00 40 0n 2A  xx      Effect parameter 40
#
# 00 40 10 00  00      Mic input mode
# 00 40 10 00  01      Line input mode
# 00 40 10 00  02      MIC1+MIC2 Mode (not in VT mode)
#
# 00 40 10 01  xx      Input pan 1 (0 - 40 - 7f)
# 00 40 10 02  xx      Input pan 2 (0 - 40 - 7f)
# 00 40 10 03  0x      Monitor (0 off, 1 on)
#
#     n = 1 (line, mic1, mic1+2), 2 (mic2), 3 (wave1), 4 (wave2), 5 (sys effect 1), 6 (sys effect 2)
#
# 00 40 1n 00  xx      Effect 1 send level (full/compact effect mode)
# 00 40 1n 02  xx      Effect 2 send level (full/compact effect mode)
# 00 40 1n 04  xx      Submaster send level (not in VT mode)
# 00 40 1n 05  xx      Fader level (not in VT mode)
# 00 40 1n 06  0x      Mute (0 off, 1 on)
# 00 40 1n 07  0x      Solo (0 off, 1 on)
#
# 00 40 40 00  01      VT effect mode
# 00 40 40 00  03      Compact effect mode (1 insertion + 2 system effects)
# 00 40 40 00  04      Full effect mode (1 effect)
# 00 40 40 01  0x      Line/Mic1/Mic1+2 insertion effect on/off (0 off, 1 on)
# 00 40 40 02  0x      Mic2 insertion effect on/off (0 off, 1 on)
# 00 40 40 03  0x      Wave1 insertion effect on/off (0 off, 1 on)
# 00 40 40 04  0x      Wave2 insertion effect on/off (0 off, 1 on)
# 00 40 40 05  0x      System effect 1 on/off (0 off, 1 on)
# 00 40 40 06  0x      System effect 2 on/off (0 off, 1 on)
#
# 00 40 40 07  xx      Effect 1 master return
# 00 40 40 08  xx      Effect 1 submaster return
# 00 40 40 09  xx      Effect 2 master return
# 00 40 40 0A  xx      Effect 2 submaster return
#
# 00 40 40 0B  0x      Vocal Transform 1 receive channel (0 - F)
# 00 40 40 0C  0x      Vocal Transform 1 note enabled (0 off, 1 on)
# 00 40 40 0D  0x      Vocal Transform 1 bend enabled (0 off, 1 on)
# 00 40 40 0E  0x      Vocal Transform 2 receive channel (0 - F)
# 00 40 40 0F  0x      Vocal Transform 2 note enabled (0 off, 1 on)
# 00 40 40 10  0x      Vocal Transform 2 bend enabled (0 off, 1 on)
#
# 00 40 50 00  0x      Record source (Mixer: 0 line/mic, 1 mic2, 2 wave1, 3 wave2,
# 				    4-7 ch 1-4, 8 submaster, 9 master)
#                                    (VT: 0 line/mic, 1 mic3, 2 wave1, 3 wave2, 4 VT-out, 5 master)
# 00 40 50 01  0x      Output (see record source)
# 00 40 50 02  xx      Recording level
# 00 40 50 03  xx      Master level
#
#
#       n  = 0 (Voice Transformer), 1 (Vocal), 2 (Guitar), 3 (Game) (NOT FOR PC MODE)
#
# 00 40 6n 00  xx      Preset effect parameter 1 (0 - 39)
# 00 40 6n 01  xx      Preset effect parameter 2 (0 - 39)
# 00 40 6n 02  xx      Preset effect parameter 3 (0 - 39)
# 00 40 6n 03  xx      Preset effect parameter 4 (0 - 39)
#
# 00 40 6n 04  xx      Preset effect default Value 1 (0 - 127)
# 00 40 6n 05  xx      Preset effect default Value 2 (0 - 127)
# 00 40 6n 06  xx      Preset effect default Value 3 (0 - 127)
# 00 40 6n 07  xx      Preset effect default Value 4 (0 - 127)
# 00 40 6n 08  xx      Preset effect default Value 5 (0 - 127)
# 00 40 6n 09  xx      Preset effect default Value 6 (0 - 127)
# 00 40 6n 0A  xx      Preset effect default Value 7 (0 - 127)
# 00 40 6n 0B  xx      Preset effect default Value 8 (0 - 127)
# 00 40 6n 0C  xx      Preset effect default Value 9 (0 - 127)
# 00 40 6n 0D  xx      Preset effect default Value 10 (0 - 127)
# 00 40 6n 0E  xx      Preset effect default Value 11 (0 - 127)
# 00 40 6n 0F  xx      Preset effect default Value 12 (0 - 127)
#
# 00 40 6n 10  xx      Preset effect default Value 13 (0 - 127)
# 00 40 6n 11  xx      Preset effect default Value 14 (0 - 127)
# 00 40 6n 12  xx      Preset effect default Value 15 (0 - 127)
# 00 40 6n 13  xx      Preset effect default Value 16 (0 - 127)
# 00 40 6n 14  xx      Preset effect default Value 17 (0 - 127)
# 00 40 6n 15  xx      Preset effect default Value 18 (0 - 127)
# 00 40 6n 16  xx      Preset effect default Value 19 (0 - 127)
# 00 40 6n 17  xx      Preset effect default Value 20 (0 - 127)
# 00 40 6n 18  xx      Preset effect default Value 21 (0 - 127)
# 00 40 6n 19  xx      Preset effect default Value 22 (0 - 127)
# 00 40 6n 1A  xx      Preset effect default Value 23 (0 - 127)
# 00 40 6n 1B  xx      Preset effect default Value 24 (0 - 127)
# 00 40 6n 1C  xx      Preset effect default Value 25 (0 - 127)
# 00 40 6n 1D  xx      Preset effect default Value 26 (0 - 127)
# 00 40 6n 1E  xx      Preset effect default Value 27 (0 - 127)
# 00 40 6n 1F  xx      Preset effect default Value 28 (0 - 127)
# 00 40 6n 20  xx      Preset effect default Value 29 (0 - 127)
# 00 40 6n 21  xx      Preset effect default Value 30 (0 - 127)
# 00 40 6n 22  xx      Preset effect default Value 31 (0 - 127)
# 00 40 6n 23  xx      Preset effect default Value 32 (0 - 127)
# 00 40 6n 24  xx      Preset effect default Value 33 (0 - 127)
# 00 40 6n 25  xx      Preset effect default Value 34 (0 - 127)
# 00 40 6n 26  xx      Preset effect default Value 35 (0 - 127)
# 00 40 6n 27  xx      Preset effect default Value 36 (0 - 127)
# 00 40 6n 28  xx      Preset effect default Value 37 (0 - 127)
# 00 40 6n 29  xx      Preset effect default Value 38 (0 - 127)
# 00 40 6n 2A  xx      Preset effect default Value 39 (0 - 127)
# 00 40 6n 2B  xx      Preset effect default Value 40 (0 - 127)
#
# 00 40 60 7F  00      Preset effect parameter write
#
#
# ---------------------------------------------------------
#
# System Effect 1
#
# 	0021: Delay
# 	0022: Chorus
#
# System Effect 2
#
# 	0031: Delay
# 	0032: Reverb
#
# Full Effects
# 	0011: High Quality Reverb
# 	0012: Mic Simulator
# 	0013: Vocoder
# 	0014: Vocal Multi
# 	0016: Game with 3D Reverb
# 	0300: Rotary Multi (same parameters as insertion #47)
# 	0400: Guitar Multi 1 (same parameters as insertion #48)
# 	0401: Guitar Multi 2 (same parameters as insertion #49)
# 	0402: Guitar Multi 3 (same parameters as insertion #50)
# 	0403: Clean Guitar Multi 1 (same parameters as insertion #51)
# 	0404: Clean Guitar Multi 2 (same parameters as insertion #52)
# 	0405: Bass Multi (same parameters as insertion #53)
# 	0406: Electric Piano Multi (same parameters as insertion #54)
# 	0500: Keyboard Multi ( (same parameters as insertion #55)
#
# Insertion Effects
# 	0000: (00) Noise Suppressor
# 	0100: (01) Stereo Equalizer
# 	0101: (02) Spectrum
# 	0102: (03) Enhancer
# 	0103: (04) Humanizer
# 	0110: (05) Overdrive
# 	0111: (06) Distortion
# 	0120: (07) Phaser
# 	0121: (08) Auto Wah
# 	0122: (09) Rotary
# 	0123: (10) Stereo Flanger
# 	0124: (11) Step Flanger
# 	0125: (12) Tremolo
# 	0126: (13) Auto Pan
# 	0130: (14) Compressor
# 	0131: (15) Limiter
# 	0140: (16) Hexa Chorus
# 	0141: (17) Tremolo Chorus
# 	0142: (18) Stereo Chorus
# 	0143: (19) Space D
# 	0144: (20) 3D Chorus
# 	0150: (21) Stereo Delay
# 	0151: (22) Modulation Delay
# 	0152: (23) 3 Tap Delay
# 	0153: (24) 4 Tap Delay
# 	0154: (25) Time Control Delay
# 	0155: (26) Reverb
# 	0156: (27) Gate Reverb
# 	0157: (28) 3D Delay
# 	0160: (29) 2-voice Pitch Shifter
# 	0161: (30) Feedback Pitch Shifter
# 	0170: (31) 3D Auto
# 	0171: (32) 3D Manual
# 	0172: (33) Lo-Fi 1
# 	0173: (34) Lo-Fi 2
# 	0200: (35) Overdrive/Chorus
# 	0201: (36) Overdrive/Flanger
# 	0202: (37) Overdrive/Delay
# 	0203: (38) Distortion/Chorus
# 	0204: (39) Distortion/Flanger
# 	0205: (40) Distortion/Delay
# 	0206: (41) Enhancer/Chorus
# 	0207: (42) Enhancer/Flanger
# 	0208: (43) Enhancer/Delay
# 	0209: (44) Chorus/Delay
# 	020a: (45) Flanger/Delay
# 	020b: (46) Chorus/Flanger
# 	0300: (47) Rotary Multi
# 	0400: (48) Guitar Multi1
# 	0401: (49) Guitar Multi2
# 	0402: (50) Guitar Multi3
# 	0403: (51) Clean Guitar Multi1
# 	0404: (52) Clean Guitar Multi2
# 	0405: (53) Bass Multi
# 	0406: (54) E.Piano Multi
# 	0500: (55) Keyboard Multi
# 	1100: (56) Chorus/Delay
# 	1101: (57) Flanger/Delay
# 	1102: (58) Chorus/Flanger
# 	1103: (59) Overdrive/Distortion1,2
# 	1104: (60) Overdrive/Distortion/Rotary
# 	1105: (61) Overdrive/Distortion/Phaser
# 	1106: (62) Overdrive/Distortion/Auto-wah
# 	1107: (63) Phaser/Rotary
# 	1108: (64) Phaser/Auto-wah


if (DEBUG_MODE):
    print('Done!')


class MidiDevsDialog(QtGui.QDialog):
    '''
    First of all, we ask for the right device to use. In fact, we know which one... and thus, we can easily guess.
    '''

    def __init__(self, parent=None):
        super(MidiDevsDialog, self).__init__(parent)

        self.ui = PyQt4.uic.loadUi('ui/device_sel.ui', self)

        if (DEBUG_MODE):
            # print('DEFAULT_UA100CONTROL= ', DEFAULT_UA100CONTROL)
            print('midiDevs=', midiDevs)
        for i in range(0, len(midiDevs)):
            self.outputDevicesList.addItem(str(midiDevs[i]), i)

        # update the device information when selecting the devices in the combobox
        self.outputDevicesList.currentIndexChanged.connect(self.updateDeviceLabels)

        # call the setMidiDevice custom slot to tell everyone which one is the selected device (output)
        self.outputDevicesList.currentIndexChanged.connect(self.setMidiDevice)
        self.outputDevicesList.setCurrentIndex(-1)
        # send true if OK is clicked
        self.dialogOK.clicked.connect(self.accept)

        # send false if Quit is clicked (and close application)
        self.dialogQuit.clicked.connect(self.reject)

        # set the current index to the guessed right outpud midi device for the UA100 controller
        if (REAL_UA_MODE):
            self.outputDevicesList.setCurrentIndex(DEFAULT_UA100CONTROL)
            pass

    def updateDeviceLabels(self, index):
        '''
        I should be an easy task to update label according to a combo box...
        '''
        # self.midiApiText.setText(str(midiDevs[index][0]))
        # self.deviceNameText.setText(str(midiDevs[index][1]))
        # if (midiDevs[index][2] == 1 and midiDevs[index][3] == 0):
        #     self.deviceIOText.setText('INPUT')
        # elif (midiDevs[index][2] == 0 and midiDevs[index][3] == 1):
        #     self.deviceIOText.setText('OUTPUT')
        # else:
        #     self.deviceIOText.setText('N/A')
        # 
        if (index == DEFAULT_UA100CONTROL):
            self.reccomendedLabel.setText('RECCOMENDED!\r\nYou don\'t really want to change it!')
            self.reccomendedLabel.setStyleSheet('color: red; font-style: bold')
        else:
            self.reccomendedLabel.setText('')
            #
            # if (DEBUG_MODE == 1):
            #     print(midiDevs[index][2], midiDevs[index][3])

    def setMidiDevice(self, index):
        '''
        This slot should set the midi device selected in the combo box of the starting dialog
        '''
        global UA100CONTROL

        UA100CONTROL = index
        if (DEBUG_MODE == 1):
            print('Index = ', index)
            if not (index == -1):
                print('UA100CONTROL = ', midiDevs[UA100CONTROL])
            else:
                print('UA100CONTROL is not yet set!')


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # load the ui
        self.ui = PyQt4.uic.loadUi('ui/main.ui', self)

        # inizialize the dicts containing the definitions for the 3 effect dialog types
        self.fullEffects = {}
        self.compactEffectsSys = {}
        self.compactEffectsIns = {}

        # setup menus
        self.actionReset_Mixer.triggered.connect(self.resetMixer)
        self.actionQuit.triggered.connect(QtGui.qApp.quit)

        # *************** MIC1 *********************

        self.Mic1.setProperty("channel", CC_MIC1_CH)

        # Setting Up the Mic1 Fader
        self.Mic1Fader.valueChanged.connect(self.Mic1Lcd.display)
        self.Mic1Fader.valueChanged.connect(functools.partial(self.valueChange, CC_MIC1_CH, CC_MAIN_FADER_PAR))
        self.Mic1Fader.setProperty("parameter", CC_MAIN_FADER_PAR)

        # Setting Up the Mic1 Pan Dial
        self.Mic1Pan.valueChanged.connect(self.Mic1PanLcd.display)
        self.Mic1Pan.valueChanged.connect(functools.partial(self.valueChange, CC_MIC1_CH, CC_PAN_PAR))
        self.Mic1Pan.setProperty("parameter", CC_PAN_PAR)
        # center...
        self.Mic1Pan.setProperty("value", CC_PAN_MIDDLE)

        # I also need Mic1Pan2, a "copy" of Mic2 for the Mic1+Mic2 mode:
        self.Mic1Pan2.valueChanged.connect(self.Mic1PanLcd2.display)
        self.Mic1Pan2.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_PAN_PAR))
        self.Mic1Pan2.setProperty("parameter", CC_PAN_PAR)
        self.Mic1Pan2.setProperty("value", CC_PAN_MIDDLE)

        # Setting up Ins1&2
        self.Mic1Ins1.valueChanged.connect(functools.partial(self.valueChange, CC_MIC1_CH, CC_SEND1_PAR))
        self.Mic1Ins2.valueChanged.connect(functools.partial(self.valueChange, CC_MIC1_CH, CC_SEND2_PAR))

        # Setting Up the Mic1 Solo Button ** THERE CAN ONLY BE ONE "SOLO" CHECKED, THUS... **
        self.Mic1Solo.toggled.connect(self.uniqueSolos)

        self.Mic1Mute.toggled.connect(functools.partial(self.valueChange, CC_MIC1_CH, CC_MUTE_PAR))

        # Setting Up the SubFader
        self.Mic1SubFader.valueChanged.connect(self.Mic1SubLcd.display)
        self.Mic1SubFader.valueChanged.connect(functools.partial(self.valueChange, CC_MIC1_CH, CC_SUB_FADER_PAR))

        # hiding the subs...
        self.Mic1SubFader.hide()
        self.Mic1SubLcd.hide()

        # *************** MIC2 *********************

        self.Mic2.setProperty("channel", CC_MIC2_CH)

        # Setting Up the Mic2 Fader
        self.Mic2Fader.valueChanged.connect(self.Mic2Lcd.display)
        self.Mic2Fader.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_MAIN_FADER_PAR))
        self.Mic2Fader.setProperty("parameter", CC_MAIN_FADER_PAR)

        # Setting Up the Mic2 Pan Dial
        self.Mic2Pan.valueChanged.connect(self.Mic2PanLcd.display)
        self.Mic2Pan.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_PAN_PAR))
        self.Mic2Pan.setProperty("parameter", CC_PAN_PAR)
        # center...
        self.Mic2Pan.setProperty("value", CC_PAN_MIDDLE)

        # I also need Mic1Pan2, a "copy" of Mic2 for the Mic1+Mic2 mode:
        self.Mic1Pan2.valueChanged.connect(self.Mic1PanLcd2.display)
        self.Mic1Pan2.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_PAN_PAR))
        self.Mic1Pan2.setProperty("parameter", CC_PAN_PAR)

        # Setting up Ins1&2
        self.Mic2Ins1.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_SEND1_PAR))
        self.Mic2Ins2.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_SEND2_PAR))

        # Setting Up the Mic2 Solo Button ** THEY CAN BE ONLY ONE SOLO CHECKED, THUS... **
        self.Mic2Solo.toggled.connect(self.uniqueSolos)

        self.Mic2Mute.toggled.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_MUTE_PAR))

        # hiding the subs...
        self.Mic2SubFader.hide()
        self.Mic2SubLcd.hide()

        # Setting Up the SubFader
        self.Mic2SubFader.valueChanged.connect(self.Mic2SubLcd.display)
        self.Mic2SubFader.valueChanged.connect(functools.partial(self.valueChange, CC_MIC2_CH, CC_SUB_FADER_PAR))

        # *************** WAVE1 *********************

        self.Wave1.setProperty("channel", CC_WAVE1_CH)

        # Setting up the Wave1 Fader
        self.Wave1Fader.valueChanged.connect(self.Wave1Lcd.display)
        self.Wave1Fader.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE1_CH, CC_MAIN_FADER_PAR))
        self.Wave1Fader.setProperty("parameter", CC_MAIN_FADER_PAR)

        # Setting up Ins1&2
        self.Wave1Ins1.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE1_CH, CC_SEND1_PAR))
        self.Wave1Ins2.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE1_CH, CC_SEND2_PAR))

        # Setting Up the Wave1 Solo Button ** THEY CAN BE ONLY ONE SOLO CHECKED, THUS... **
        self.Wave1Solo.toggled.connect(self.uniqueSolos)
        self.Wave1Mute.toggled.connect(functools.partial(self.valueChange, CC_WAVE1_CH, CC_MUTE_PAR))

        # Setting Up the SubFader
        self.Wave1SubFader.valueChanged.connect(self.Wave1SubLcd.display)
        self.Wave1SubFader.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE1_CH, CC_SUB_FADER_PAR))

        # hiding the subs...
        self.Wave1SubFader.hide()
        self.Wave1SubLcd.hide()

        # *************** WAVE2 *********************

        self.Wave2.setProperty("channel", CC_WAVE2_CH)

        # Setting up the Wave1 Fader
        self.Wave2Fader.valueChanged.connect(self.Wave2Lcd.display)
        self.Wave2Fader.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE2_CH, CC_MAIN_FADER_PAR))
        self.Wave2Fader.setProperty("parameter", CC_MAIN_FADER_PAR)

        # Setting up Ins1&2
        self.Wave2Ins1.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE2_CH, CC_SEND1_PAR))
        self.Wave2Ins2.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE2_CH, CC_SEND2_PAR))

        # Setting Up the Wave2 Solo Button ** THEY CAN BE ONLY ONE SOLO CHECKED, THUS... **
        self.Wave2Solo.toggled.connect(self.uniqueSolos)

        self.Wave2Mute.toggled.connect(functools.partial(self.valueChange, CC_WAVE2_CH, CC_MUTE_PAR))

        # Setting Up the SubFader
        self.Wave2SubFader.valueChanged.connect(self.Wave2SubLcd.display)
        self.Wave2SubFader.valueChanged.connect(functools.partial(self.valueChange, CC_WAVE2_CH, CC_SUB_FADER_PAR))

        # hiding the subs...
        self.Wave2SubFader.hide()
        self.Wave2SubLcd.hide()

        # *************** MASTERLINE *********************

        self.MasterLineFader.setProperty("channel", CC_LINE_MASTER_CH)

        # Setting Up the MasterLine Fader
        self.MasterLineFader.valueChanged.connect(self.MasterLineLcd.display)
        self.MasterLineFader.valueChanged.connect(
            functools.partial(self.valueChange, CC_LINE_MASTER_CH, CC_MAIN_FADER_PAR))
        self.MasterLineFader.setProperty("parameter", CC_MAIN_FADER_PAR)

        # *************** WAVE (REC) **********************

        # Setting up the Wave (Rec) Fader
        self.WaveRecFader.valueChanged.connect(self.WaveRecLcd.display)
        self.WaveRecFader.valueChanged.connect(functools.partial(self.valueChange, CC_WAVEREC_CH, CC_MAIN_FADER_PAR))

        # *************** SYSEFF **************************

        # Return
        self.SysEffRet1.valueChanged.connect(functools.partial(self.valueChange, CC_SYSRET_CH, CC_SEND1_PAR))
        self.SysEffRet2.valueChanged.connect(functools.partial(self.valueChange, CC_SYSRET_CH, CC_SEND2_PAR))
        # Sub
        self.SysEffSub1.valueChanged.connect(functools.partial(self.valueChange, CC_SYSSUB_CH, CC_SEND1_PAR))
        self.SysEffSub2.valueChanged.connect(functools.partial(self.valueChange, CC_SYSSUB_CH, CC_SEND2_PAR))

        # SUB BUTTON

        self.SubButton.toggled.connect(self.showHideSub)

        # hiding more...
        self.SysEffSub1.hide()
        self.SysEffSub2.hide()
        self.SysEffSubLabel.hide()

        # Setting Up Mixer Output Sources for Master
        self.OutputMasterSourceSelect.currentIndexChanged.connect(
            functools.partial(self.valueChange, CC_LINE_MASTER_CH, CC_SELECTOR_PAR))
        if (MIXER_OUTPUT_MODE):
            for key in MASTER_SELECT_MIXERMODE.keys():
                self.OutputMasterSourceSelect.addItem(MASTER_SELECT_MIXERMODE[key])
            self.OutputMasterSourceSelect.setCurrentIndex(0x09)

        # Setting Up Mixer Output Sources for Wave(Rec)
        self.OutputWaveRecSourceSelect.currentIndexChanged.connect(
            functools.partial(self.valueChange, CC_WAVEREC_CH, CC_SELECTOR_PAR))
        if (MIXER_OUTPUT_MODE):
            for key in WAVE_SELECT_MIXERMODE.keys():
                self.OutputWaveRecSourceSelect.addItem(WAVE_SELECT_MIXERMODE[key])
            self.OutputWaveRecSourceSelect.setCurrentIndex(0x09)

        if (MIXER_OUTPUT_MODE):
            for key in MIXER_EFFECT_MODE_PAR.keys():
                self.uiEffectModeSelector.addItem(MIXER_EFFECT_MODE_PAR[key], key)
            self.uiEffectModeSelector.setCurrentIndex(-1)
        self.uiEffectModeSelector.currentIndexChanged.connect(self.setEffectMode)
        self.EffMic1Button.setProperty('HEX', [0x01])
        self.EffMic1Button.clicked.connect(self.effectSelection)
        self.EffMic2Button.setProperty('HEX', [0x02])
        self.EffMic2Button.clicked.connect(self.effectSelection)
        self.EffWave1Button.setProperty('HEX', [0x03])
        self.EffWave1Button.clicked.connect(self.effectSelection)
        self.EffWave2Button.setProperty('HEX', [0x04])
        self.EffWave2Button.clicked.connect(self.effectSelection)
        self.EffSys1Button.setProperty('HEX', [0x05])
        self.EffSys1Button.clicked.connect(self.effectSelection)
        self.EffSys2Button.setProperty('HEX', [0x06])
        self.EffSys2Button.clicked.connect(self.effectSelection)

        if (REAL_UA_MODE):
            self.__setInitMixerLevels__()
            pass

        self.uiInputModeButton.setProperty('state', 0x00)
        self.Mic1Pan2.hide()
        self.Mic1PanLcd2.hide()
        self.uiInputModeButton.clicked.connect(self.setInputMode)

        # Setting up the"Easy Settings" Box.
        #
        # by now, just my "Sax Mode" button will work.

        # Setting up "Sax Mode"
        #
        # Actually, as I use Audacity to listen and record my "performances" on the Saxophone, this button will
        # just switch MAIN output source to "Wave1" (the audacity output) and the Wave (REC) output to "Mic1/..."

        self.SaxModeButton.clicked.connect(self.saxMode)

    def saxMode(self):
        '''
        This should just switch MAIN output source to "Wave1" (the audacity output) and the Wave (REC) output to "Mic1/..."
        '''
        self.OutputMasterSourceSelect.setCurrentIndex(0x02)
        self.OutputWaveRecSourceSelect.setCurrentIndex(0x00)
        pass

    def setInputMode(self):
        '''
        
        The MIC1-GUITAR/LINE/MIC1+MIC2 toggler
        
        need a tree way button...
        MIC/LINE 21 (15H)       0: Mic Mode, 1: Line Mode, 2: MIC1+MIC2 Mod
        
        '''

        if self.sender().property('state') == 0x00:
            # Going to line mode...
            self.sender().setProperty('state', 0x01)
            self.Mic1.setTitle('Line')
            self.uiInputModeLabel.setText('Line')
            self.Mic2.hide()
            self.Mic1Pan2.hide()
            self.Mic1PanLcd2.hide()
        elif self.sender().property('state') == 0x01:
            # going to Mic1 + Mic 2 Mode
            self.sender().setProperty('state', 0x02)
            self.Mic1.setTitle('Mic1/GTR+Mic2')
            self.uiInputModeLabel.setText('Mic1\n+Mic2')
            self.Mic2.setEnabled(False)
            self.Mic2.hide()
            self.Mic1Pan2.show()
            self.Mic1PanLcd2.show()
            # let's expand a bit...
            self.Mic1.setProperty
        elif self.sender().property('state') == 0x02:
            # Back to
            self.sender().setProperty('state', 0x00)
            self.Mic1.setTitle('Mic1/Guitar')
            self.uiInputModeLabel.setText('Mic/GTR')
            self.Mic2.setEnabled(True)
            self.Mic1Pan2.hide()
            self.Mic1PanLcd2.hide()
            self.Mic2.show()

        if (REAL_UA_MODE):
            p = mido.Parser()
            p.feed([CC_MIC1_CH, CC_MICLINESELECTOR_PAR, self.sender().property('state').toPyObject()])
            shortMsg = p.get_message()
            if (DEBUG_MODE):
                print('Message to be sent ', shortMsg)
            pmout.send(shortMsg)

        if (DEBUG_MODE):
            print(CC_MIC1_CH, ' ', CC_MICLINESELECTOR_PAR, ' ', self.sender().property('state').toPyObject())

    def setEffectMode(self, value):
        '''
        ???
        '''

        global MixerEffectMode
        valueToList = [sorted(MIXER_EFFECT_MODE_PAR.keys())[value]]
        send_DT1(MIXER_EFFECT_CONTROL + MIXER_EFFECT_MODE + valueToList)
        MixerEffectMode = sorted(MIXER_EFFECT_MODE_PAR.keys())[value]

    def effectSelection(self):
        global MixerEffectMode
        # if (DEBUG_MODE):
        #    print(self.sender().objectName())
        if (MixerEffectMode == 0x04):
            # if not (self.sender() in self.fullEffects):
            #    self.fullEffects[self.sender()] = FullEffectsDialog(self)
            # self.fullEffects[self.sender()].show()
            if (self.fullEffects):
                # self.fullEffects.uiToggleEffect.setChecked(0)
                self.fullEffects.close()
                self.fullEffects = FullEffectsDialog(self)
                # self.fullEffects.uiToggleEffect.setChecked(1)
            else:
                self.fullEffects = FullEffectsDialog(self)
            self.fullEffects.show()
        if (MixerEffectMode == 0x03):
            # We can have only one effect for the mic1, mic2, wave1 and wave2
            # and both of sys1 and sys2
            if (self.sender().property('HEX') in ([0x05], [0x06])):
                if not (self.sender() in self.compactEffectsSys):
                    self.compactEffectsSys[self.sender()] = CompactEffectsSysDialog(self)
                self.compactEffectsSys[self.sender()].show()
            elif (self.sender().property('HEX') in ([0x01], [0x02], [0x03], [0x04])):
                # if not (self.sender() in self.compactEffectsIns):
                #    self.compactEffectsIns[self.sender()] = CompactEffectsInsDialog(self)
                # self.compactEffectsIns[self.sender()].show()
                if (self.compactEffectsIns):
                    self.compactEffectsIns.uiToggleEffect.setChecked(0)
                    self.compactEffectsIns.close()
                    self.compactEffectsIns = CompactEffectsInsDialog(self)
                    # self.compactEffectsInsert.uiToggleEffect.setChecked(1)
                else:
                    self.compactEffectsIns = CompactEffectsInsDialog(self)
                self.compactEffectsIns.show()

    def showHideSub(self, checked):
        '''
        Hide/Show Sub fader control when button clicked.
        '''
        if (checked):
            self.Mic1SubFader.show()
            self.Mic1SubLcd.show()
            self.Mic2SubFader.show()
            self.Mic2SubLcd.show()
            self.Wave1SubFader.show()
            self.Wave1SubLcd.show()
            self.Wave2SubFader.show()
            self.Wave2SubLcd.show()
            self.SysEffSub1.show()
            self.SysEffSub2.show()
            self.SysEffSubLabel.show()
        else:
            self.Mic1SubFader.hide()
            self.Mic1SubLcd.hide()
            self.Mic2SubFader.hide()
            self.Mic2SubLcd.hide()
            self.Wave1SubFader.hide()
            self.Wave1SubLcd.hide()
            self.Wave2SubFader.hide()
            self.Wave2SubLcd.hide()
            self.SysEffSub1.hide()
            self.SysEffSub2.hide()
            self.SysEffSubLabel.hide()

    def valueChange(self, a, b, val):
        '''
        custom slot to connect to the changes in the interface with WriteShort to send the control change messages
        '''
        if (DEBUG_MODE == 1):
            print(a, b, val)

        if (REAL_UA_MODE):
            p = mido.Parser()
            p.feed([a, b, val])
            shortMsg = p.get_message()
            if (DEBUG_MODE):
                print('Message to be sent ', shortMsg)
            pmout.send(shortMsg)

    def uniqueSolos(self, checked):
        '''
        unchecks all other solo buttons if the present is checked.
        besides, it actually soloes/unsoloes the channel
        '''

        soloers = ['Mic1', 'Mic2', 'Wave1', 'Wave2']
        soloers.remove(str(self.sender().parent().objectName()))
        if (checked):
            if (DEBUG_MODE == 1):
                print(soloers)
                print('unchecking and desoloing ')
                print('soloing ', str(self.sender().parent().objectName()))

            if (REAL_UA_MODE):
                p = mido.Parser()
                p.feed([self.sender().parent().property('channel').toPyObject(), CC_SOLO_PAR, 1])
                shortMsg = p.get_message()
                if (DEBUG_MODE):
                    print('Message to be sent ', shortMsg)
                pmout.send(shortMsg)

            for soloer in soloers:
                soloingObj = self.findChild(QtGui.QGroupBox, soloer)

                if (REAL_UA_MODE):
                    p = mido.Parser()
                    p.feed([soloingObj.property('channel').toPyObject(), CC_SOLO_PAR, 0])
                    shortMsg = p.get_message()
                    if (DEBUG_MODE):
                        print('Message to be sent ', shortMsg)
                    pmout.send(shortMsg)

                soloingButtonStr = soloer + 'Solo'
                nomuteButtonStr = soloer + 'Mute'
                # print soloingButtonStr
                soloingButton = soloingObj.findChild(QtGui.QPushButton, soloingButtonStr)
                nomuteButton = soloingObj.findChild(QtGui.QPushButton, nomuteButtonStr)
                soloingButton.setChecked(False)
                nomuteButton.hide()
                if (DEBUG_MODE):
                    # review those fucking debug messages. They are just fucking messed up!
                    print('desoloing: ', soloingObj.objectName())
                    print(soloingObj.property('channel').toPyObject())
        else:
            for soloer in soloers:
                soloingObj = self.findChild(QtGui.QGroupBox, soloer)
                remuteButtonStr = soloer + 'Mute'
                remuteButton = soloingObj.findChild(QtGui.QPushButton, remuteButtonStr)
                remuteButton.show()

            if (REAL_UA_MODE):
                p = mido.Parser()
                p.feed([self.sender().parent().property('channel').toPyObject(), CC_SOLO_PAR, 0])
                shortMsg = p.get_message()
                if (DEBUG_MODE):
                    print('Message to be sent ', shortMsg)
                pmout.send(shortMsg)

    def resetMixer(self):
        '''
        Reset all mixer values to average ones.
        ***************************************
        A better idea could be to retrieve the current values (with sysex messages) and use them...
        maybe in the future
        ***************************************
        '''
        self.MasterLineFader.setProperty("value", CC_0127_DEFAULT)
        self.Wave1Fader.setProperty("value", CC_0127_DEFAULT)
        # self.Wave1SubFader.setProperty("value", CC_0127_DEFAULT)
        self.Wave2Fader.setProperty("value", CC_0127_DEFAULT)
        # self.Wave2SubFader.setProperty("value", CC_0127_DEFAULT)
        self.Mic1Fader.setProperty("value", CC_0127_DEFAULT)
        self.Mic1Pan.setProperty("value", CC_PAN_MIDDLE)
        # self.Mic1SubFader.setProperty("value", CC_0127_DEFAULT)
        self.Mic2Fader.setProperty("value", CC_0127_DEFAULT)
        self.Mic2Pan.setProperty("value", CC_PAN_MIDDLE)
        # self.Mic2SubFader.setProperty("value", CC_0127_DEFAULT)
        self.WaveRecFader.setProperty("value", CC_0127_DEFAULT)

        self.Mic1Pan2.setProperty("value", CC_PAN_MIDDLE)

    def __setInitMixerLevels__(self):
        '''
        It works. It send SYSEX and reads answers. But there must me a better way to read and write.
        Actually there is, but I'm lazy.
        '''

        send_RQ1(MIXER_OUTPUT_CONTROL + MIXER_OUTPUT_MASTERLEVEL + MIXER_OUTPUT_MASTERLEVEL_SIZE)
        time.sleep(SLEEP_TIME)

        masterLevel = sysexRead()
        if (DEBUG_MODE):
            print('masterlevel=', masterLevel)
        self.MasterLineFader.setProperty("value", masterLevel)

        send_RQ1(MIXER_OUTPUT_CONTROL + MIXER_OUTPUT_WAVEREC + MIXER_OUTPUT_WAVEREC_SIZE)
        time.sleep(SLEEP_TIME)
        waverecLevel = sysexRead()
        self.WaveRecFader.setProperty("value", waverecLevel)

        send_RQ1(MIC1_FADER + MIC1_FADER_SIZE)
        time.sleep(SLEEP_TIME)
        mic1Level = sysexRead()
        self.Mic1Fader.setProperty("value", mic1Level)

        send_RQ1(MIC2_FADER + MIC2_FADER_SIZE)
        time.sleep(SLEEP_TIME)
        mic2Level = sysexRead()
        self.Mic2Fader.setProperty("value", mic2Level)

        send_RQ1(WAVE1_FADER + WAVE1_FADER_SIZE)
        time.sleep(SLEEP_TIME)
        wave1Level = sysexRead()
        self.Wave1Fader.setProperty("value", wave1Level)

        send_RQ1(WAVE2_FADER + WAVE2_FADER_SIZE)
        time.sleep(SLEEP_TIME)
        wave2Level = sysexRead()
        self.Wave2Fader.setProperty("value", wave2Level)


class CompactEffectsInsDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(CompactEffectsInsDialog, self).__init__(parent)
        # here is where I store the channel choosen fo the effect (mic1, mic2, wave1, wave2, sys1, sys2)
        self.SenderHex = parent.sender().property('HEX').toPyObject()
        # load the ui...
        self.ui = PyQt4.uic.loadUi('ui/compacteffectsinsdialog.ui', self)

        # populate the effect groups

        for key in COMPACT_INS_EFX_GROUP.keys():
            self.uiEffectGroupsList.addItem(COMPACT_INS_EFX_GROUP[key][0])

        # connect the group list to the effect type list in order to populate it
        self.uiEffectGroupsList.currentIndexChanged.connect(self.populateEffectType)

        # populate the effect type list with the first one (0)
        self.populateEffectType(0)

        # connect the set effect button with the relative function
        self.uiToggleEffect.toggled.connect(self.setEffect)

    def populateEffectType(self, index):
        """
        populate the list of effect types


        """
        # first, clear the previous list
        self.uiEffectTypeList.clear()

        # remember in which group we are
        self.InsEffectGroup = index

        # get the effect type names and put them in the drop down list
        for effectType in COMPACT_INS_EFX_GROUP[index][1]:
            self.uiEffectTypeList.addItem(COMPACT_INS_EFX_TYPE[effectType][0])

        # connect the effect type drop down widget with the parameters in order to populate the effect options
        self.uiEffectTypeList.currentIndexChanged.connect(self.populateEffect)

        # set the start effect type to 0
        self.populateEffect(0)

    def populateEffect(self, index):
        """
        populate the effect parameter.
        BE CAREFUL! The offset shit is tricky. I must explain better, I did not understand it myself after a year.

        :param index is relative to the effect group: we must add the offset to get to the right point.

        """
        # clear the parameters
        self.uiEffectParameters.clear()

        # tell the UA-100 we are setting exactly those effect parameters
        send_DT1([0x00, 0x40] + self.SenderHex + [0x00] + COMPACT_INS_EFX_TYPE[indice][1])

        # I need to add an offset because of the grouping for the compact insertion effects.
        #
        # Please note:
        #
        # COMPACT_INS_EFX_GROUP contains the GROUPS or TYPE
        #
        # The offset is actually the first value of the range list in the definition
        #
        # COMPACT_INS_EFX_TYPE misleading name containing the single effects
        #
        # COMPACT_INS_EFX_PARAMETERS[xxx] countains the parameters of the single effects
        #

        # read the offset of the specified group to reach the right effects
        offset = COMPACT_INS_EFX_GROUP[self.InsEffectGroup][1][0]

        if (DEBUG_MODE):
            print('Indice: ', index, ' Offset: ', offset)

        # populate the effect parameters

        for param in COMPACT_INS_EFX_PARAMETERS[index + offset]:
            if (DEBUG_MODE):
                print('dentro: ', param)
            item = CustomTreeItem(self.uiEffectParameters, param)

    def sendEffect(self, value):
        '''
        We send the values set to the UA-100. The effects are only active when also the switch is checked.
        '''

        # first of all convert the passed value to list in order to send the SYSEX message
        valueToList = [value]
        if (DEBUG_MODE):
            print 'LSB/MSB for parameter:', self.sender().property('HEX').toPyObject()

        # if in real mode, actually send the message
        send_DT1([0x00, 0x40] + self.SenderHex + self.sender().property('HEX').toPyObject() + valueToList)

    def setEffect(self, checked):
        '''
        A small but invaluable function:
        
        IT SWITCHES THE WHOLE THIG ON!
        '''

        if (DEBUG_MODE):
            print(self.SenderHex)
        if (checked):
            checkedList = [0x01]
        else:
            checkedList = [0x00]
        send_DT1([0x00, 0x40, 0x40] + self.SenderHex + checkedList)


class CompactEffectsSysDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super(CompactEffectsSysDialog, self).__init__(parent)
        # here is where I store the channel choosen fo the effect (mic1, mic2, wave1, wave2, sys1, sys2)
        self.SenderHex = parent.sender().property('HEX').toPyObject()
        # load the ui...
        self.ui = PyQt4.uic.loadUi('ui/compacteffectssysdialog.ui', self)
        if self.SenderHex == [0x05]:
            self.setWindowTitle('System 1 - ' + self.windowTitle())
            self.uiEffectTypeList.addItem(COMPACT_SYS1_EFX_TYPE[1][0])
            self.uiEffectTypeList.addItem(COMPACT_SYS1_EFX_TYPE[2][0])
        elif self.SenderHex == [0x06]:
            self.setWindowTitle('System 2 - ' + self.windowTitle())
            self.uiEffectTypeList.addItem(COMPACT_SYS2_EFX_TYPE[1][0])
            self.uiEffectTypeList.addItem(COMPACT_SYS2_EFX_TYPE[2][0])

        # connect the combobox with the slot which populates the QTreeWidget
        self.uiEffectTypeList.currentIndexChanged.connect(self.populateEffect)

        self.populateEffect(0)

        self.uiToggleEffect.toggled.connect(self.setEffect)

    def populateEffect(self, index):

        # first af all, sent the effect type to the UA-100
        # This is the LSB/MSB of the effect type (i.e. High Quality Reverb, Mic Simulator) aka the FULL_EFX_TYPE[n][1] (hex value)
        self.uiEffectParameters.clear()
        if (self.SenderHex == [0x05]):
            if (DEBUG_MODE):
                print([0x00, 0x40] + self.SenderHex + [0x00] + COMPACT_SYS1_EFX_TYPE[index + 1][1])
            send_DT1([0x00, 0x40] + self.SenderHex + [0x00] + COMPACT_SYS1_EFX_TYPE[index + 1][1])
            for par in COMPACT_SYS1_EFX_PARAMETERS[index + 1]:
                item = CustomTreeItem(self.uiEffectParameters, par)
        elif (self.SenderHex == [0x06]):
            if (DEBUG_MODE):
                print([0x00, 0x40] + self.SenderHex + [0x00] + COMPACT_SYS2_EFX_TYPE[index + 1][1])
            send_DT1([0x00, 0x40] + self.SenderHex + [0x00] + COMPACT_SYS2_EFX_TYPE[index + 1][1])
            for par in COMPACT_SYS2_EFX_PARAMETERS[index + 1]:
                item = CustomTreeItem(self.uiEffectParameters, par)

    def setEffect(self, checked):
        '''
        A small but invaluable function:
        
        IT SWITCHES THE WHOLE THIG ON!
        '''

        if (DEBUG_MODE):
            print(self.SenderHex)
        if (checked):
            checkedList = [0x01]
        else:
            checkedList = [0x00]
        send_DT1([0x00, 0x40, 0x40] + self.SenderHex + checkedList)

    def sendEffect(self, value):
        '''
        We send the values set to the UA-100. The effects are only active when also the switch is checked.
        '''

        # first of all convert the passed value to list in order to send the SYSEX message
        valueToList = [value]
        if (DEBUG_MODE):
            print 'LSB/MSB for parameter:', self.sender().property('HEX').toPyObject()

        # if in real mode, actually send the message
        send_DT1([0x00, 0x40] + self.SenderHex + self.sender().property('HEX').toPyObject() + valueToList)


class FullEffectsDialog(QtGui.QDialog):
    '''
    The full effect dialog.
    For every single effect selected, I should check if there are already instances for the effect. If not, generate it, if yes, use the old ones.
    BUT after I clead the QTreeWidget the instances of the QTreeWidgetItems get deleted. There should be a better way.
    To achieve this, sadly, we need to classify the items...
    '''

    def __init__(self, parent=None):
        super(FullEffectsDialog, self).__init__(parent)

        # here is where I store the channel choosen fo the effect (mic1, mic2, wave1, wave2, sys1, sys2)
        self.SenderHex = parent.sender().property('HEX').toPyObject()
        # QLineEditStr = 'uiEffectName' + self.sender().text()
        # self.EffectNameTextBox = self.parent().findChild(QtGui.QLineEdit, QLineEditStr)
        # load the ui...
        self.ui = PyQt4.uic.loadUi('ui/fulleffectsdialog.ui', self)

        # look for the FULL_EFX_TYPEs and populate the combo box (drop down menu)
        for key in FULL_EFX_TYPE.keys():
            self.EffectTypeList.addItem(FULL_EFX_TYPE[key][0])

        # connect the combobox with the slot which populates the QTreeWidget
        self.EffectTypeList.currentIndexChanged.connect(self.populateEffect)

        self.populateEffect(0)

        self.uiToggleEffect.toggled.connect(self.setEffect)

    def setEffect(self, checked):
        '''
        A small but invaluable function:
        
        IT SWITCHES THE WHOLE THIG ON!
        '''

        if (DEBUG_MODE):
            print(self.SenderHex)
        if (checked):
            checkedList = [0x01]
            # self.EffectNameTextBox.setText(FULL_EFX_TYPE[self.actualEffectIndex][0])
        else:
            checkedList = [0x00]
            # self.EffectNameTextBox.clear()
        send_DT1([0x00, 0x40, 0x40] + self.SenderHex + checkedList)

    def populateEffect(self, index):

        # first af all, sent the effect type to the UA-100
        # This is the LSB/MSB of the effect type (i.e. High Quality Reverb, Mic Simulator) aka the FULL_EFX_TYPE[n][1] (hex value)
        # if (DEBUG_MODE):
        #    print([0x00, 0x40] + self.SenderHex + [0x00] + FULL_EFX_TYPE[index+1][1])
        send_DT1([0x00, 0x40] + self.SenderHex + [0x00] + FULL_EFX_TYPE[index + 1][1])
        self.actualEffectIndex = index + 1

        self.uiEffectParameters.clear()
        # check if the list isn't yet there... but, as said, the instances are deleted... so what? and How?
        # if not (index in self.effectList):
        #    self.effectList[index]={}
        #    for par in FULL_EFX_PARAMETERS[index+1]:
        #        self.effectList[index][par[0]] = CustomTreeItem(self.uiEffectParameters, par)
        # else:
        #    print self.effectList[index]
        #    for item in self.effectList[index]:
        #        self.uiEffectParameters.addTopLevelItem(self.effectList[index][item])

        # "anonimously" polulate the QTreeWidget ...
        for par in FULL_EFX_PARAMETERS[index + 1]:
            item = CustomTreeItem(self.uiEffectParameters, par)

    def sendEffect(self, value):
        '''
        We send the values set to the UA-100. The effects are only active when also the switch is checked.
        '''

        # first of all convert the passed value to list in order to send the SYSEX message
        valueToList = [value]
        if (DEBUG_MODE):
            print 'LSB/MSB for parameter:', self.sender().property('HEX').toPyObject()

        # if in real mode, actually send the message
        send_DT1([0x00, 0x40] + self.SenderHex + self.sender().property('HEX').toPyObject() + valueToList)


class CustomTreeItem(QtGui.QTreeWidgetItem):
    '''
    Just a dirty way to populate the QTreeWidget with custom items containing each a QSpinBox.
    
    ******************************************************************************************
    ************************************** TODO **********************************************
    set limits, mean value, default value and possibly also a better way to show the values...
    ******************************************************************************************
    
    '''

    def __init__(self, parent, par):
        '''
        parent (QTreeWidget) : Item's QTreeWidget parent.
        name   (str)         : Item's name. just an example.
        '''

        ## Init super class ( QtGui.QTreeWidgetItem )
        super(CustomTreeItem, self).__init__(parent)
        self.par = par
        self.setText(0, par[0])
        self.spinBox = QtGui.QSpinBox(parent)
        self.spinBox.setProperty('HEX', par[3])
        # self.spinBox.setValue(5)

        # nell'implementazione con par[2] dizionario questa riga non va bene...
        # self.spinBox.setRange(min(par[2]), max(par[2]))
        # devo usare par[2].keys()
        self.spinBox.setValue(-1)
        self.spinBox.setRange(min(par[2].keys()), max(par[2].keys()))

        self.spinBox.setWrapping(1)
        parent.setItemWidget(self, 1, self.spinBox)
        self.setText(3, par[1])

        # set the spinBox to some value, in order to let the next setValue trigger the signals


        self.spinBox.valueChanged.connect(self.setActualValue)
        # set the spinBox to some value, in order to let the next setValue trigger the signals
        self.spinBox.setValue(-1)
        self.spinBox.valueChanged.connect(parent.parent().sendEffect)
        self.spinBox.setValue(par[4])

    def setActualValue(self, value):
        self.setText(2, self.par[2][value])


def actualMidiDevices():
    '''
    This should enumerate the devices to (later on) give then the possibility to choose one or guess the right one
    Returns a dictionary with tuples like 
    
    midiDevs = { 0: (tuple), 1: (tuple), ... }
    
    where the tuple is in the format:
    
    ('ALSA', 'UA-100 MIDI 2', 0, 1, 0)
    
    '''
    # Count the MIDI devices connected
    # if (REAL_UA_MODE):
    # #   numDevs = pm.get_count()
    #     try:
    #         numDevs = pm.CountDevices()
    #     except AttributeError:
    #         numDevs = pm.get_count()
    # else:
    #     numDevs = 5
    #     # Initialize the device dictionary
    # # midiDevs = { 0: (tuple), 1: (tuple), ... }
    # #
    if (REAL_UA_MODE):
        IODevs = mido.get_ioport_names()
        numIODevs = len(IODevs)

        if (numIODevs == 0):
            if (DEBUG_MODE == 1):
                print('***************  No midi device found - and we should be in REAL UA mode! Exiting. Bye!')
            sys.exit()

        if (DEBUG_MODE):
            print('We have ', numIODevs, ' output devices:', IODevs)
    else:
        numIODevs = 1
        IODevs = {u'Dummy midi device 0:0'}

    # Initialize the device dictionary
    # midiDevs = { 0: (tuple), 1: (tuple), ... }
    midiDevs = {}
    for dev in range(0, numIODevs):
        midiDevs[dev] = IODevs[dev]
        # try:
        #     midiDevs[dev] = pm.GetDeviceInfo(dev)
        # except AttributeError:
        #     midiDevs[dev] = pm.get_device_info(dev)

    return midiDevs


def rightMidiDevice(midiDevs):
    '''
    Guess the right device for sending Control Change and SysEx messages.
    
    I suppose it is HEAVY dependant on pyPortMidi and ALSA: 
    if *they* change something in the structure of the device info, we are lost!
    
    It scans the midiDevs (dictionary!) looking for something like 'UA-100 Control' with the output flag set to 1.
    '''
    for i in range(0, len(midiDevs)):
        if ('UA-100 Control' in midiDevs[i]):
            if (DEBUG_MODE == 1):
                print('Found something! The controller is device ', i, ', aka ', midiDevs[i][1])
            return int(i)


def sysexRead():
    global pmin

    # if (REAL_UA_MODE):
    #     try:
    #         answer = pmin.Read(buffer_size)
    #     except AttributeError:
    #         answer = pmin.read(buffer_size)
    # else:
    #     answer = CC_0127_DEFAULT
    answerMsg = pmin.receive()
    answerBytes = answerMsg.bytes()
    value = answerBytes[11]
    print('risposta:', answerMsg, ', aka ', answerBytes, '. Value is: ', value)
    # need to parse answer again... 

    return value


def send_RQ1(data):
    '''
    Here we are about to send a Request Data 1.
    Never forget to checksum!
    
    ** Note
    The first part of the message is fixed. What can change is the data (of course, it's function agument!)
    AND the checksum, which on his side, depends on the data.
    '''
    global pmout, pmin
    checksum_result = checksum(data)
    message = RQ1_STATUS \
              + UA_SYSEX_ID \
              + RQ1_COMMAND \
              + data \
              + checksum_result \
              + EOX
    if (DEBUG_MODE):
        print("Message RQ1: ", message)

    if (REAL_UA_MODE):
        p = mido.Parser()
        p.feed(message)
        sysEx_msg = p.get_message()
        if (DEBUG_MODE):
            print('Message to be sent: ', sysEx_msg)
        pmout.send(sysEx_msg)


def send_DT1(data):
    global pmout, pmin
    checksum_result = checksum(data)
    message = DT1_STATUS \
              + UA_SYSEX_ID \
              + DT1_COMMAND \
              + data \
              + checksum_result \
              + EOX
    if (DEBUG_MODE):
        # print(message)
        print(np.array(message))

    if (REAL_UA_MODE):
        p = mido.Parser()
        p.feed(message)
        sysEx_msg = p.get_message()
        if (DEBUG_MODE):
            print('Message to be sent: ', sysEx_msg)
        pmout.send(sysEx_msg)


def checksum(toChecksum):
    '''
    That's how the UA-100 does the checksum:
    Take the data part of SYSEXES and do the maths.
    '''
    checksum_value = (128 - (sum(toChecksum) % 128))
    checksum_list = [checksum_value]
    return list(checksum_list)


if (__name__ == '__main__'):

    # brutal way to catch the CTRL+C signal if run in the console...
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # **************************** MIDI PART: could it go somewhere else? **********************************************

    # initialize the portmidi interface

    # if (REAL_UA_MODE):
    #      #pm.init()
    #      try:
    #          pm.Initialize()
    #          if (DEBUG_MODE):
    #             print('pm.Initialize works')
    #      except AttributeError:
    #          pm.init()
    #          if (DEBUG_MODE):
    #             print('must use init()')

    # INITIALIZATION NOT NEEDED ANYMORE WITH MIDO/RTMID - KEPT FOR THE RECORDS

    # setting the backend to rtmidi and alsa - Actually it's not wise to do it so, but it's ok for now.
    mido.set_backend('mido.backends.rtmidi/LINUX_ALSA')
    # *************************************************
    # TODO: change it to be more general

    # get the list of the Midi Devices according to portmidy
    midiDevs = actualMidiDevices()

    if (DEBUG_MODE == 1):
        print('MIDI DEVICES FOUND: ', len(midiDevs), '. They are: ', midiDevs)

    # guess the right midi device
    if (REAL_UA_MODE):
        DEFAULT_UA100CONTROL = rightMidiDevice(midiDevs)
    else:
        DEFAULT_UA100CONTROL = 1

    if (DEBUG_MODE == 1):
        print('DEFAULT_UA100CONTROL = ', midiDevs[DEFAULT_UA100CONTROL])

    # *******************************************************************************************************************

    app = None
    if (not app):
        app = QtGui.QApplication([])

    dialog = MidiDevsDialog()
    dialog.show()

    if not dialog.exec_():
        # We quit if the the selection dialog quits
        if (DEBUG_MODE == 1):
            print('Bye.')
        sys.exit()

    if (DEBUG_MODE) and (REAL_UA_MODE):
        print('UA100CONTROL = ', midiDevs[UA100CONTROL])

    if (DEBUG_MODE):
        print(
            'Opening device: ', midiDevs[UA100CONTROL], ' for input/ouput')

    if (REAL_UA_MODE):
        # Open device for output

        if (DEBUG_MODE):
            print('Trying the Output...')

        pmout = mido.open_output(midiDevs[UA100CONTROL])

        if (DEBUG_MODE):
            print('...Done! Just opened ', midiDevs[UA100CONTROL], ' for output')

        # Open "the next" device for input

        if (DEBUG_MODE):
            print('Trying the Input...')

        pmin = mido.open_input(midiDevs[UA100CONTROL])

        if (DEBUG_MODE):
            print('...Done! Just opened ', midiDevs[UA100CONTROL], ' for input')

    window = MainWindow()
    window.show()

    if (app):
        app.exec_()
