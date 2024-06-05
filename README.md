## Setup Python Environment

### Prerequisites
On Mac OS
```
brew install ffmpeg
```

On Raspberry Pi
```
sudo apt-get install -y python3-dev libasound2-dev
```

### Development Environment 
Within the project root directory.
```
# Install virtualenv
pip install virtualenv

# Create virtual environment
virtualenv env

# Activate the project environment
source env/bin/activate

# Install all project dependencies
pip install -r requirements.txt

# Install all local packages
# This command must be run every time a change is made to the led directory when
# running python as sudo.
pip install -e .

# Run sample scripts
python sample/led_effect.py
```

### Raspberry Pi LED Environment

Within the project root directory.
```
sudo apt-get install libbluetooth-dev

# Install all project dependencies
python3 -m pip install -r requirements_rpi.txt

# Install all local packages
sudo python3 -m pip install -e .

# Run sample scripts
sudo python3 sample/led_effect.py
```

## Design

### UML Diagram
![UML Design](app/files/images/design.png)

The code currently follows the above design. Objects with similar colors all share the same base object type. The inheritance-heavy design allows us to define common behavior in base classes and to enable the use of mock objects. For example:

MockStrip uses a (NUM_PIXELS x 3) numpy array to represent an RGB LED strip. We can use the MockStrip anywhere an LedStrip is expected. This allows us to test LedEffects, which apply an effect on an LedStrip, without needing a physical LED strip.


## TODO

### In order of importance
1. Refactor the sample code. Should be separated by on-device and host.
1. Establish interprocess communication layer to control Cauldron
    a. Should have a configuration and interface.  
    b. Interface should be decypherable across processes.  
    c. This interface needs to be generic enough to allow changing the client without needing to change Cauldron implementation.  
    d. Must support multiple clients for different forms of control (Web interface, Bluetooth, Sensors)  
    e. Needs to accept configuration object/file to configure the process connections. This file should also contain the interface that can be used to communicate with the cauldron
1. Create configuration file to initialize the Cauldron process, specifying GPIO, sound files, etc...
1. Implement a control for the cauldron to trigger explosions
2. Create an AudioEffect class which wraps AudioSegment. This will allow us to test AudioPlayers
3. Create a test suite that can catch threading issues in the players module
4. Create a multithreaded MockEffectPlayer that can be run from a non-main thread
5. Add more colors to the Cauldron
6. Optionally randomize the cauldron bubble colors, instead of having fixed combinations
