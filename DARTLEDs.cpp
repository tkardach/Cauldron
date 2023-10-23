#include "FastLED.h"
#include <Arduino.h>
#include<Event.h>
#include<EEPROM.h>
#include <Timer.h>
#include <boards.h>
#include <RBL_nRF8001.h>

#define NUM_LEDS 100
#define DATA_PIN 0
#define UPDATES_PER_SECOND 100
#define FRAMES_PER_SECOND  120
#define REQN 8
#define RDYN 9
const int firmwareVersion = 191; // divide by 10 to get 1.9, ...

/*
 ** New **
 Bluetooth protocol - all commands are three bytes:
 command, Data0, Data1:
 0x00: firmware version
 0x01: Start/Stop
     0- stop
     1- play
     3- reset
 0x02: Mode
 0- off
 1- on
 2- blink
 3- show
 4- single led run
 5- duel led run
 6- broadway flash
 0x03: Dart 1: r, g
 0x04: Dart 1: b
 0x05: Dart 2: r, g
 0x06: Dart 2: b
 0x07: Dart 3: r, g
 0x08: Dart 3: b
 0x09: Dart 4: r, g
 0x0a: Dart 4: b
 0x0b: Dart 5: r, g
 0x0c: Dart 5: b
 0x0d: bg: r, g
 0x0e: bg: b

 0x0f: brightness (all)
 0x10: setColor (0-5)
 */
 
// this is for terminal printing during debug
//#define DEBUG 1
#ifdef DEBUG
 #define DEBUG_PRINT(x)  Serial.print(x)
 #define DEBUG_PRINTLN(x) Serial.println(x)
#else
 #define DEBUG_PRINT(x)
 #define DEBUG_PRINTLN(X)
#endif
 


// Define the array of leds
CRGB leds[NUM_LEDS];

CRGB dart1=0xFF7F50;   // orange 0xFF7F50
CRGB dart2=0xA9A9A9; // gun metal 0xA9A9A9
CRGB dart3=0xDCDCDC;    // 0xDCDCDC
CRGB dart4=0x87CEEB;     // blue 0x87CEEB
CRGB dart5=0xEE82EE;      // magenta 0xEE82EE
CRGB backGround=0xFFFFE0; // warm yellow 0xFFFFE0
CRGB setColor = 0;

void rainbow();
void rainbowWithGlitter();
void addGlitter( fract8 chanceOfGlitter);
void confetti();
void sinelon();
void bpm();
void juggle();

CRGBPalette16 currentPalette;
TBlendType    currentBlending;

extern CRGBPalette16 myRedWhiteBluePalette;
extern const TProgmemPalette16 myRedWhiteBluePalette_p PROGMEM;

int timerID = 0;
int timerID2 = 0;
int brightness = 50;
bool gReverseDirection = false;
bool clearHeat = true;

class Runner { 
  uint8_t pos;
  uint8_t dir; 
public: 
  void setPos(uint8_t i) { pos = i; } 
  uint8_t getPos() { return pos; }  
  void setDir(uint8_t i) { dir = i; } 
  uint8_t getDir() { return dir; }
}; 

Runner run[6];  // no more than 6 runners
int numRunners = 1; // total number of runners
 
Timer t;      // timer
Timer t2;     // timer 2
byte loaded = 0;        // flag to print BLE connected message only once
byte mode = 1;

// List of patterns to cycle through.  Each is defined as a separate function below.
typedef void (*SimplePatternList[])();
SimplePatternList gPatterns = { rainbow, rainbowWithGlitter, confetti, sinelon, juggle, bpm };

uint8_t gCurrentPatternNumber = 0; // Index number of which pattern is current
uint8_t gHue = 0; // rotating "base color" used by many of the patterns

void setBrightness();
void allOff();
void stopTimer();
void Fire2012(void *context);

#define ARRAY_SIZE(A) (sizeof(A) / sizeof((A)[0]))

