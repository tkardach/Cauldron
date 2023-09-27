#pragma once

#include "LEDStrip.h"

namespace led {

// Performs an effect on a provided LEDStrip object
class LEDEffect {
  public:
    virtual void playAffect(LEDStrip& strip) = 0;
};

// Glimmer causes the lights to glow/glimmer in a sine-
// wave fashion. The provided high and low color values
// will provide a range that the sine-wave will operate
// on.
class GlimmerEffect : public LEDEffect {
  public:
    GlimmerEffect(LEDColor glow_high, LEDColor glow_low)
        : _glow_high(glow_high), _glow_low(glow_low) {}

    void playAffect(LEDStrip& strip) override;

  private:
    const LEDColor _glow_high;
    const LEDColor _glow_low;
};

class RainbowEffect : public LEDEffect {
  public:
    RainbowEffect() = default;

    void playAffect(LEDStrip& strip) override;
};

} // namespace led