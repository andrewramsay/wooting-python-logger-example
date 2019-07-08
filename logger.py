import sys
import time
import ctypes
import os
import csv

SCAN_CODE_ESC       = 0x00
SCAN_CODE_SPACE     = 0x53

SLEEP_TIME          = 0.0001

class WootingPython(object):
    
    def __init__(self, dll='wooting-analog-sdk-x86.dll'):
        try:
            self._dll = ctypes.cdll.LoadLibrary(dll)
        except OSError as e:
            sys.exit('Failed to load dll from "{}" ({})'.format(dll, e))

        self._excluded = []

    def set_excluded_keys(self, excluded):
        self._excluded = excluded

    def is_connected(self):
        """
        Returns True if a Wooting One/Two is connected, False if not
        """
        return bool(self._dll.wooting_kbd_connected())

    def read_full_buffer(self, items=32):
        """
        Reads a full buffer from the keyboard. See wooting_read_full_buffer
        description at:
        https://dev.wooting.io/wooting-analog-sdk-guide/analog-api-description/
        """

        # number of keypresses that can be retrieved in one operation
        # (range must be 1-32)
        items = min(max(1, items), 32) 

        # buffer is items x 2 bytes to allow for (keycode, analog value) pairs to be returned
        buffer = ctypes.cast(ctypes.create_string_buffer(items * 2), ctypes.POINTER(ctypes.c_uint8))
        # call the C function, which returns the number of keys written into the buffer.
        # the values are interleaved, i.e. scancode1, analogvalue1, scancode2, analogvalue2, ...
        items_read = self._dll.wooting_read_full_buffer(buffer, ctypes.c_uint32(items))

        # separate the two sets of values into their own lists
        scan_codes, analog_vals, codes_and_vals = [], [], []
        excl_count = 0
        for i in range(0, items_read * 2, 2):
            if buffer[i] in self._excluded:
                excl_count += 1
                continue
            scan_codes.append(buffer[i])
            codes_and_vals.append(buffer[i])
            analog_vals.append(buffer[i+1])
            codes_and_vals.append(buffer[i+1])

        return items_read - excl_count, scan_codes, analog_vals, codes_and_vals

    def wait_for_key(self, scan_code):
        """
        Blocks until a specific scan code is received
        """
        while True:
            _, scan_codes, _, _ = self.read_full_buffer()
            if scan_code in scan_codes:
                return

            time.sleep(SLEEP_TIME)

def get_log_name(prefix='wooting_log_'):
    for i in range(10000):
        fname = os.path.join('{}{:04d}.csv'.format(prefix, i))
        if not os.path.exists(os.path.join(fname)):
            return fname

    return None

if __name__ == "__main__":
        wp = WootingPython()
        print('> Checking if keyboard is connected...')
        if not wp.is_connected():
            print('> ERROR: No keyboard found! Connect it and try again.')
            sys.exit(-1)

        # NOTE: on the Wooting Two I was testing this on, it seemed to keep 
        # registering keypresses on codes 88 & 89 even when nothing was touching
        # the device. These codes aren't listed on the keymap either. If anything
        # similar happens with your keyboard, you can filter out those specific
        # keycodes from the returned results like this:
        wp.set_excluded_keys([88, 89])

        print('> Keyboard found OK!')
        logfile_name = get_log_name()
        print('> Will record data to: {}'.format(logfile_name))
        print('> Press <Space> to begin recording, <Esc> to exit')

        wp.wait_for_key(SCAN_CODE_SPACE)

        with open(logfile_name, 'w') as logfile:
            # set up a CSV file for storing the data
            logcsv = csv.writer(logfile, delimiter=',')
            rows = 0
            while True:
                keys_pressed, scan_codes, analog_values, codes_and_values = wp.read_full_buffer()
                print('{} keys pressed'.format(keys_pressed))
                if SCAN_CODE_ESC in scan_codes:
                    break

                # each row of the CSV file will contain these fields:
                #   1. a timestamp (in seconds)
                #   2. the number of keys pressed at that time
                #   3. a single string containing the scan codes and analog values,
                #       separated by | chars (note that the total number of values will
                #       be <number of keys pressed * 2> !)
                #
                # (this could easily be modified, e.g. if you want to have a variable number of
                # fields on each row and save the pressed keys directly)
                row = [str(time.time()), str(keys_pressed), '|'.join(map(str, codes_and_values))]
                logcsv.writerow(row)
                rows += 1
                time.sleep(SLEEP_TIME)

            print('Recorded {} data points'.format(rows))
