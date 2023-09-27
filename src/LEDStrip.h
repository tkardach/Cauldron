#pragma once

#include "LEDColor.h"

namespace led {

// TODO: investigate if there are other LED light strip libraries, if
// Adafruit is the only one, this LEDStrip class is redundant.

// Abstract wrapper class around LED light strip library. This allows
// our code to work accross different LED light strip types.
class LEDStrip {
  public:
    // Color all LEDs in the LEDStrip the 
    virtual void fill(const LEDColor& color) = 0;
    virtual void setPixelColor(int index, const LEDColor& color) = 0;
    virtual void setPixelColor(int index, uint32_t color) = 0;
    virtual int numPixels() const = 0;

    virtual uint32_t color(uint8_t r, uint8_t g, uint8_t b) = 0;

    virtual void begin() = 0;
    virtual void show() = 0;
};

} // namespace led