void nextPattern()
{
  // add one to the current pattern number, and wrap around at the end
  gCurrentPatternNumber = (gCurrentPatternNumber + 1) % ARRAY_SIZE( gPatterns);
}

void rainbow() 
{
  // FastLED's built-in rainbow generator
  fill_rainbow( leds, NUM_LEDS, gHue, 7);
}

void rainbowWithGlitter() 
{
  // built-in FastLED rainbow, plus some random sparkly glitter
  rainbow();
  addGlitter(80);
}

void addGlitter( fract8 chanceOfGlitter) 
{
  if( random8() < chanceOfGlitter) {
    leds[ random16(NUM_LEDS) ] += CRGB::White;
  }
}

void confetti() 
{
  // random colored speckles that blink in and fade smoothly
  fadeToBlackBy( leds, NUM_LEDS, 10);
  int pos = random16(NUM_LEDS);
  leds[pos] += CHSV(gHue + random8(64), 200, 255);
}

void sinelon()
{
  // a colored dot sweeping back and forth, with fading trails
  fadeToBlackBy( leds, NUM_LEDS, 20);
  int pos = beatsin16(13,0,NUM_LEDS);
  leds[pos] += CHSV( gHue, 255, 192);
}

void bpm()
{
  // colored stripes pulsing at a defined Beats-Per-Minute (BPM)
  uint8_t BeatsPerMinute = 62;
  CRGBPalette16 palette = PartyColors_p;
  uint8_t beat = beatsin8( BeatsPerMinute, 64, 255);
  for( int i = 0; i < NUM_LEDS; i++) { //9948
    leds[i] = ColorFromPalette(palette, gHue+(i*2), beat-gHue+(i*10));
  }
}

void juggle() {
  // eight colored dots, weaving in and out of sync with each other
  fadeToBlackBy( leds, NUM_LEDS, 20);
  byte dothue = 0;
  for( int i = 0; i < 8; i++) {
    leds[beatsin16(i+7,0,NUM_LEDS)] |= CHSV(dothue, 200, 255);
    dothue += 32;
  }
}

void rainbowShow(void *context)
{
    // Call the current pattern function once, updating the 'leds' array
  gPatterns[gCurrentPatternNumber]();

  // send the 'leds' array out to the actual LED strip
  FastLED.show();  
  // insert a delay to keep the framerate modest
  FastLED.delay(1000/FRAMES_PER_SECOND); 

  // do some periodic updates
  EVERY_N_MILLISECONDS(20) { gHue++; } // slowly cycle the "base color" through the rainbow
  EVERY_N_SECONDS(3) { nextPattern(); } // change patterns periodically
}

void startRainbowShow()
{
   FastLED.setBrightness(96);
  // set all off, then set brightness, then start
  allOff();
  timerID = t.stop(timerID); // stop any existing timer
  rainbowShow((void*)0);
  timerID = t.every(10, rainbowShow, (void*)0);
}

// sets all pixels to color
void lightsOn(CRGB color)
{
  //stopTimer();
  //allOff();
  for(int dot = 0; dot < NUM_LEDS; dot++) { 
    leds[dot] = color;
  }
  FastLED.show();
}

void lightsRunning(void *context)
{
  
  for (int i = 0; i < numRunners; i++) {
    uint8_t pos = run[i].getPos();  // get current position
    leds[pos] = CRGB::Black; // led at pos gets blanked
    
    // calculate pos of new led (+/- 1 based on direction)
    if (run[i].getDir() == 0) { // increment position
      if (pos == NUM_LEDS-1) {
        run[i].setPos(0);
      } else {
        run[i].setPos(pos+1);
      }
      //run[i].setPos(run[i].getPos() + 1);
    } else {  // decrement position
      if (pos == 0) {
        run[i].setPos(NUM_LEDS-1);
      } else {
        run[i].setPos(pos-1);
      }
    }

    pos = run[i].getPos();
    leds[pos] = setColor;
  }
  FastLED.show();
}

