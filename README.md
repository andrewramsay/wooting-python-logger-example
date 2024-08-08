# wooting-python-logger-example

This is a basic script showing how to read keypress data from a Wooting One/Two keyboard using the [Wooting Analog SDK](https://github.com/WootingKb/wooting-analog-sdk).

The Wooting SDK has a C interface, so this script uses `ctypes` to access methods in the dynamic libraries provided. It doesn't expose all the functionality in the SDK but should allow reading of key states.

Instructions:

 * Follow the SDK installation instructions for your platform, and find the path to the `libwooting_analog_wrapper` dynamic library (the extension will be `.so`, `.dll` or `.dylib` depending on the platform)
 * Connect a Wooting keyboard
 * Run the script and press `Space` to start checking for keypresses
 * Try pressing some keys: if things are working you'll see `Keys pressed: <number>` messages being printed
 * To stop recording, just hit `Escape`
 
Each line of the recorded CSV file will contain 3 fields:
 * a timestamp in seconds
 * the number of keys pressed at that time point
 * a |-separated sequence (which may be empty) of interleaved scan codes and analog pressure values (e.g. scan_code_1|analog_value_1|scan_code_2|analog_value_2|...)
 
 
