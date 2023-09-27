
// this is for terminal printing during debug
//#define DEBUG 1
#ifdef DEBUG
 #define DEBUG_PRINT(x)  Serial.print(x)
 #define DEBUG_PRINTLN(x) Serial.println(x)
#else
 #define DEBUG_PRINT(x)
 #define DEBUG_PRINTLN(X)
#endif

#include "application.h"
#include "LEDColor.h"

namespace led {

/**
 * Represents the LEDColor structure as a 32-bit color value.
 * Returns the first 32-bits of LEDColor, in order from most
 * significant bit to least: WRGB.
*/
uint32_t LEDColor::getColor() const
{
    uint32_t color;
    memcpy(static_cast<void*>(std::addressof(color)),
           static_cast<const void*>(std::addressof(*this)),
           sizeof(color));
    return color;
}

} // namespace led