void lightsOddEven(int odd)
{
  for(int dot = 0; dot < NUM_LEDS; dot+=2) { 
    if (odd == 0) {
      leds[dot] = setColor;
      leds[dot+1] = CRGB::Black;
    } else {
      leds[dot] = CRGB::Black;
      leds[dot+1] = setColor;
    }
  }
}

void lightsBroadway(void *context)
{
  static bool blink = false;
  blink = !blink;
  if (blink) {
    lightsOddEven(0);
  } else {
    lightsOddEven(1);
  }
  FastLED.show();
}

void lightsFlashing(void *context)
{
  static bool blink = false;
  blink = !blink;
  if (blink) {
    lightsOn(setColor);
  } else {
    allOff();
  }
  FastLED.show();
}

void FillLEDsFromPaletteColors( uint8_t colorIndex)
{
    uint8_t brightness = 255;
    
    for( int i = 0; i < NUM_LEDS; i++) {
        leds[i] = ColorFromPalette(currentPalette, colorIndex, brightness, currentBlending);
        colorIndex += 3;
    }
}

void ChangePalettePeriodically()
{
    uint8_t secondHand = (millis() / 1000) % 60;
    static uint8_t lastSecond = 99;
    
    if( lastSecond != secondHand) {
        lastSecond = secondHand;
        if( secondHand ==  0)  { currentPalette = RainbowColors_p;         currentBlending = LINEARBLEND; }
        if( secondHand == 10)  { currentPalette = RainbowStripeColors_p;   currentBlending = NOBLEND;  }
        if( secondHand == 15)  { currentPalette = RainbowStripeColors_p;   currentBlending = LINEARBLEND; }
        if( secondHand == 20)  { SetupPurpleAndOrangePalette();            currentBlending = LINEARBLEND; }
        if( secondHand == 25)  { SetupTotallyRandomPalette();              currentBlending = LINEARBLEND; }
        if( secondHand == 30)  { SetupBlackAndFuchsiaStripedPalette();       currentBlending = NOBLEND; }
        if( secondHand == 35)  { SetupBlackAndFuchsiaStripedPalette();       currentBlending = LINEARBLEND; }
        if( secondHand == 40)  { currentPalette = CloudColors_p;           currentBlending = LINEARBLEND; }
        if( secondHand == 45)  { currentPalette = PartyColors_p;           currentBlending = LINEARBLEND; }
        if( secondHand == 50)  { currentPalette = myRedWhiteBluePalette_p; currentBlending = NOBLEND;  }
        if( secondHand == 55)  { currentPalette = myRedWhiteBluePalette_p; currentBlending = LINEARBLEND; }
    }
}

// This function fills the palette with totally random colors.
void SetupTotallyRandomPalette()
{
    for( int i = 0; i < 16; i++) {
        currentPalette[i] = CHSV( random8(), 255, random8());
    }
}

// This function sets up a palette of black and fuchsia stripes,
void SetupBlackAndFuchsiaStripedPalette()
{
    // 'black out' all 16 palette entries...
    fill_solid( currentPalette, 16, CRGB::Black);
    // and set every fourth one to white.
    currentPalette[0] = CRGB::Fuchsia;
    currentPalette[4] = CRGB::Fuchsia;
    currentPalette[8] = CRGB::Fuchsia;
    currentPalette[12] = CRGB::Fuchsia;
    
}

// This function sets up a palette of purple and orange stripes.
void SetupPurpleAndOrangePalette()
{
    CRGB purple = CHSV( HUE_PURPLE, 255, 255);
    CRGB orange  = CHSV( HUE_ORANGE, 255, 255);
    CRGB black  = CRGB::Black;
    
    currentPalette = CRGBPalette16(
                                   orange, orange, black, black,
                                   purple, purple, black,  black,
                                   orange, orange, black, black,
                                   purple, purple, black,  black );
}


