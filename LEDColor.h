#ifndef LEDCOLOR_H
#define LEDCOLOR_H

#include "application.h"

class LEDColor
{
    public:
        LEDColor(uint8_t r, uint8_t g, uint8_t b);  // constructor

        // setters/getters
        void r(uint8_t r);
        uint8_t r();
    
        void g(uint8_t g);
        uint8_t g();
    
        void b(uint8_t b);
        uint8_t b();
        
        void intense(uint8_t b);
        uint8_t intense();
    
    private:
        uint8_t _r;
        uint8_t _g;
        uint8_t _b;
        uint8_t _intense;
};

#endif