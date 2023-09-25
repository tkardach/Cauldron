// This #include statement was automatically added by the Particle IDE.
#include "LEDColor.h"

// This #include statement was automatically added by the Particle IDE.
#include <neopixel.h>
#include "application.h"

LEDColor *led1 = new LEDColor(255, 70, 0);   // orange
LEDColor *led2 = new LEDColor(105, 105, 105); // gun metal
LEDColor *led3 = new LEDColor(192, 192, 192);    // silver
LEDColor *led4 = new LEDColor(30, 144, 255);     // blue
LEDColor *led5 = new LEDColor(255, 0, 255);      // magenta
LEDColor *bg = new LEDColor(255, 255, 153); // warm yellow
LEDColor *black = new LEDColor(255, 255, 255);  // black
LEDColor *white = new LEDColor(0, 0, 0);  // white

Timer *interTimer;      // pointer for timer
const int firmwareVersion = 191; // divide by 10 to get 1.9, ...

/* ======================= prototypes =============================== */
void colorAll(uint32_t c, uint8_t wait);
void colorWipe(uint32_t c, uint8_t wait);
void rainbow(uint8_t wait);
void rainbowCycle(uint8_t wait);
uint32_t Wheel(byte WheelPos);

void setPixelColorDim(uint16_t led, LEDColor *color, uint8_t dim);
void ledDim(int bank, uint8_t dim);
void allLedsDim(uint8_t dim);
void backDim(int bank, uint8_t dim);
void allBackDim(uint8_t dim);
void allOff();

void blinkLeds();
void startBlinkingLeds(uint16_t interval);
void stopLedsTimer();

void runningBankLeds();
void startRunningBankLeds(uint16_t interval);
void startRunningDuelLeds(uint16_t interval);
void startRunningSingleLed(uint16_t interval);
void runningLed();
void runningLeds();

void duelLedsOn(int led, uint8_t dim);
void singleLedOn(int led, uint8_t dim);
LEDColor getLedColor(int led);
int LedLessTen(int led);



#define PIXEL_COUNT 50  // number of LEDs in strip
#define PIXEL_PIN D1    // dataline for the LED strip
#define PIXEL_TYPE WS2811   // LED controller used

int HALF_PIXEL_COUNT = PIXEL_COUNT / 2;

Adafruit_NeoPixel strip = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);

// functions
// Set all pixels in the strip to a solid color, then wait (ms)
void colorAll(uint32_t c, uint8_t wait) {
  uint16_t i;

  for(i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
  }
  strip.show();
  delay(wait);
}

// Fill the dots one after the other with a color, wait (ms) after each one
void colorWipe(uint32_t c, uint8_t wait) {
  for(uint16_t i = 0; i < strip.numPixels(); i++) {
    strip.setPixelColor(i, c);
    strip.show();
    delay(wait);
  }
}

void rainbow(uint8_t wait) {
  uint16_t i, j;

  for(j = 0; j < 256; j++) {
    for(i = 0; i < strip.numPixels(); i++) {
      strip.setPixelColor(i, Wheel((i + j) & 255));
    }
    strip.show();
    delay(wait);
  }
}

// Slightly different, this makes the rainbow equally distributed throughout, then wait (ms)
void rainbowCycle(uint8_t wait) {
  uint16_t i, j;

  for(j = 0; j < 256; j++) { // 1 cycle of all colors on wheel
    for(i = 0; i < strip.numPixels(); i++) {
      strip.setPixelColor(i, Wheel(((i * 256 / strip.numPixels()) + j) & 255));
    }
    strip.show();
    delay(wait);
  }
}

// Input a value 0 to 255 to get a color value.
// The colors are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}

void setPixelColorDim(uint16_t led, LEDColor *color, uint8_t dim) {
    strip.setColorDimmed(led, color->r(), color->g(), color->b(), dim);
}

void runningLeds(){
    static int led = 1;
    duelLedOn(led, 255);
    
    led += 2;
    if (led >= PIXEL_COUNT)
        led = 1;
}

void runningLed() {
    static int led = 1;
    singleLedOn(led, 255);
    
    led += 2;
    if(led >= PIXEL_COUNT)
        led = 1;
}

void startRunningDuelLeds(uint16_t interval)  {
    interTimer = new Timer(interval, runningLeds);
    interTimer->start();
}

void startRunningSingleLed(uint16_t interval)  {
    //Serial.printlnf("Start Running Single LED");
    interTimer = new Timer(interval, runningLed);
    interTimer->start();
}

