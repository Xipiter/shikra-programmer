#! /usr/bin/env python

import cmd
import usb.core
import struct
import sys

# shikra USB vendor/product
ID_VENDOR = 0x403
ID_PRODUCT = 0x6014
USB_RELEASE_VERSION = 0x0900
EEPROM_SIZE = 256
BYTES_AT_A_TIME = 2  # we need to read 2 "bytes" at a time since each word in eeprom is 16bit, so 2 8bit bytes in python.
# this is the minimum amount of data we can do on a CTRL transfer.
READ_REQ_TYPE = 0xc0
READ_REQ = 0x90
READ_VAL = 0
WRITE_REQ_TYPE = 0x40
WRITE_REQ = 0x91
DUMP_WIDTH = 16  # how many python bytes to print per row in a hex dump. this is 8, 16bit words per line.

# shikra LED eeprom values
LED_TX = 0x10
LED_TRISTATE = 0x00
LED_RX = 0x20
LED_TXRX = 0x30
LED_DRIVE_0 = 0x60

# eeprom type 93C56
EEPROM_TYPE = 0x56

# shikra modes
RS232_MODE = 0x10

# notes
# http://www.graphics.cornell.edu/~westin/canon/ch03.html
# bmRequestType is 0xC0 during read and 0x40 during write.
# https://developer.cisco.com/site/eiot/documents/pyusb-dev-guide/#pyusb-hello-world-program
# http://www.element14.com/community/community/designcenter/single-board-computers/next-gen_beaglebone/blog/2013/07/15/bbb--usb-io-with-ftdi-ft2232h
# https://github.com/walac/pyusb/blob/master/usb/control.py
# https://learn.adafruit.com/adafruit-ft232h-breakout/windows-setup
# http://sourceforge.net/p/ftdi-usb-sio/mailman/message/4081015/
# https://github.com/richardeoin/ftx-prog/blob/master/ftx_prog.c

# Shikra LED on board is D1.
# pin 33 on FT232H / ACBUS9 (https://cdn.shopify.com/s/files/1/0244/5107/products/Screen_Shot_2014-07-28_at_3.52.56_PM_1024x1024.png?v=1423861544)


class ShikraCLI(cmd.Cmd):
    '''
    shikra command line interface
    '''
    def preloop(self):
        self.prompt = "shikra> "
        self.intro = self.welcome()
        pass

    def postloop(self):
        pass

    def do_exit(self, args):
        print("Exiting SHIKRA programming utility...")
        return True

    def do_EOF(self, args):
        print ""
        return True

    def do_find_shikra(self, args):
        '''
            Look for Shikra USB device and do initial configuration.
            This should be run before other configuration steps.
        '''
        print "[+] Looking for Shikra..."
        found = SHIKRA.find()
        if(found):
            print "[+] Shikra device found."
            SHIKRA.config()
            # go to subloop if device is found.
            foundcli = ShikraFoundCLI()
            foundcli.cmdloop()

        else:
            print "[+] Shikra device not found. Try unplugging and plugging the Shikra back in."

    def welcome(self):
            line = "[+] Welcome to the SHIKRA programming utility by XIPITER.\n"
            shikra_logo = '''
  ###### ###  ##  ###  ###  ##  ######      ####
 ###  ## ###  ##  ###  ### ##   ###  ##    #####
 ####    ###  ##  ###  #####    ###  ##   ## ###
  #####  #######  ###  #####    ######   ##  ###
    #### ###  ##  ###  ### ##   ### ##  ########
 ##  ### ###  ##  ###  ###  ##  ###  ## ##   ###
  #####  ###  ##  ###  ###  ##  ###  ## ##   ###
'''
            return line + shikra_logo


