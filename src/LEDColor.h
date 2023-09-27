#pragma once

#include "application.h"

namespace led {

struct LEDColor
{
    public:
        LEDColor(uint8_t r, uint8_t g, uint8_t b, uint8_t intensity)
            : _g(g), _b(b), _r(r), _intensity(intensity) {}
        LEDColor(uint8_t r, uint8_t g, uint8_t b, uint8_t w, uint8_t intensity)
            : _g(g), _b(b), _r(r), _w(w), _intensity(intensity) {}

        void r(uint8_t r) { _r = r; }
        uint8_t r() const { return _r; }
    
        void g(uint8_t g) { _g = g; }
        uint8_t g() const { return _g; }
    
        void b(uint8_t b) { _b = b; }
        uint8_t b() const { return _b; }
    
        void w(uint8_t w) { _w = w; }
        uint8_t w() const { return _w; }
        
        void intensity(uint8_t intensity) { _intensity = intensity; }
        uint8_t intensity() const { return _intensity; }

        uint32_t getColor() const;
    
    private:
        uint8_t _g;
        uint8_t _b;
        uint8_t _r;
        uint8_t _w;
        uint8_t _intensity;
};

} // namespace led