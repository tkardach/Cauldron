
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

LEDColor::LEDColor(uint8_t r, uint8_t g, uint8_t b)
{
    _r = r;
    _g = g;
    _b = b;
}

uint8_t LEDColor::r()
{
    return _r;
}

void LEDColor::r(uint8_t r)
{
    _r = r;
}

uint8_t LEDColor::g()
{
    return _g;
}

void LEDColor::g(uint8_t g)
{
    _g = g;
}


uint8_t LEDColor::b()
{
    return _b;
}

void LEDColor::b(uint8_t b)
{
    _b = b;
}

uint8_t LEDColor::intense()
{
    return _intense;
}

void LEDColor::intense(uint8_t intense)
{
    _intense = intense;
}