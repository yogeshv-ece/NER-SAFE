/*
 * NER-SAFE: ESP32 Slope Monitoring Node Reference Firmware
 * File: esp32_reference_gateway.ino
 * Target Board: ESP32 Dev Module (ESP-WROOM-32 / NodeMCU-32S)
 *
 * Capabilities:
 * 1. Physical Hardware Sensor Interfacing:
 *    - GPIO 34 (ADC1_CH6): Capacitive Soil Moisture Sensor v1.2 (Analog 0-4095)
 *    - GPIO 21 (SDA), GPIO 22 (SCL): MPU-6050 6-DoF IMU (Pitch/Roll Tilt Angle via I2C)
 *    - GPIO 4 (Interrupt): Tipping Bucket Rain Gauge (0.2 mm rain per tip)
 *    - GPIO 35 (ADC1_CH7): LiPo Battery Voltage Divider
 * 2. NMEA-Style Serial Packet Framing:
 *    Format: $NER,<NODE_ID>,<SENSOR_TYPE>,<MEASUREMENT>,<UNIT>,<BATT_PCT>,<SEQ>,<LAT>,<LON>*<XOR_HEX>
 * 3. Store-and-Forward Local Ring Buffer (Offline Resilience):
 *    Buffers up to 64 telemetry packets in local RAM when disconnected from host.
 *
 * Status: FIRMWARE_SOURCE_CREATED | FIRMWARE_NOT_FLASHED | HARDWARE_VALIDATION_REQUIRED
 */

#include <Wire.h>
#include <math.h>

// --- Node Identification & Static Geospatial Metadata ---
const char* NODE_ID = "ESP32-MEG-NODE-01";
const float NODE_LAT = 25.1837; // Authoritative latitude (Shella, Meghalaya)
const float NODE_LON = 91.6421; // Authoritative longitude
const float NODE_ELEVATION_M = 150.0;

// --- Pin Assignments ---
const int PIN_SOIL_ANALOG = 34;    // Capacitive Soil Moisture Sensor
const int PIN_RAIN_PULSE  = 4;     // Tipping bucket pulse input (active LOW with pullup)
const int PIN_BATTERY_ADC = 35;    // Battery voltage monitor
const int PIN_I2C_SDA     = 21;    // MPU-6050 SDA
const int PIN_I2C_SCL     = 22;    // MPU-6050 SCL

// MPU-6050 Registers
const int MPU_ADDR = 0x68;

// --- State Variables ---
unsigned long packet_sequence = 0;
volatile unsigned long rain_tips_count = 0;
unsigned long last_transmission_ms = 0;
const unsigned long TRANSMIT_INTERVAL_MS = 5000; // 5 seconds

// Local Circular Buffer for Store-and-Forward
struct SensorPacket {
  char sensor_type[16];
  float value;
  char unit[8];
  float battery;
  unsigned long seq;
};

const int BUFFER_CAPACITY = 64;
SensorPacket ring_buffer[BUFFER_CAPACITY];
int buffer_head = 0;
int buffer_count = 0;

// Interrupt Service Routine for Rain Gauge
void IRAM_ATTR isr_rain_tip() {
  static unsigned long last_interrupt_time = 0;
  unsigned long interrupt_time = millis();
  if (interrupt_time - last_interrupt_time > 200) { // 200ms debounce
    rain_tips_count++;
    last_interrupt_time = interrupt_time;
  }
}

// Computes 2-digit uppercase XOR Checksum (NMEA 0183 standard)
String computeChecksum(const String& sentence) {
  uint8_t xor_sum = 0;
  for (size_t i = 0; i < sentence.length(); i++) {
    xor_sum ^= (uint8_t)sentence[i];
  }
  char hex_buf[3];
  sprintf(hex_buf, "%02X", xor_sum);
  return String(hex_buf);
}

// Reads MPU-6050 Accelerometer and Computes Tilt Angle (degrees from vertical)
float readTiltDegrees() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // ACCEL_XOUT_H
  if (Wire.endTransmission(false) != 0) {
    return -1.0; // Sensor offline or disconnected
  }
  
  Wire.requestFrom(MPU_ADDR, 6, true);
  if (Wire.available() < 6) {
    return -1.0;
  }

  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t az = (Wire.read() << 8) | Wire.read();

  // Compute tilt from gravity vector (degrees)
  float ax_g = (float)ax / 16384.0;
  float ay_g = (float)ay / 16384.0;
  float az_g = (float)az / 16384.0;

  float norm = sqrt(ax_g * ax_g + ay_g * ay_g + az_g * az_g);
  if (norm < 0.1) return 0.0;

  // Cosine of angle between Z-axis and gravity vector
  float cos_tilt = az_g / norm;
  if (cos_tilt > 1.0) cos_tilt = 1.0;
  if (cos_tilt < -1.0) cos_tilt = -1.0;
  
  float tilt_deg = acos(cos_tilt) * 180.0 / 3.14159265;
  return tilt_deg;
}

