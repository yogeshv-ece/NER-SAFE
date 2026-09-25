# NER-SAFE: GROUND SENSOR HARDWARE REQUIREMENTS & SPECIFICATION

**Problem Statement**: SIH 26001 (Physical Ground Sensor Integration)  
**Target Terrain**: North Eastern Region (Steep Soil-Covered & Rock Slopes)  
**Document Status**: Authoritative Hardware Specification & Bill of Materials (BOM)  
**Date**: September 13, 2026  

---

## 1. OVERVIEW & HARDWARE SEPARATION

To bridge the gap between regional satellite remote sensing (GPM ~10 km, SMAP ~9 km) and slope-scale physical failure, NER-SAFE provides a hardware-neutral ground sensor ingestion interface.

This document clearly distinguishes between:
1. **Tier A: Minimum Demo Hardware** (Low-cost prototype for lab testing and demonstration with an ESP32).
2. **Tier B: Production Field Monitoring Node** (Ruggedized, solar-powered multi-sensor station for remote Himalayan deployment).

---

## 2. TIER A: MINIMUM DEMO HARDWARE (LOW-COST PROTOTYPE)

This configuration can be assembled with off-the-shelf maker components for under ₹2,000 (~$25 USD) to demonstrate live hardware telemetry to evaluators.

| Component | Recommended Model | Approximate Cost | Interface / Pinout | Role in NER-SAFE System |
| :--- | :--- | :---: | :--- | :--- |
| **Microcontroller** | **ESP32 Dev Module (WROOM-32)** | ₹450 | Micro-USB / CP2102 | Acquires analog/I2C signals, packages `$NER` serial sentences, posts to HTTP endpoint |
| **Soil Moisture Sensor** | **Capacitive Soil Moisture v1.2** | ₹120 | Analog Pin (GPIO 34) | Measures relative volumetric moisture without resistive probe corrosion |
| **Tilt / Inclinometer** | **MPU-6050 (6-DOF IMU)** | ₹180 | I2C (SDA: GPIO 21, SCL: GPIO 22) | Detects slope displacement and pitch/roll angle changes ($0^\circ\text{–}90^\circ$) |
| **Temperature Sensor** | Onboard MPU6050 / DS18B20 | ₹80 | I2C / 1-Wire (GPIO 4) | Monitors freezing/thawing cycles affecting slope stability |
| **Power Supply** | Standard USB Power Bank or 3.7V 18650 | ₹300 | 5V / 3.3V Regulator | Powers node during mobility and live demonstrations |
| **Wiring & Prototyping**| Breadboard + Dupont Jumpers | ₹100 | Solderless | Connects modular sensor breakout boards |
| **TOTAL (Tier A)** | | **~₹1,230** | | |

### Hardware Connection Diagram (Tier A):
```text
  +-------------------------------------------------------------+
  |                        ESP32 BOARD                          |
  |                                                             |
  |   3V3 ------------------+------------+                      |
  |   GND ------------------|-----+------|-----+                |
  |   GPIO 34 (ADC1) <------+     |      |     |                |
  |   GPIO 21 (SDA) <-------------|------+     |                |
  |   GPIO 22 (SCL) <-------------|------------+                |
  +-------------------------------|-----------------------------+
                                  |            |
             +--------------------+            +-------------------+
             | Capacitive Soil v1.2|            | MPU-6050 Gyro/Acc |
             | VCC: 3.3V           |            | VCC: 3.3V         |
             | GND: GND            |            | GND: GND          |
             | AOUT: GPIO 34       |            | SDA: GPIO 21      |
             +---------------------+            | SCL: GPIO 22      |
                                                +-------------------+
```

---

## 3. TIER B: PRODUCTION FIELD MONITORING NODE (HIMALAYAN SLOPES)

For operational deployment in remote landslide zones across Meghalaya and Mizoram (e.g., Shella, Sohra, Aizawl slopes), hardware must withstand high precipitation (>11,000 mm/year) and prolonged cloud cover.

| Subsystem | Component Specification | Role & Environmental Justification |
| :--- | :--- | :--- |
| **Core Controller** | Industrial Ultra-Low Power ESP32-S3 or STM32L4 | Deep sleep capability ($<15\,\mu\text{A}$), hardware crypto engine, watchdog timer |
| **Soil Hydrology** | Multi-Depth TDR / Frequency Domain SDI-12 Probe (Stevens HydraProbe / Campbell CS655) | Measures dielectric permittivity, electrical conductivity, and moisture at 30cm, 60cm, 100cm depths |
| **Slope Kinematics** | Dual-Axis MEMS Inclinometer (Murata SCA103T / Jewell Instruments) | Sub-milliradian resolution ($0.001^\circ$ precision) with temperature compensation |
| **Surface Hydrology** | Tipping Bucket Rain Gauge (0.2 mm / tip, pulse output) | Ground-truth precipitation calibration for satellite GPM IMERG feeds |
| **Subsurface Water** | Vibrating Wire Piezometer (Roctest / Encardio Rite) | Measures pore water pressure buildup in shear failure plane |
| **Long-Range Comms** | Semtech SX1262 LoRa Transceiver (868 MHz / 433 MHz) + SIM7600 4G LTE | Level 2/3 store-and-forward communications; 5–15 km range through mountain valleys |
| **Power Harvesting** | 20W Monocrystalline Solar Panel + 12V 12Ah LiFePO4 Battery + MPPT | Continuous operation through 14 consecutive days of heavy monsoon overcast |
| **Enclosure** | NEMA 4X / IP67 Die-Cast Aluminum with Gore vent | Prevents moisture ingress and internal condensation |

---

## 4. CALIBRATION & INGESTION PARAMETERS

1. **Capacitive Soil Moisture Calibration**:
   * Dry Air Reading: Raw ADC $\approx 3,200$ (0% Saturation)
   * Saturated Wet Soil: Raw ADC $\approx 1,400$ (100% Saturation)
   * Formula: $\text{Saturation \%} = \text{constrain}\left(\frac{3200 - \text{raw}}{3200 - 1400} \times 100, 0, 100\right)$
2. **MPU-6050 Pitch/Roll Calculation**:
   * $\text{Pitch} = \text{atan2}(a_y, \sqrt{a_x^2 + a_z^2}) \times \frac{180}{\pi}$
   * Normal Slope Baseline: Subtracted to compute $\Delta\theta$ (tilt displacement rate).
3. **Transmission Protocol**:
   * Transmits every 10 minutes under normal conditions.
   * Dynamically increases rate to 30 seconds when $|\Delta\theta| > 0.5^\circ/\text{hr}$ or soil moisture $>85\%$.