void duelLedOn(int led, uint8_t dim) {
    //Serial.printlnf("led: %d", led);
    singleLedOn(led, dim);
    int secondLed = led;
    if (led < HALF_PIXEL_COUNT)
        secondLed = led + HALF_PIXEL_COUNT;
    else {
        secondLed = led - HALF_PIXEL_COUNT;
    }
    singleLedOn(secondLed, dim);
}

//  passed an odd number, figures out the color, then turns previous dart off, new dart on
void singleLedOn(int led, uint8_t dim)  {
    int colorInt = ledLessTen(led);
    //Serial.printlnf("led: %d Off, colorInt: %d", led, colorInt);
    setLedColor(led, colorInt, 0);
    int nxtLed = led + 2;
    if(nxtLed >= PIXEL_COUNT)
        nxtLed = 1;
    colorInt = ledLessTen(nxtLed);
    //Serial.printlnf("led: %d On, colorInt: %d", nxtLed, colorInt);
    setLedColor(nxtLed, colorInt, dim);  // turns on dart
}

void setLedColor(int led, int color, uint8_t dim) {
    if(color == 1) {
        setPixelColorDim(led, led1, dim);
    } else if(color == 3) {
        setPixelColorDim(led, led2, dim);
    } else if(color == 5) {
        setPixelColorDim(led, led3, dim);
    } else if(color == 7) {
        setPixelColorDim(led, led4, dim);
    } else if(color == 9) {
        setPixelColorDim(led, led5, dim);
    }
    strip.show(); 
}

// this turns on the even LEDs in 5 colors, and a dim white LED
void ledDim(int bank, uint8_t dim)  {
    uint gunDim = dim;
    if(dim < HALF_PIXEL_COUNT) {
        gunDim = 0;
    }
    // even, set to one of five dart colors
    bank = bank * 10;
    setPixelColorDim(bank + 1, led1, dim);   // orange
    setPixelColorDim(bank + 3, led2, gunDim); // gun metal
    setPixelColorDim(bank + 5, led3, dim); // silver
    setPixelColorDim(bank + 7, led4, dim); // blue
    setPixelColorDim(bank + 9, led5, dim); // magenta
}

// returns a number less than 10, recursive function
int ledLessTen(int led)  {
    if(led < 10) {
        return led;
    } else {
        ledLessTen(led - 10);
    }
    return 0;   // should never get here
}

void allLedsDim(uint8_t dim) {
    for(int bank = 0; bank < 10; bank++) {
        ledDim(bank, dim);
    }
}

void runningBankLeds() {
    static int bank = 0;
    // take bank and blank it
    // increment bank, check for roll-over
    // turn bank on
    ledDim(bank, 0);
    bank++;
    if(bank > 9) {
        bank = 0;
    }
    ledDim(bank, 255);
    strip.show();
}

void startRunningBankLeds(uint16_t interval)  {
    interTimer = new Timer(interval, runningBankLeds);
    interTimer->start();
}

void broadwayLeds() {
    static bool blink = false;
    blink = !blink;
    if(blink) {
        for(int led = 1; led < PIXEL_COUNT; led += 4) {
             singleLedOn(led, 255);
        }
    } else {
        for(int led = 3; led < PIXEL_COUNT; led += 4) {
             singleLedOn(led, 255);
        }
    }
    strip.show();
}

void startBroadwayLeds(uint16_t interval)  {
    interTimer = new Timer(interval, broadwayLeds);
    interTimer -> start();
}

void blinkLeds() {
    static bool blink = false;
    blink = !blink;
    if(blink) {
        allLedsDim(255);
        strip.show();
    } else {
        allLedsDim(0);
        strip.show();
    }
}

void startBlinkingLeds(uint16_t interval)  {
    interTimer = new Timer(interval, blinkLeds);
    interTimer -> start();
}

void stopLedsTimer() {
    interTimer -> stop();
    interTimer -> dispose();
}

// this turns on the Leds (even LEDs) in 5 colors, and a dim white LED
void backDim(int bank, uint8_t dim) {
    bank = bank * 10;
    // odd so set to white
    for (int i = 0; i < 5; i++) {
        setPixelColorDim(bank + 2 * i, bg, dim);   // dim yellow white
    }
}


// set all banks to slight yellow dim
void allBackDim(uint8_t dim) {
    for(int bank = 0; bank < 10; bank++) {
        backDim(bank, dim);
    }
}

// sets all pixels to off/black
void allOff() {
    for(uint8_t led = 0; led < strip.numPixels(); led++) {
        setPixelColorDim(led, black, 0);
    }
}


void setup() {
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
  
}

void loop() {

}