// This example shows how to set up a static color palette
// which is stored in PROGMEM (flash), which is almost always more
// plentiful than RAM.  A static PROGMEM palette like this
// takes up 64 bytes of flash.
const TProgmemPalette16 myRedWhiteBluePalette_p PROGMEM =
{
    CRGB::Orange,
    CRGB::Gray, // 'white' is too bright compared to red and blue
    CRGB::Blue,
    CRGB::DarkMagenta,
    
    CRGB::Orange,
    CRGB::Gray,
    CRGB::Blue,
    CRGB::DarkMagenta,
    
    CRGB::Orange,
    CRGB::Orange,
    CRGB::Gray,
    CRGB::Gray,
    CRGB::Blue,
    CRGB::Blue,
    CRGB::DarkMagenta,
    CRGB::DarkMagenta
};


void lightShow(void *context)
{
  int disp = rand() % 7;
  randomColor();
  switch (disp) {
    case 0:
      // flashing lights
      startLightsFlashing(200);
      break;
    case 1:
      // four running lights
      startLightsRunning(200, 4);
      break;
    case 2:
      // broadway lights flashing
      startLightsBroadway(200);
      break;
    case 3:
      // Pallet light show
      startPaletteShow();
      break;
    case 4:
      // six running lights
      startLightsRunning(200, 6);
      break;
    case 5:
      // fire simulation
      startFire();
      break;
    case 6:
      // rainbow light show
      startRainbowShow();
      break;
    default:
      break;
  }
}


void startFire()
{
  setBrightness();
  // set all off, then set brightness, then start
  allOff();
  timerID = t.stop(timerID); // stop any existing timer
  clearHeat = true;
  Fire2012((void*)0);
  timerID = t.every(100, Fire2012, (void*)0);
}

// randomly sets the color to one of the five dart colors
void randomColor()
{
  /* random int between 0 and 4 */
  int r = rand() % 5;
    switch (r) {
    case 0:
      // set dart1 color
      setColor = dart1;
      break;
    case 1:
      // set dart2 color
      setColor = dart2;
      break;
    case 2:
      // set dart3 color
      setColor = dart3;
      break;
    case 3:
      // set dart4 color
      setColor = dart4;
      break;
    case 4:
      // set dart4 color
      setColor = dart5;
      break;
    default:
      break;
  }
}


void startLightsShow()
{
  setBrightness();
  allOff();
  timerID2 = t2.stop(timerID2); // stop any existing timer
  lightShow((void*)0);
  timerID2 = t2.every(10000, lightShow, (void*)0);
}

void stopLightsShow()
{
  t2.stop(timerID2);
  allOff();
}

void paletteShow(void *context)
{
  ChangePalettePeriodically();
  
  static uint8_t startIndex = 0;
  startIndex = startIndex + 1; /* motion speed */
  
  FillLEDsFromPaletteColors( startIndex);
  
  FastLED.show();
}

void startPaletteShow()
{
  currentPalette = RainbowColors_p;
  currentBlending = LINEARBLEND;
  FastLED.setBrightness(60);

  allOff();
  timerID = t.stop(timerID); // stop any existing timer
  paletteShow((void*)0);
  timerID = t.every(10, paletteShow, (void*)0);
}

// starts flashing all lights in a random dart color at an interval of dur
void startLightsFlashing(int dur)
{
  randomColor();
  setBrightness();
  allOff();
  timerID = t.stop(timerID); // stop any existing timer
  lightsFlashing((void*)0);
  timerID = t.every(dur, lightsFlashing, (void*)0);
}

// starts "broadway" flashing lights in a random dart color at an interval of dur
void startLightsBroadway(int dur)
{
  randomColor();
  setBrightness();
  allOff();
  timerID = t.stop(timerID); // stop any existing timer
  lightsBroadway((void*)0);
  timerID = t.every(dur, lightsBroadway, (void*)0);
}

