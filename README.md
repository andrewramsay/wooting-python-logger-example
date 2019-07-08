# wooting-python-logger-example

This is a basic script showing how to read keypress data from a Wooting One/Two keyboard using their Analog SDK API (see https://dev.wooting.io/wooting-analog-sdk-guide/analog-api-description/).

The API is provided through a C DLL. This script uses ctypes to expose a couple of the required functions, and allows you to record keypress data to a CSV file.

For convenience there's a precompiled DLL included (use an x86/32-bit version of Python!).

Instructions:

 * Connect the keyboard
 * Run the script and check it detects the keyboard (it should hopefully work for both the Wooting One and Two)
 * The script will tell you the name of the file it will log data to (wooting_log_XXXX.csv), then ask you to press Space to begin
 * While it's recording, you'll see "x keys pressed" messages being printed continuously
 * To stop recording, just hit Esc
 
Each line of the recorded CSV file will contain 3 fields:
 * a timestamp in seconds
 * the number of keys pressed at that time point
 * a |-separated sequence (which may be empty) of interleaved scan codes and analog pressure values (e.g. scan_code_1|analog_value_1|scan_code_2|analog_value_2|...)
 
 