class ShikraFoundCLI(cmd.Cmd):

    def preloop(self):
        self.prompt = "shikra programming> "
        pass

    def do_exit(self, args):
        print("Exiting SHIKRA programming utility...")
        return True

    def do_EOF(self, args):
        print ""
        return True

    def do_set_led_tx(self, args):
        '''
            Turn the Shikra LED on during data transmission.
        '''
        self.warn_led()
        SHIKRA.setLEDTx()

    def do_set_led_rx(self, args):
        '''
            Turn the Shikra LED on during data recieve.
        '''
        self.warn_led()
        SHIKRA.setLEDRx()

    def do_set_led_txrx(self, args):
        '''
            Turn the Shikra LED on during data recieved and transmit.
        '''
        self.warn_led()
        SHIKRA.setLEDTxRx()

    def do_set_led_on(self, args):
        '''
            Turn the Shikra LED on solid.
        '''
        self.warn_led()
        SHIKRA.setLEDOn()

    def do_set_led_off(self, args):
        '''
            Turn Shikra LED off.
        '''
        self.warn_led()
        SHIKRA.setLEDOff()

    def do_write_config(self, args):
        '''
            Write current configuration to Shikra.
        '''
        template = SHIKRA.createEEPROMWriteTemplate()
        SHIKRA.writeEEPROM(template)

    def do_dump(self, args):
        '''
            Dumps the device EEPROM values stored on the Shikra to the screen
            in Hex dump format.
        '''
        dump = SHIKRA.dumpEEPROM()
        print SHIKRA.printEEPROM(dump)

    def do_print_config(self, args):
        '''
            Prints the current programming utility configuration to the screen in hex dump format.
            This does not print what is on the shikra EEPROM, `dump` command does that. This prints
            the EEPROM values that will be written on `write_config` command.
        '''
        template = SHIKRA.createEEPROMWriteTemplate()
        print SHIKRA.printEEPROM(template)

    def do_factory_reset(self, args):
        '''
            Restore shikra eeprom to factory defaults of 0xffff in each word
        '''
        SHIKRA.factoryResetEEPROM()

    def do_zero(self, args):
        '''
            Write over shikra eeprom with 0x0000 for every word.
        '''
        SHIKRA.zeroEEPROM()

    def do_backup(self, filename):
        '''
            Backup shikra device eeprom configuration to file specified by filename.
            Format is Hex dump format that resembles FTDI's FT_PROG format.
        '''
        if(filename):
            try:
                f = open(filename, "w+")
                template = SHIKRA.dumpEEPROM()
                eeprom_string = SHIKRA.printEEPROM(template)
                f.write(eeprom_string)
                f.close()
                print "[+] Backup successful to file: {0}".format(filename)
            except:
                print "[+] Trouble writing to file {0}".format(filename)
        else:
            print "[+] Filename needed."

    def do_restore_from_backup(self, filename):
        '''
            After doing `backup` you can restore the eeprom from a backup file into the
            Shikra device's onboard EEPROM memory.
        '''
        SHIKRA.restoreEEPROMFromFile(filename)

    def warn_led(self):
        '''
            Warn users that LED functions for older shikra models may not work.
        '''
        print "[+] WARNING: LED programming methods may not work for older Shikra Models."


