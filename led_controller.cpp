// This #include statement was automatically added by the Particle IDE.
#include <neopixel.h>

#include <array>

#include "Particle.h"


#define BRIGHTNESS_START_INDEX 0
#define LED_START_INDEX 1
#define PIXEL_COUNT 50
#define PIXEL_PIN D2
#define PIXEL_TYPE WS2811

constexpr unsigned int udpPort = 5456;

const BleUuid ledStreamService("57dbeaa0-e776-4f99-b451-903d371ade07");
const BleUuid ledStream("c8c9b555-53a3-46f6-97d0-4e642b6d4526");

void onDataReceived(const uint8_t* data, size_t len, const BlePeerDevice& peer, void* context);

// Instantiate variables
Adafruit_NeoPixel strip(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);
SerialLogHandler logHandler;
BleCharacteristic ledStreamCharacteristics("led info", BleCharacteristicProperty::WRITE_WO_RSP, ledStream,
                                           ledStreamService, onDataReceived, NULL);
uint8_t buffer[(PIXEL_COUNT * 3) + 1];
uint8_t latestFrame[PIXEL_COUNT * 3];
UDP Udp;
bool ipPrinted = false;

// Decyphers a buffer into Led data, and writes this data to the Led strip
void writeBytes(const uint8_t* data, size_t len) {
    strip.setBrightness(data[BRIGHTNESS_START_INDEX]);
    // Copy the pixel data to the LED strip
    size_t led_len = len - sizeof(uint8_t);
    if (led_len > 0) {
        int num_leds = led_len / 3;
        for (int i=0; i<num_leds; i++) {
            uint32_t color = 0;
            memcpy(&color, &data[LED_START_INDEX + (i * 3)], sizeof(uint8_t) * 3);
            strip.setPixelColor(i, color);
        }
        // memcpy(strip.getPixels(), &data[LED_START_INDEX], led_len);
    }
    // Set the brightness based on the first byte of data
    strip.setBrightness(data[BRIGHTNESS_START_INDEX]);
    strip.show();
}

void writeUdpBytes(const uint8_t* data, size_t len) {
    if (len != PIXEL_COUNT * 3) {
        Log.warn("Ignoring UDP frame with unexpected size: %lu", (unsigned long)len);
        return;
    }

    // UdpStreamStrip sends a complete frame as raw RGB bytes, with no header.
    strip.setBrightness(255);
    for (int i = 0; i < PIXEL_COUNT; i++) {
        size_t pixel_offset = i * 3;
        strip.setPixelColor(i, data[pixel_offset], data[pixel_offset + 1], data[pixel_offset + 2]);
    }
    strip.show();
}

// Callback function responsible for writing the LED data from the stream to the neopixel strip
void onDataReceived(const uint8_t* data, size_t len, const BlePeerDevice& peer, void* context) {
    writeBytes(data, len);
}

void setup_ble() {
    WiFi.off();
    
    // Initialize BLE
    BLE.on();
    BLE.selectAntenna(BleAntennaType::EXTERNAL);
    BLE.setDeviceName("led_stream");

    BLE.addCharacteristic(ledStreamCharacteristics);
    
    // Advertise Led Stream service
    BleAdvertisingData advData;
    advData.appendServiceUUID(ledStreamService);
    BLE.advertise(&advData);
}

void setup_udp() {
  // Start the UDP
  Udp.begin(udpPort);
}

void setup() {
    // Initialize neopixel strip
    strip.begin();
    strip.show();
    
    // Initialize the UDP endpoint
    setup_udp();
    
    Serial.begin(9600);
}

void loop() {
    static bool ipPublished = false;
    if (!ipPublished && WiFi.ready() && Particle.connected()) {
        String ipString = WiFi.localIP().toString();
        // This sends a public event to the Particle Cloud console
        Particle.publish("device_ip", ipString, PRIVATE);
        
        // This also outputs to the cloud logging stream via Log.info
        Log.info("localIP=%s", ipString.c_str());
        
        ipPublished = true;
    }

    // Drain queued packets but display only the newest frame, avoiding stale
    // frames being replayed back-to-back when UDP delivery is bursty.
    int count;
    bool frameReceived = false;
    while ((count = Udp.receivePacket(buffer, sizeof(buffer))) >= 0) {
        if (count == PIXEL_COUNT * 3) {
            memcpy(latestFrame, buffer, sizeof(latestFrame));
            frameReceived = true;
        } else if (count > 0) {
            Log.warn("Ignoring UDP frame with unexpected size: %lu", (unsigned long)count);
        }
    }
    if (frameReceived) {
        writeUdpBytes(latestFrame, sizeof(latestFrame));
    }
    
    // Catch fatal socket errors (ignoring normal -1 'no packet' states)
    if (count < -1) {
        Udp.begin(udpPort);
    }
}