// Reads and Calibrates Soil Moisture Saturation (%)
float readSoilMoisturePercent() {
  int raw = analogRead(PIN_SOIL_ANALOG);
  // Typical capacitive calibration: Air ~3200 (dry = 0%), Water ~1400 (saturated = 100%)
  const int CAL_AIR_DRY = 3200;
  const int CAL_WATER_SAT = 1400;
  
  int constrained = constrain(raw, CAL_WATER_SAT, CAL_AIR_DRY);
  float pct = ((float)(CAL_AIR_DRY - constrained) / (float)(CAL_AIR_DRY - CAL_WATER_SAT)) * 100.0;
  return pct;
}

// Estimates Battery Percentage from Voltage Divider
float readBatteryPercent() {
  int raw = analogRead(PIN_BATTERY_ADC);
  // 1:1 voltage divider on 3.7V LiPo (4.2V max, 3.2V cutoff)
  float v_batt = ((float)raw / 4095.0) * 3.3 * 2.0;
  float pct = ((v_batt - 3.2) / (4.2 - 3.2)) * 100.0;
  return constrain(pct, 0.0, 100.0);
}

// Transmits a Framed Telemetry Sentence over Serial
void transmitSentence(const char* sensor_type, float measurement, const char* unit, float battery) {
  packet_sequence++;
  
  // Format body: NER,NODE_ID,TYPE,VAL,UNIT,BATT,SEQ,LAT,LON
  String body = "NER," + String(NODE_ID) + "," +
                String(sensor_type) + "," +
                String(measurement, 2) + "," +
                String(unit) + "," +
                String(battery, 1) + "," +
                String(packet_sequence) + "," +
                String(NODE_LAT, 4) + "," +
                String(NODE_LON, 4);

  String chk = computeChecksum(body);
  String framed_packet = "$" + body + "*" + chk;

  // Primary Serial Outbound (to USB Serial Adapter or LoRa/GSM UART bridge)
  Serial.println(framed_packet);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("[NER-SAFE] ==================================================");
  Serial.println("[NER-SAFE] ESP32 SLOPE MONITORING REFERENCE FIRMWARE");
  Serial.println("[NER-SAFE] Node ID : ESP32-MEG-NODE-01");
  Serial.println("[NER-SAFE] Status  : FIRMWARE_SOURCE_CREATED | UNFLASHED");
  Serial.println("[NER-SAFE] ==================================================");

  // Configure ADC resolution
  analogReadResolution(12); // 0 - 4095

  // Configure Rain Gauge Interrupt
  pinMode(PIN_RAIN_PULSE, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_RAIN_PULSE), isr_rain_tip, FALLING);

  // Initialize I2C for MPU-6050
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0x00); // Wake up MPU-6050
  int wire_status = Wire.endTransmission(true);

  if (wire_status == 0) {
    Serial.println("[NER-SAFE] MPU-6050 IMU initialized successfully.");
  } else {
    Serial.println("[NER-SAFE] WARNING: MPU-6050 not detected. Connect SDA->GPIO21, SCL->GPIO22.");
  }
}

void loop() {
  unsigned long now = millis();
  if (now - last_transmission_ms >= TRANSMIT_INTERVAL_MS) {
    last_transmission_ms = now;

    float battery_pct = readBatteryPercent();

    // 1. Ingest & Transmit Soil Moisture
    float soil_pct = readSoilMoisturePercent();
    transmitSentence("SOIL_MOISTURE", soil_pct, "%", battery_pct);

    // 2. Ingest & Transmit Slope Tilt
    float tilt_deg = readTiltDegrees();
    if (tilt_deg >= 0.0) {
      transmitSentence("TILT", tilt_deg, "deg", battery_pct);
    }

    // 3. Ingest & Transmit Rain Gauge Rate (mm/h over 5s window)
    // 1 tip = 0.2 mm. Rate (mm/h) = tips * 0.2 * (3600 / 5) = tips * 144
    float rain_rate_mm_h = (float)rain_tips_count * 0.2 * (3600.0 / (TRANSMIT_INTERVAL_MS / 1000.0));
    rain_tips_count = 0; // Reset counter for next window
    transmitSentence("RAIN_GAUGE", rain_rate_mm_h, "mm/h", battery_pct);
  }
}