class Shikra():
    '''
    deals with setting up device interface on USB bus.
    '''
    def __init__(self):
        self.shikra_dev = ""
        self.read_ep = ""
        self.write_ep = ""
        self.led_config = None
        self.mode = RS232_MODE

    def find(self):
        '''
        find shikra device
        '''
        self.shikra_dev = usb.core.find(idVendor=ID_VENDOR, idProduct=ID_PRODUCT)
        if self.shikra_dev is not None:
            return True
        else:
            return False

    def config(self):
        # set first active
        self.shikra_dev.set_configuration()

        # get endpoint
        cfg = self.shikra_dev.get_active_configuration()
        intf = cfg[0, 0]
        self.read_ep = usb.util.find_descriptor(intf, custom_match=lambda e: e.bEndpointAddress == 0x81)
        self.write_ep = usb.util.find_descriptor(intf, custom_match=lambda e: e.bEndpointAddress == 0x2)

    # -------------------- Shikra EEPROM programming methods ---------------------------#

    def readWordFromEEPROM(self, index):
        '''
        read byte from EEPROM on Shikra.
        '''
        out = self.shikra_dev.ctrl_transfer(READ_REQ_TYPE, READ_REQ, 0x00, index, data_or_wLength=BYTES_AT_A_TIME)
        s = struct.unpack('B' * BYTES_AT_A_TIME, out)
        # word from eeprom is 2 bytes, represented as two integers in struct returned.
        return s

    def writeWordToEEPROM(self, index, value):
        '''
        Write a 'Word' to EEPROM. A Word on the shikra is 16bits, or two bytes on x86.
        value is like 0xFFFF or 0x0000, two bytes
        '''
        self.shikra_dev.ctrl_transfer(WRITE_REQ_TYPE, WRITE_REQ, value, index, data_or_wLength=BYTES_AT_A_TIME)

    def dumpEEPROM(self):
        '''
        reads all bytes from the shikra device eeprom and returns a packed structure
        for printing, writing, restoring, etc.
        '''
        addrcount = 0
        string_struct = ""
        for index in xrange(EEPROM_SIZE / BYTES_AT_A_TIME):
            byte = self.readWordFromEEPROM(addrcount)
            string_struct += struct.pack(">B", byte[0])
            string_struct += struct.pack(">B", byte[1])
            addrcount += 1
        eeprom_list = []
        for byte in string_struct:
            eeprom_list.append(byte)
        return eeprom_list

    def printEEPROM(self, eeprom_list):
        '''
        takes a packed structure as input as eeprom_list.
        Prints a "hex dump" style format of the eeprom_list.
        '''
        eeprom_string = ""
        width = 0
        count = 0
        for index in xrange(EEPROM_SIZE / BYTES_AT_A_TIME):
            byte0 = "{0:0{1}x}".format(ord(eeprom_list[count]), 2).upper()
            byte1 = "{0:0{1}x}".format(ord(eeprom_list[count + 1]), 2).upper()
            if(width < DUMP_WIDTH):
                # print in reverse order due to endian-ness
                eeprom_string += byte1
                eeprom_string += byte0
                eeprom_string += " "
            else:
                eeprom_string += "\n"
                eeprom_string += byte1
                eeprom_string += byte0
                eeprom_string += " "
                width = 0
            count += 2
            width += 2
        return eeprom_string

    def zeroEEPROM(self):
        '''
        write zeros to all 128bytes of shikra EEPROM.
        '''
        for index in xrange(EEPROM_SIZE / BYTES_AT_A_TIME):
            # we can read and write 2
            self.writeWordToEEPROM(index, 0x0000)

    def factoryResetEEPROM(self):
        '''
        return to factory defaults of 0xffff for every word
        '''
        for index in xrange(EEPROM_SIZE / BYTES_AT_A_TIME):
            self.writeWordToEEPROM(index, 0xFFFF)

    def setLEDOff(self):
        '''
        turn shikra led mode off. Sets ACBUS9 to high voltage to inhibit current through LED.
        '''
        self.led_config = LED_TRISTATE

    def setLEDOn(self):
        '''
        test with programming eeprom the pulls ACBUS9 down to 0.00v to turn LED on continously.
        '''
        self.led_config = LED_DRIVE_0

    def setLEDTx(self):
        '''
        configure the led to blink on transmit data.
        '''
        self.led_config = LED_TX

    def setLEDRx(self):
        '''
        configure the led to blink on recieve data.
        '''
        self.led_config = LED_RX

    def setLEDTxRx(self):
        '''
        configure the led to blink on recieve data.
        '''
        self.led_config = LED_TXRX

    def writeEEPROM(self, eeprom_template):
        '''
        write out packed data structure to eeprom on device.
        '''
        count = 0
        for index in xrange(EEPROM_SIZE / BYTES_AT_A_TIME):
            byte0 = struct.unpack('>B', eeprom_template[count])[0]
            byte1 = struct.unpack('>B', eeprom_template[count + 1])[0]
            word = self.bytesToWord(byte1, byte0)  # swap here for endian-ness
            self.writeWordToEEPROM(index, word)
            count += 2

    def bytesToWord(self, byte0, byte1):
        '''
        takes two individual bytes and makes a 16bit word
        '''
        return byte0 << 8 | byte1

    def wordToBytes(self, word):
        '''
        takes a 2 byte word and returns a tuple with two individual bytes
        '''
        byte0 = word >> 8
        byte1 = word & 0xff
        return (byte0, byte1)

    def computeChecksum(self, eeprom_template):
        '''
        compute the checksum to be written to eeprom based on eeprom template
        eeprom template is a struct.packed' object, ie a list of strings where each
        element is a byte in the eeprom.
        '''
        # http://stackoverflow.com/questions/25239423/crc-ccitt-16-bit-python-manual-calculation
        # TODO this doesnt work right now, so come back to it.
        # good thing that checksum is not necessary to functionality :-)
        count = 0
        crc = 0xaaaa
        while count < EEPROM_SIZE:
            byte0 = struct.unpack('>B', eeprom_template[count])[0]
            byte1 = struct.unpack('>B', eeprom_template[count + 1])[0]
            word = self.bytesToWord(byte1, byte0)  # swappadoodle
            if((count >= 0 and count < 36) or (count >= 128 and count < 254)):
                crc = crc ^ word
                crc = (crc << 1) | (crc >> 15)
            count += 2
        return crc

    def restoreEEPROMFromFile(self, filename):
        '''
        given a filename, this function reads the hex dump of eeprom
        from the file and then writes the file contents to eeprom on
        the shikra device.
        '''
        try:
            fd = open(filename, "r")
        except:
            print "[+] ERROR File \"{0}\" does not exist or permissions are wrong.".format(filename)
            sys.exit(1)
        print "[+] Reading EEPROM backup from {0}".format(filename)
        temp_eeprom_array = []
        for line in fd:
            line_tuple = line.strip().split(" ")
            for element in line_tuple:
                temp_eeprom_array.append(int(element, 16))
        print "[+] Writing EEPROM backup from {0} to Shikra".format(filename)
        for index, element in enumerate(temp_eeprom_array):
            self.writeWordToEEPROM(index, element)
        fd.close()

    def createEEPROMWriteTemplate(self):
        '''
        creates a eeprom template in the form of a packed struct and returns that.
        This template can be fed to other methods to print the template or write
        the template to eeprom on a shikra device's eeprom.
        input - mode, defaults to RS232/UART mode.

        This is where most of the 'magic' happens. This is where most of the bytes to
        'bootstrap' the eeprom to a FT_PROG readable state happen here. This includes
        setting the manufacturer, product, and serial number, as well as many other
        configurations.

        This is a little messy, but dealing with raw bytes is probably not the cleanest :P
        '''
        # the shikra eeprom uses 16bit word sizes, so therefore we have
        # to write 2 "bytes" on each write since a byte here is 8 bits.
        vendor_id = ID_VENDOR
        product_id = ID_PRODUCT
        release_number = USB_RELEASE_VERSION
        bus_powered = True
        remote_wakeup = False
        current = 100  # draw of device in mAh
        manufacturer_string = "XIPITER"
        product_string = "SHIKRA"
        serial_string = "XIP12345"
        temp_eeprom_array = ["\x00" for x in xrange(EEPROM_SIZE)]  # initialize with 0x0 bytes

        # write shikra mode
        temp_eeprom_array[0x1] = struct.pack('>B', 0)
        temp_eeprom_array[0x0] = struct.pack('>B', self.mode)

        # write vendor id
        t = self.wordToBytes(vendor_id)
        temp_eeprom_array[0x2] = struct.pack('>B', t[1])
        temp_eeprom_array[0x3] = struct.pack('>B', t[0])

        # write product id
        t = self.wordToBytes(product_id)
        temp_eeprom_array[0x4] = struct.pack('>B', t[1])
        temp_eeprom_array[0x5] = struct.pack('>B', t[0])

        # write release number
        t = self.wordToBytes(release_number)
        temp_eeprom_array[0x6] = struct.pack('>B', t[1])
        temp_eeprom_array[0x7] = struct.pack('>B', t[0])

        # set bus_powerd, remote_wakeup and current draw
        byte0 = 0x0
        byte1 = 0x0
        if(not bus_powered):
            byte0 = 0x40
        else:
            byte0 = 0x80
        if(remote_wakeup):
            byte1 = 0x20
        else:
            byte1 = 0x0

        byte2 = byte0 + byte1
        temp = (current / 2) << 8 | byte2
        t = self.wordToBytes(temp)
        temp_eeprom_array[0x8] = struct.pack('>B', t[1])
        temp_eeprom_array[0x9] = struct.pack('>B', t[0])

        # user programmable portion of 93C56 EEPROM starts at 0x14, so index 7 in our array
        # first byte is len(manufacturer_string) at 0xf
        # which tells us how long to parse the string
        byte0 = (len(manufacturer_string) * 2) + 2

        # the second byte is at 0xe and tells us where the string begins
        # user space is everything after 0x14, and string can start at 0x80 as base

        # one byte needs to be reserved for ETX,NL
        etx = 0x03
        start = 0x20
        base = 0x80
        temp_eeprom_array[base + start] = struct.pack('>B', byte0)
        temp_eeprom_array[base + start + 1] = struct.pack('>B', etx)
        start += 2

        byte1 = base + start  # start of string for manufacturer
        char_start = byte1  # address of first character of the string
        temp_eeprom_array[0xf] = struct.pack('>B', byte0)
        temp_eeprom_array[0xe] = struct.pack('>B', byte1)
        # now we need to actually write the string to that location
        count = 0
        for char in manufacturer_string:
            addr = base + start + count
            temp_eeprom_array[addr + 0] = struct.pack('>B', 0x00)  # add Nul byte
            temp_eeprom_array[addr] = struct.pack('>B', ord(char))
            count += 2
        char_start += len(manufacturer_string) * 2

        # now we have to set product string.
        byte0 = (len(product_string) * 2) + 2
        temp_eeprom_array[char_start] = struct.pack('>B', byte0)
        temp_eeprom_array[char_start + 1] = struct.pack('>B', etx)
        char_start += 2
        byte1 = char_start
        temp_eeprom_array[0x11] = struct.pack('>B', byte0)  # set length of string
        temp_eeprom_array[0x10] = struct.pack('>B', byte1)  # set address of string
        count = 0
        for char in product_string:
            addr = char_start + count
            temp_eeprom_array[addr] = struct.pack('>B', ord(char))
            count += 2
        char_start += len(product_string) * 2

        # now write out the serial number
        # serial num = fixed 8-digit alphanumeric string
        byte0 = (len(serial_string) * 2) + 2
        temp_eeprom_array[char_start] = struct.pack('>B', byte0)
        temp_eeprom_array[char_start + 1] = struct.pack('>B', etx)
        char_start += 2
        byte1 = char_start
        temp_eeprom_array[0x13] = struct.pack('>B', byte0)  # set strlen
        temp_eeprom_array[0x12] = struct.pack('>B', byte1)  # set address of string
        count = 0
        for char in serial_string:
            addr = char_start + count
            temp_eeprom_array[addr] = struct.pack('>B', ord(char))
            count += 2
        char_start += len(serial_string) * 2

        # compute checksum TODO
        temp_eeprom_array[254] = struct.pack('>B', 0xff)
        temp_eeprom_array[255] = struct.pack('>B', 0xff)

        # set eeprom hardware type
        temp_eeprom_array[30] = struct.pack('>B', EEPROM_TYPE)

        # configure the shikra's LED.
        # LED on ACBUS9 or C9 depending on FT_PROG name
        if(self.led_config is not None):
            # led argument has been set
            temp_eeprom_array[28] = struct.pack('>B', self.led_config)

        return temp_eeprom_array


# lets just make the shikra device class global so we can stop trying to pass it around. This just makes things easier.
SHIKRA = Shikra()
shell = ShikraCLI()
shell.cmdloop()
