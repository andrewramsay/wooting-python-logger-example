import csv
import os
import sys
import time
import datetime
from ctypes import (
    POINTER,
    c_float,
    c_uint16,
    c_uint32,
    cast,
    cdll,
    create_string_buffer,
    sizeof,
    memset,
)
from typing import List, Tuple

KEYCODES_HID                  = 0
KEYCODES_SCANCODE1            = 1
KEYCODES_VIRTUALKEY           = 2
KEYCODES_VIRTUALKEY_TRANSLATE = 3

SCAN_CODE_ESC       = 41
SCAN_CODE_SPACE     = 44

class WootingPython(object):
    """
    Implements a simple ctypes interface to some of the functionality in the 
    Wooting Analog SDK: https://github.com/WootingKb/wooting-analog-sdk
    """

    def __init__(self, sdk_wrapper_path: str, buffer_size: int = 64) -> None:
        """
        Create a new WootingPython instance.

        To access the analog SDK functionality, 3 dynamic libraries need to be
        installed from the SDK (either using an installer/package or manually).

        There are:
           - the core SDK itself (libwooting_analog_sdk.so/dll/dylib)
           - the analog plugin (libwooting_analog_plugin.so/dll/dylib)
           - the SDK "wrapper" (libwooting_analog_wrapper.so/dll/dylib)
       
        The SDK wrapper implements the external API for applications to use, and you
        must pass the path to a copy of this library to this method. 

        Args:
            sdk_wrapper_path (str): full filename of the libwooting_analog_wrapper dynamic library
            buffer_size (int): max number of key states to read from the device with read_full_buffer

        Returns:
            None
        """
        try:
            self._lib = cdll.LoadLibrary(sdk_wrapper_path)
        except OSError as e:
            sys.exit(f'Failed to load SDK wrapper library from {sdk_wrapper_path} ({e})')

        self._excluded = set()

        # initialise the SDK, check for negative return codes on error
        result = self._lib.wooting_analog_initialise()
        if result < 0:
            raise Exception(f'SDK initialisation failed with error {result}')

        self.buffer_size = buffer_size
        # create ctypes buffers for calling read_full_buffer
        self.code_buffer = cast(create_string_buffer(buffer_size * sizeof(c_uint16)), POINTER(c_uint16))
        self.analog_buffer = cast(create_string_buffer(buffer_size * sizeof(c_float)), POINTER(c_float))

    def set_excluded_keys(self, excluded: List[int]) -> None:
        """
        Update the set of keycodes to be ignored when reading a buffer from the device.

        Args:
            excluded (List[int]): a set of keycodes/scancodes to be removed from results

        Returns:
            None
        """
        self._excluded = set(excluded)

    def read_key(self, code: int) -> float:
        """
        Reads the analogue value of a single keycode/scancode.

        This wraps the wooting_analog_read_analog method, which reads
        the key for the given code from any connected device. See
        https://github.com/WootingKb/wooting-analog-sdk/blob/develop/includes/wooting-analog-wrapper.h#L67

        Args:
            code (int): a keycode/scancode

        Returns:
            float: either an analogue value in the 0.0-1.0 range, or a negative value on error
        """
        return self._lib.wooting_analog_read_analog(code)

    def read_full_buffer(self, strip: bool = True) -> List[Tuple[int, float]]:
        """
        Reads a full buffer from the keyboard. 

        https://github.com/WootingKb/wooting-analog-sdk/blob/develop/SDK_USAGE.md#read-all-analog-values
        https://github.com/WootingKb/wooting-analog-sdk/blob/develop/includes/wooting-analog-wrapper.h#L132

        The maximum number of returned key states is set by the buffer_size parameter
        passed to the constructor. 

        If "strip" is set to True, entries for keycodes which are set to 0 will be removed from the
        results. 

        If "set_excluded_keys" has been used to create a set of excluded keycodes, these will also be
        removed from the results. 

        Args:
            strip (bool): if True, remove entries where the keycode is 0 (usually meaning empty/unset)

        Returns:
            List[Tuple[int, float]]: a list of (keycode, analog value) pairs up to a max of self.buffer_size
        """

        # clear our ctypes buffers and call the SDK method
        memset(self.code_buffer, 0, self.buffer_size * sizeof(c_uint16))
        memset(self.analog_buffer, 0, self.buffer_size * sizeof(c_float))
        result = self._lib.wooting_analog_read_full_buffer(self.code_buffer, self.analog_buffer, c_uint32(self.buffer_size))

        # if the result is negative, it indicates an error
        if result < 0:
            print(f'Warning: wooting_analog_read_full_buffer returned an error: {result}')
            return []

        values = []
        # if result is >0, it is the number of buffer entries that were populated
        for x in range(result):
            if (strip is False or self.code_buffer[x] > 0) and self.code_buffer[x] not in self._excluded:
                values.append((self.code_buffer[x], self.analog_buffer[x]))

        return values

    def wait_for_key(self, code: int) -> None:
        """
        Blocks until a specific keycode/scancode is received

        Args:
            code (int): a keycode/scancode to wait for

        Returns:
            None
        """
        while True:
            result = self.read_full_buffer()
            for value in result:
                cur_code, _ = value
                if cur_code == code:
                    return

            time.sleep(0.001)

def get_log_name(prefix: str = 'wooting_log_') -> str:
    """
    Return a timestamped log file name.

    Args:
        prefix (str): a prefix for the filename

    Returns:
        str: a filename of the form "<prefix>YYYYmmdd_HHMMSS.csv"
    """
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{prefix}{now}.csv'

if __name__ == "__main__":
    wp = WootingPython('libwooting_analog_wrapper.so')

    logfile_name = get_log_name()
    print(f'> Will record data to: {logfile_name}')
    print('> Press <Space> to begin recording, <Esc> to exit')

    wp.wait_for_key(SCAN_CODE_SPACE)
    rows = 0
    logging = True
    last_keys_pressed = -1

    with open(logfile_name, 'w') as logfile:
        logcsv = csv.writer(logfile, delimiter=',')
        while logging:
            key_states = wp.read_full_buffer(True)
            if len(key_states) != last_keys_pressed:
                print(f'Keys pressed: {len(key_states)}')
                last_keys_pressed = len(key_states)

            for code, value in key_states:
                if code == SCAN_CODE_ESC:
                    logging = False

            # each row of the CSV file will contain these fields:
            #   1. a timestamp (in seconds)
            #   2. the number of keys pressed at that time
            #   3. a single string containing the scan codes and analog values,
            #       separated by | chars (note that the total number of values will
            #       be <number of keys pressed * 2> !)
            #
            # (this could easily be modified, e.g. if you want to have a variable number of
            # fields on each row and save the pressed keys directly)
            row = [str(time.time()), str(len(key_states)), '|'.join(map(str, [x for key_state in key_states for x in key_state]))]
            logcsv.writerow(row)
            rows += 1
            time.sleep(0.001)

        print('Recorded {} data points'.format(rows))
