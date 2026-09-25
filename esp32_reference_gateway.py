"""
NER-SAFE: ESP32 Hardware Reference Gateway & Protocol Specification
Provides reference protocol encoding, serial sentence generation, and test emulator
for physical ESP32 slope monitoring nodes.

Protocol Format:
$NER,<NODE_ID>,<SENSOR_TYPE>,<MEASUREMENT>,<UNIT>,<BATT_PCT>,<SEQ>,<LAT>,<LON>*<XOR_HEX>
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ground_sensor_interface import (
    ground_sensor_adapter, SENSOR_TILT, SENSOR_SOIL_MOISTURE,
    SENSOR_RAIN_GAUGE, SENSOR_TEMPERATURE
)

def compute_checksum(sentence_body: str) -> str:
    """Computes NMEA-style XOR checksum for sentence."""
    csum = 0
    for ch in sentence_body:
        csum ^= ord(ch)
    return f"{csum:02X}"

class ESP32ReferenceNode:
    """Emulates a physical ESP32 slope monitoring node transmitting sensor packets."""
    def __init__(self, node_id: str = "ESP32-MEG-NODE-01", lat: float = 25.1837, lon: float = 91.6421):
        self.node_id = node_id
        self.latitude = lat
        self.longitude = lon
        self.sequence = 0
        self.battery = 98.5

    def build_packet(self, sensor_type: str, value: float, unit: str) -> str:
        """Constructs a certified $NER serial telemetry packet."""
        self.sequence += 1
        self.battery = max(5.0, self.battery - 0.05) # Simulated battery drain
        
        body = f"NER,{self.node_id},{sensor_type},{value:.2f},{unit},{self.battery:.1f},{self.sequence},{self.latitude:.4f},{self.longitude:.4f}"
        chk = compute_checksum(body)
        return f"${body}*{chk}"

    def send_to_adapter(self, sensor_type: str, value: float, unit: str) -> Dict[str, Any]:
        """Encodes and directly delivers packet to the local ground sensor adapter."""
        packet_str = self.build_packet(sensor_type, value, unit)
        return ground_sensor_adapter.parse_serial_packet(packet_str, gateway_id="ESP32_USB_GATEWAY")

# Arduino / ESP-IDF C++ Reference Firmware Source
ESP32_FIRMWARE_SKETCH = """
/*
 * NER-SAFE: ESP32 Slope Sensor Node Reference Firmware
 * Board: ESP32 Dev Module (WROOM-32 / NodeMCU)
 * Hardware Pins:
 *   - GPIO 34 (ADC1): Capacitive Soil Moisture Sensor v1.2
 *   - GPIO 21 (SDA), GPIO 22 (SCL): MPU6050 6-DOF IMU (Tilt Angle)
 *   - GPIO 4 (Pulse Input): Tipping Bucket Rain Gauge (0.2mm tip)
 */

#include <Wire.h>
#include <WiFi.h>

const char* NODE_ID = "ESP32-MEG-NODE-01";
const float NODE_LAT = 25.1837;
const float NODE_LON = 91.6421;
unsigned long seq = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  analogReadResolution(12); // 12-bit ADC (0-4095)
  delay(1000);
  Serial.println("[NER-SAFE] ESP32 Slope Node Initialized.");
}

String computeXOR(String msg) {
  uint8_t c = 0;
  for (int i = 0; i < msg.length(); i++) {
    c ^= msg[i];
  }
  char hexBuf[3];
  sprintf(hexBuf, "%02X", c);
  return String(hexBuf);
}

void loop() {
  seq++;
  
  // 1. Read Soil Moisture (Analog 0-4095 mapped to 0-100% saturation)
  int rawADC = analogRead(34);
  float soilPct = constrain(map(rawADC, 3200, 1400, 0, 100), 0, 100);
  
  // 2. Transmit Soil Packet
  String soilBody = "NER," + String(NODE_ID) + ",SOIL_MOISTURE," + String(soilPct, 1) + ",%,95.0," + String(seq) + "," + String(NODE_LAT, 4) + "," + String(NODE_LON, 4);
  Serial.println("$" + soilBody + "*" + computeXOR(soilBody));
  
  delay(5000); // 5-second interval
}
"""

def get_firmware_code() -> str:
    return ESP32_FIRMWARE_SKETCH.strip()
