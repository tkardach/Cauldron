import asyncio
from bleak import BleakClient, BleakGATTCharacteristic
import led_effect
from led_strip import RgbArrayStrip, PixelOrder, LedStrip
from players import LedEffectPlayer, Handle
import sys


LED_UUID = "c8c9b555-53a3-46f6-97d0-4e642b6d4526"
NUM_PIXELS = 50


def test_bubbling_effect(strip: LedStrip):
    colors = ([142, 75, 166], [0, 255, 0])
    bubble_lengths = [7, 9, 11]
    bubble_pop_speeds = [3000, 4000, 5000]
    weights = [0.5, 0.25, 0.25]

    # bubble_effect = led_effect.BubblingEffect(
    #     strip,
    #     colors[0],
    #     colors[1],
    #     bubble_lengths,
    #     weights,
    #     bubble_pop_speeds,
    #     weights,
    #     10,
    #     0.05,
    # )
    bubble_effect = led_effect.SineWaveEffect(
        strip,
        colors[0],
        colors[1],
        oscillate=True,
        b=5,
        oscillation_speed_ms=1000,
    )
    player = LedEffectPlayer(bubble_effect)
    strip.fill(colors[0])
    return player.loop()


async def main():
    async with BleakClient("FD:6E:13:0F:51:C5", timeout=30) as client:
        strip = RgbArrayStrip(NUM_PIXELS)
        strip.brightness = 0.4
        handle = test_bubbling_effect(strip)
        try:
            while True:
                brightness = int(strip.brightness * 255)
                data = (
                    brightness.to_bytes(1, "big")
                    + strip.get_pixels(PixelOrder.BGR).tobytes()
                )
                await client.write_gatt_char(
                    LED_UUID,
                    data,
                    response=False,
                )
        except KeyboardInterrupt:
            pass
        finally:
            handle.stop()


# Using asyncio.run() is important to ensure that device disconnects on
# KeyboardInterrupt or other unhandled exception.
asyncio.run(main())
# strip = RgbArrayStrip(NUM_PIXELS)

# x = b""
# for i in range(151):
#     x += b"\xFF"
# print(sys.getsizeof(x))
# brightness = int(strip.brightness * 255)
# data = (
#     brightness.to_bytes(1, "big") + strip.get_pixels(PixelOrder.BGR).tobytes()
# )
# print(sys.getsizeof(data))
