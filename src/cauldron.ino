/* ======================= includes ================================= */

#include "application.h"
//#include "neopixel/neopixel.h" // use for Build IDE
#include "neopixel.h" // use for local build
#include "NeopixelStrip.h"
#include "LEDColor.h"
#include "LEDEffect.h"

/* ======================= prototypes =============================== */

// void colorAll(uint32_t c, uint8_t wait);
// void colorWipe(uint32_t c, uint8_t wait);
// void rainbow(uint8_t wait);
// void rainbowCycle(uint8_t wait);
// uint32_t Wheel(byte WheelPos);
// void dartDim(uint8_t dimDart, uint8_t dimWhite, uint8_t wait);

/* ======================= extra-examples.cpp ======================== */

SYSTEM_MODE(AUTOMATIC);

#define PIXEL_COUNT 100 // number of LEDs in two strips chained together
#define PIXEL_PIN D1    // dataline for the LED strip
#define PIXEL_TYPE WS2811   // LED controller used

using namespace led;

std::unique_ptr<LEDStrip> strip;

// IMPORTANT: To reduce NeoPixel burnout risk, add 1000 uF capacitor across
// pixel power leads, add 300 - 500 Ohm resistor on first pixel's data input

void setup() {
  strip = std::make_unique<NeopixelStrip>(std::make_unique<Adafruit_NeoPixel>(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE));
  strip->begin();
  strip->show(); // Initialize all pixels to 'off'
}

void loop() {
  // Some example procedures showing how to display to the pixels:
  // Do not run more than 15 seconds of these, or the b/g tasks
  // will be blocked.
  //--------------------------------------------------------------

  //strip->setPixelColor(0, strip->Color(255, 0, 255));
  //strip->show();

  //colorWipe(strip->Color(255, 0, 0), 50); // Red

  //colorWipe(strip->Color(0, 255, 0), 50); // Green

  //colorWipe(strip->Color(0, 0, 255), 50); // Blue

  //rainbow(20);

  // rainbowCycle(20);

  //colorAll(strip->Color(0, 255, 255), 50); // Cyan
  // dartDim(100, 50, 50);

  RainbowEffect effect;
  effect.playAffect(*strip);
}

// // this turns on the Darts (even LEDs) in 5 colors, and a dim white LED
// void dartDim(uint8_t dimDart, uint8_t dimWhite, uint8_t wait) 
// {
//     for (uint16_t led=0; led<strip->numPixels(); led+=10) {
//         // odd so set to white
//         strip->setColorDimmed(led, 0, 0, 0, dimWhite);
//         strip->setColorDimmed(led+2, 0, 0, 0, dimWhite);
//         strip->setColorDimmed(led+4, 0, 0, 0, dimWhite);
//         strip->setColorDimmed(led+6, 0, 0, 0, dimWhite);
//         strip->setColorDimmed(led+8, 0, 0, 0, dimWhite);
//         // even, set to one of five dart colors
//         strip->setColorDimmed(led+1, 255, 140, 0, dimDart);   // orange
//         strip->setColorDimmed(led+3, 105, 105, 105, dimDart); // gun metal
//         strip->setColorDimmed(led+5, 192, 192, 192, dimDart); // silver
//         strip->setColorDimmed(led+7, 30, 144, 255, dimDart); // blue
//         strip->setColorDimmed(led+9, 255, 0, 255, dimDart); // magenta 
//         strip->show();
//     }
    
//     delay(wait);         
// }

// // Set all pixels in the strip to a solid color, then wait (ms)
// void colorAll(uint32_t c, uint8_t wait) {
//   uint16_t i;

//   for(i=0; i<strip->numPixels(); i++) {
//     strip->setPixelColor(i, c);
//   }
//   strip->show();
//   delay(wait);
// }

// // Fill the dots one after the other with a color, wait (ms) after each one
// void colorWipe(uint32_t c, uint8_t wait) {
//   for(uint16_t i=0; i<strip->numPixels(); i++) {
//     strip->setPixelColor(i, c);
//     strip->show();
//     delay(wait);
//   }
// }

// void rainbow(uint8_t wait) {
//   uint16_t i, j;

//   for(j=0; j<256; j++) {
//     for(i=0; i<strip->numPixels(); i++) {
//       strip->setPixelColor(i, Wheel((i+j) & 255));
//     }
//     strip->show();
//     delay(wait);
//   }
// }

// // Slightly different, this makes the rainbow equally distributed throughout, then wait (ms)
// void rainbowCycle(uint8_t wait) {
//   uint16_t i, j;

//   for(j=0; j<256; j++) { // 1 cycle of all colors on wheel
//     for(i=0; i< strip->numPixels(); i++) {
//       strip->setPixelColor(i, Wheel(((i * 256 / strip->numPixels()) + j) & 255));
//     }
//     strip->show();
//     delay(wait);
//   }
// }

// // Input a value 0 to 255 to get a color value.
// // The colours are a transition r - g - b - back to r.
// uint32_t Wheel(byte WheelPos) {
//   if(WheelPos < 85) {
//    return strip->Color(WheelPos * 3, 255 - WheelPos * 3, 0);
//   } else if(WheelPos < 170) {
//    WheelPos -= 85;
//    return strip->Color(255 - WheelPos * 3, 0, WheelPos * 3);
//   } else {
//    WheelPos -= 170;
//    return strip->Color(0, WheelPos * 3, 255 - WheelPos * 3);
//   }
// }
