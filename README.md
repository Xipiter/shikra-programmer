# Shikra EEPROM Programming

## Requirements

1. Install Libusb: `sudo apt-get install libusb-dev` on linux. OSX can skip this step.
2. Install pyusb python libusb bindings: `sudo pip install pyusb`
3. Run Shikra programming utility: `sudo ./shikra.py` Root access is needed to be able to Read and Write to the Shikra USB Device.

## Using LED programming methods

The Shikra programming utility allows users to enable the Shikra LED under different configurations. These methods are called `set_led_*`
Warning: This may not work with older Shikra devices.

1. Run utility: `sudo ./shikra.py`
2. Find attached Shikra device with `find_shikra`
3. Set LED configuration with `set_led_*`
4. Write config to Shikra EEPROM with `write_config`

## Utility Output

```
[+] Welcome to the SHIKRA programming utility by XIPITER.

  ###### ###  ##  ###  ###  ##  ######      ####
 ###  ## ###  ##  ###  ### ##   ###  ##    #####
 ####    ###  ##  ###  #####    ###  ##   ## ###
  #####  #######  ###  #####    ######   ##  ###
    #### ###  ##  ###  ### ##   ### ##  ########
 ##  ### ###  ##  ###  ###  ##  ###  ## ##   ###
  #####  ###  ##  ###  ###  ##  ###  ## ##   ###

shikra> help

Documented commands (type help <topic>):
========================================
find_shikra  help

Undocumented commands:
======================
EOF  exit

shikra> find_shikra
[+] Looking for Shikra...
[+] Shikra device found.
shikra programming> help

Documented commands (type help <topic>):
========================================
backup         help                 set_led_off  set_led_tx    zero
dump           print_config         set_led_on   set_led_txrx
factory_reset  restore_from_backup  set_led_rx   write_config

Undocumented commands:
======================
EOF  exit

shikra programming>
```
