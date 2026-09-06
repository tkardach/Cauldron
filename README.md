# Cauldron

Halloween IoT special effects system.

The project consists of a distributed architecture where a "dumb" microcontroller acts as a high-speed peripheral receiver, while a central Python server manages the complex logic and audio-visual orchestration

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
# Create virtual environment
python -m venv .env

# Activate the project environment
source .env/bin/activate

# Install all project dependencies
pip install -r requirements.txt

# Run sample scripts
python -m cauldron.sample.effect_chain_test
```

## Design

### UML Diagram
![UML Design](app/files/images/design.png)

The code currently follows the above design. Objects with similar colors all share the same base object type. The inheritance-heavy design allows us to define common behavior in base classes and to enable the use of mock objects. For example:

MockStrip uses a (NUM_PIXELS x 3) numpy array to represent an RGB LED strip. We can use the MockStrip anywhere an LedStrip is expected. This allows us to test LedEffects, which apply an effect on an LedStrip, without needing a physical LED strip.