// starts a number of running lights in a random dart color
void startLightsRunning(int dur, int runners)
{
  randomColor();
  setBrightness();
  allOff();
  timerID = t.stop(timerID); // stop any existing timer

  // create an array of LED runners
  for (int i = 0; i < runners; i++) {
    // initialize each runner
    int r = rand() % 2;
    run[i].setDir(r);
    uint8_t pos = i*(NUM_LEDS/runners);
    
    run[i].setPos(pos);
  }
  numRunners = runners; // set runners to global var
  lightsRunning((void*)0);
  timerID = t.every(dur, lightsRunning, (void*)0);
}

// stop timer "t"
void stopTimer()
{
  timerID = t.stop(timerID);
}

// sets all pixels to off/black
void allOff()
{
  for(int dot = 0; dot < NUM_LEDS; dot++) { 
    leds[dot] = CRGB::Black;
  }
  FastLED.show();
}

// set the brightness of the lights based off "brightness" variable
void setBrightness()
{
  FastLED.setBrightness(brightness);
  FastLED.show();
}

// writes a 3 byte BLE command to BLE host
// first byte command, next two bytes an int_16
void writeCmd(uint8_t command, int value)
{
  ble_write(command);
  ble_write(value >> 8);
  ble_write(value);
}

// writes the firmware version to BLE host
void writeFirmware()
{
  writeCmd(0x00, firmwareVersion);
}

void setup() 
{ 
  ble_set_pins(REQN, RDYN);         // REQN pin, RDYN pin
  delay(3000); // power-up safety delay
  FastLED.addLeds<WS2811, DATA_PIN, RGB>(leds, NUM_LEDS);
  
  char name[11] = "FIN6LEDBt2";             
  ble_set_name(name);        // set advertising name
  ble_begin();                // Init. and start BLE library.
  allOff();                   // all on
  FastLED.setBrightness(brightness);
  // start with a default lightshow
  startLightsShow();
}

// Fire2012 by Mark Kriegsman, July 2012
// fire simulation based off cooling and sparking constants
#define COOLING  55
#define SPARKING 120
void Fire2012(void *context)
{
// Array of temperature readings at each simulation cell
  static byte heat[NUM_LEDS];
  if (clearHeat) {
    for(int i = 0; i < NUM_LEDS; i++) {
      heat[i] = 0;
    }
    clearHeat = false;
  }

  // Step 1.  Cool down every cell a little
    for( int i = 0; i < NUM_LEDS; i++) {
      heat[i] = qsub8( heat[i],  random8(0, ((COOLING * 10) / NUM_LEDS) + 2));
    }
  
    // Step 2.  Heat from each cell drifts 'up' and diffuses a little
    for( int k= NUM_LEDS - 1; k >= 2; k--) {
      heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2] ) / 3;
    }
    
    // Step 3.  Randomly ignite new 'sparks' of heat near the bottom
    if( random8() < SPARKING ) {
      int y = random8(7);
      heat[y] = qadd8( heat[y], random8(160,255) );
    }

    // Step 4.  Map from heat cells to LED colors
    for( int j = 0; j < NUM_LEDS; j++) {
      CRGB color = HeatColor( heat[j]);
      int pixelnumber;
      if( gReverseDirection ) {
        pixelnumber = (NUM_LEDS-1) - j;
      } else {
        pixelnumber = j;
      }
      leds[pixelnumber] = color;
    }
    FastLED.show();
}

