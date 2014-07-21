import sys
import os
import pyportmidi as pm
from PyQt4 import QtGui, QtCore
from main_ui import *
from types import MethodType
import functools


# Defining costants (taken from UA-100 documentation

# Control Change Messages (for the Mixer part) - SysEx messages will be implemented later on (maybe)

# Control Change *CHANNELS*
CC_MIC1_CH = 0xb0
CC_MIC2_CH = 0xb1
CC_WAVE1_CH = 0xb2
CC_WAVE2_CH = 0xb3
CC_SYSRET_CH = 0xb4
CC_SYSSUB_CH = 0xb5
CC_WAVEREC_CH = 0xbE
CC_LINE_MASTER_CH = 0xBF

# Control Change *PARAMETERS* 
CC_MICLINESELECTOR_PAR = 21 # 0x15
CC_PAN_PAR = 10 # 0x0A - 0 - 64 - 127 (LEFT - CENTER - RIGHT)
CC_SEND1_PAR = 16 # 0x10
CC_SEND2_PAR = 17 # 0x11
CC_MUTE_PAR = 18 # 0x12
CC_SOLO_PAR = 19 # 0x13
CC_SUB_FADER_PAR = 20 # 0x14
CC_MAIN_FADER_PAR = 7 # 0x70
CC_SELECTOR_PAR = 22 # 0x16
CC_EFFECTSWITHC_PAR = 23 # 0x23

# Control Change Setting range

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


CC_0127_DEFAULT = 64


def pm_open(device):
    '''
    Possibly not the best solution.
    '''
    global pmout
    pmout = pm.midi.Output(device)
    #pmout.write_short(0xBF,7,60)
    

@QtCore.pyqtSlot()
def valueChange(a,b,val):
    '''
    I had to create a custom slot to connect to the changes in the interface. Hope it's the right way.
    '''
    global pmout
    #pmout.write_short(0xBF,7,volume)
    pmout.write_short(a,b,val)
    
    # output for debug purposes
    print hex(a),b,val

@QtCore.pyqtSlot()
def updateDeviceLabels(ui, midiDevs, indice):
    '''
    I should be an easy task to update label according to a combo box...
    '''
    ui.midiApiText.setText(str(midiDevs[indice][0]))
    ui.deviceNameText.setText(str(midiDevs[indice][1]))
    if (midiDevs[indice][2] == 1 and midiDevs[indice][3] == 0):
        ui.deviceIOText.setText('INPUT')
    elif (midiDevs[indice][2] == 0 and midiDevs[indice][3] == 1):
        ui.deviceIOText.setText('OUTPUT')
    else:
        ui.deviceIOText.setText('N/A')
    print midiDevs[indice][2], midiDevs[indice][3]

def actualMidiDevices():
    '''
    This should enumerate the devices to (later on) give then the possibility to choose one or guess the right one
    '''
    numDevs = pm.get_count()
    midiDevs = {}
    for dev in range(0,numDevs):
        midiDevs[dev]=pm.get_device_info(dev)
    return midiDevs


def rightMidiDevice(midiDevs):
    '''
    Guess the right device for sending Control Change and SysEx messages.
    
    I suppose is HEAVY dependant on pyPortMidi and ALSA: if they change something in the structure of the device info, we are lost!
    '''
    for i in range(0,len(midiDevs)):
        print i
        if (midiDevs[i][1] == 'UA-100 Control') & (midiDevs[i][3] == 1):
            print 'Trovato! Il controller e il device ',i, ', ovvero ',midiDevs[i][1]
            return int(i)


