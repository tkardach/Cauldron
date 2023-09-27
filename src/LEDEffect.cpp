#include "LEDEffect.h"

#include <math.h>

namespace led {
namespace {

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t wheel(LEDStrip& strip, byte pos) {
  if(pos < 85) {
   return strip.color(pos * 3, 255 - pos * 3, 0);
  } else if(pos < 170) {
   pos -= 85;
   return strip.color(255 - pos * 3, 0, pos * 3);
  } else {
   pos -= 170;
   return strip.color(0, pos * 3, 255 - pos * 3);
  }
}

} // namespace

void GlimmerEffect::playAffect(LEDStrip& strip) {
  const int x_max = strip.numPixels();
}

void RainbowEffect::playAffect(LEDStrip& strip) {
  uint16_t i, j;

  for(j=0; j<256; j++) { // 1 cycle of all colors on wheel
    for(i=0; i< strip.numPixels(); i++) {
      uint32_t color = wheel(strip, ((i * 256 / strip.numPixels()) + j) & 255);
      strip.setPixelColor(i, color);
    }
    strip.show();
  }
}

} // namespace led