void loop() 
{
  t.update();
  t2.update();
      while(ble_available())    // if BLE has bytes available to read, returns true
    {
        byte data0, data1, data2 = 0;
        data0 = ble_read();
        data1 = ble_read();
        data2 = ble_read();
        
        if (data0 == 0x00) {  // firmware
            writeFirmware();
        } else if (data0 == 0x01) { // stop/play/reset
            if (data2 == 0x00) {
                // stop
                stopTimer();
                stopLightsShow();
                allOff();     // turn off darts
            } else if (data2 == 0x01) {
              // play
                switch (mode) {
                  case 0:
                    // off
                    stopTimer();
                    stopLightsShow();
                    allOff();     // turn off darts
                    break;
                  case 1:
                    // darts On
                    stopTimer();
                    allOff();
                    lightsOn(dart1);
                    break;
                  case 2:
                    // darts blink
                    startLightsFlashing(500);
                    break;
                  case 3:
                    // running 2 lights
                    startLightsRunning(200, 2);
                    break;
                  case 4:
                    // Fire simulation
                    break;
                  case 5:
                    // darts broadway
                    startLightsBroadway(200);
                    break;
                  case 6:
                    // light show
                    startLightsShow();
                    break;
                  case 7:
                    // all on dart1 color
                    if (data1 == 0) {
                      lightsOn(dart1);
                    } else if (data1 == 1) {
                      // all on dart2 color
                      lightsOn(dart2);
                    } else if (data1 == 2) {
                      // all on dart3 color
                      lightsOn(dart3);
                    } else if (data1 == 3) {
                      // all on dart4 color
                      lightsOn(dart4);
                    } else if (data1 == 4) {
                      // all on dart5 color
                      lightsOn(dart5);
                    } else if (data1 == 5) {
                      // all on background color
                      lightsOn(backGround);
                    }
                    
                    break;
                  case 8:
                  // pallet color show
                    startPaletteShow();
                    break;
                  case 9:
                  // rainbow color show
                    startRainbowShow();
                    break;
                    
                  default:
                    stopTimer();
                    allOff();
                    break;
                }
            } else if (data2 == 0x02) {
              // reset
            }
        } else if (data0 == 0x02) { // Mode
            mode = data2;
        } else if (data0 == 0x03) { // RGB Values
            // DART1
            dart1.r = data1;
            dart1.g = data2;
        } else if (data0 == 0x04) {
            // DART1
            dart1.b = data2;
        } else if (data0 == 0x05) {
            // DART2
            dart2.r = data1;
            dart2.g = data2;
        } else if (data0 == 0x06) {
            // DART2
            dart2.b = data2;
        } else if (data0 == 0x07) {
            // DART3
            dart3.r = data1;
            dart3.g = data2;
        } else if (data0 == 0x08) {
            // DART3
            dart3.b = data2;
        } else if (data0 == 0x09) {
            // DART4
            dart4.r = data1;
            dart4.g = data2;
        } else if (data0 == 0x0a) {
            // DART4
            dart4.b = data2;
        } else if (data0 == 0x0b) {
            // DART5
            dart5.r = data1;
            dart5.g = data2;
        } else if (data0 == 0x0c) {
            // DART5
            dart5.b = data2;
        } else if (data0 == 0x0d) {
            // bg
            backGround.r = data1;
            backGround.g = data2;
        } else if (data0 == 0x0e) {
            // bg
            backGround.b = data2;
        } else if (data0 == 0x0f) {
            // brightness
            brightness = data2;
            setBrightness();
        } else if (data0 == 0x10) {
            // setColor
            switch (data2) {
                  case 0:
                    setColor = dart1;
                    break;
                  case 1:
                    setColor = dart2;
                    break;
                  case 2:
                    setColor = dart3;
                    break;
                  case 3:
                    setColor = dart4;
                    break;
                  case 4:
                    setColor = dart5;
                    break;
                  case 5:
                    setColor = backGround;
                    break;

                  default:
                    stopTimer();
                    allOff();
                    break;
                }
        }
    }   // end while loop
    ble_do_events();  

    if (!ble_connected()) {
        DEBUG_PRINTLN("BLE did not connect");
    } else if (!loaded) {
        DEBUG_PRINTLN("BLE Connected");
        loaded = 1;
    }
        
}   // end of loop