def setupMixer(ui,window):
    '''
    I thought it'd be better to setup the connections here, as qt4designer is not so nice with custom slots.
    '''
    
    # *************** MIC1 *********************

    # Setting Up the Mic1 Fader
    ui.Mic1.valueChanged.connect(ui.Mic1Lcd.display)
    ui.Mic1.valueChanged.connect(functools.partial(window.valueChange, CC_MIC1_CH, CC_MAIN_FADER_PAR))
    #ui.Mic1.setProperty("value", CC_0127_DEFAULT)
    ui.Mic1.setProperty("channel", CC_MIC1_CH)
    ui.Mic1.setProperty("parameter", CC_MAIN_FADER_PAR)
    
    # Setting Up the Mic1 Pan Dial
    ui.Mic1Pan.valueChanged.connect(ui.Mic1PanLcd.display)
    ui.Mic1Pan.valueChanged.connect(functools.partial(window.valueChange, CC_MIC1_CH, CC_PAN_PAR))
    #ui.Mic1Pan.setProperty("value", CC_0127_DEFAULT)
    ui.Mic1Pan.setProperty("channel", CC_MIC1_CH)
    ui.Mic1Pan.setProperty("parameter", CC_PAN_PAR)
    
    # *************** MIC2 *********************
    
    # Setting Up the Mic2 Fader
    ui.Mic2.valueChanged.connect(ui.Mic2Lcd.display)
    ui.Mic2.valueChanged.connect(functools.partial(window.valueChange, CC_MIC2_CH, CC_MAIN_FADER_PAR))
    #ui.Mic2.setProperty("value", CC_0127_DEFAULT)
    ui.Mic2.setProperty("channel", CC_MIC2_CH)
    ui.Mic2.setProperty("parameter", CC_MAIN_FADER_PAR)
    
    # Setting Up the Mic2 Pan Dial
    ui.Mic2Pan.valueChanged.connect(ui.Mic2PanLcd.display)
    ui.Mic2Pan.valueChanged.connect(functools.partial(window.valueChange, CC_MIC2_CH, CC_PAN_PAR))
    #ui.Mic2Pan.setProperty("value", CC_0127_DEFAULT)
    ui.Mic2Pan.setProperty("channel", CC_MIC2_CH)
    ui.Mic2Pan.setProperty("parameter", CC_PAN_PAR)
    
    # *************** WAVE1 *********************
    
    # Setting up the Wave1 Fader
    ui.Wave1.valueChanged.connect(ui.Wave1Lcd.display)
    ui.Wave1.valueChanged.connect(functools.partial(window.valueChange, CC_WAVE1_CH, CC_MAIN_FADER_PAR))
    #ui.Wave1.setProperty("value", CC_0127_DEFAULT)
    ui.Wave1.setProperty("channel", CC_WAVE1_CH)
    ui.Wave1.setProperty("parameter", CC_MAIN_FADER_PAR)
    
    # *************** WAVE2 *********************
    
    # Setting up the Wave1 Fader
    ui.Wave2.valueChanged.connect(ui.Wave2Lcd.display)
    ui.Wave2.valueChanged.connect(functools.partial(window.valueChange, CC_WAVE2_CH, CC_MAIN_FADER_PAR))
    #ui.Wave2.setProperty("value", CC_0127_DEFAULT)
    ui.Wave2.setProperty("channel", CC_WAVE2_CH)
    ui.Wave2.setProperty("parameter", CC_MAIN_FADER_PAR)    
    
    # *************** MASTERLINE *********************
    
    # Setting Up the MasterLine Fader
    ui.MasterLine.valueChanged.connect(ui.MasterLineLcd.display)
    ui.MasterLine.valueChanged.connect(functools.partial(window.valueChange, CC_LINE_MASTER_CH, CC_MAIN_FADER_PAR))
    #ui.MasterLine.setProperty("value", CC_0127_DEFAULT)
    ui.MasterLine.setProperty("channel", CC_LINE_MASTER_CH)
    ui.MasterLine.setProperty("parameter", CC_MAIN_FADER_PAR)
    
def setupDevicesList(ui,window,midiDevs,UA100CONTROL):
    '''
    Sets up the ComboBox with a list of MIDI devices. Not that the combo box must be connected: at the moment it is not.
    '''
    for i in range(0,len(midiDevs)):
        ui.outputDevicesList.addItem(str(midiDevs[i]), i)
    
    ui.outputDevicesList.currentIndexChanged.connect(functools.partial(window.updateDeviceLabels, ui, midiDevs))
    
    ui.outputDevicesList.setCurrentIndex(UA100CONTROL)
    

def resetMixer(ui,window):
    '''
        Reset all mixer values to average ones.
    '''
    ui.MasterLine.setProperty("value", CC_0127_DEFAULT)
    ui.Wave1.setProperty("value", CC_0127_DEFAULT)
    ui.Wave2.setProperty("value", CC_0127_DEFAULT)
    ui.Mic1.setProperty("value", CC_0127_DEFAULT)
    ui.Mic1Pan.setProperty("value", CC_0127_DEFAULT)
    ui.Mic2.setProperty("value", CC_0127_DEFAULT)
    ui.Mic2Pan.setProperty("value", CC_0127_DEFAULT)

def main(): 
    '''
    it already needs a big clean-up. *Andiamo bene...*
    
    '''
    
    # **************************** MIDI PART: could it go somewhere else? **********************************************
    pm.init()
    midiDevs=actualMidiDevices()
    #print midiDevs
    #print len(midiDevs)
    UA100CONTROL = rightMidiDevice(midiDevs)
    pm_open(UA100CONTROL)
    # *******************************************************************************************************************
    app = QtGui.QApplication(sys.argv)
    window = QtGui.QMainWindow()
    window.valueChange = valueChange
    window.updateDeviceLabels = updateDeviceLabels
    ui = Ui_MainWindow()
    ui.setupUi(window)
    
    # Changing the device in the device list ACTUALLY DOES NOT WORK!
    # **************************************************************
    setupDevicesList(ui,window,midiDevs,UA100CONTROL)
    # **************************************************************
    setupMixer(ui,window)
    resetMixer(ui,window)

    window.show()
    sys.exit(app.exec_())



if __name__ == '__main__':
    main()

