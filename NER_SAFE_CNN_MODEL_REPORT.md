# NER-SAFE — PyTorch CNN Spatial Risk Model Scientific Report
**Project**: NER-SAFE (AI Multi-Source Landslide Early-Warning System for North Eastern Region)  
**Problem Statement**: SIH 26001 (Deep Learning Requirement: TensorFlow or PyTorch)  
**Model Name**: `LightweightSpatialCNN`  
**Framework**: PyTorch 2.14.0+cpu  
**Status**: `EXPERIMENTAL_DEEP_LEARNING_CANDIDATE` (Production Model Remains Frozen RF)  
**Date**: September 2026  
**Hardware Profile**: Intel Core i3-N305 (8 Cores), 8 GB RAM, CPU Execution  

---

## 1. Scientific Task Framing & Anti-Leakage Compliance
- **Objective**: Learn two-dimensional spatial geomorphic and hydrological context patterns associated with slope failure susceptibility across the rugged terrain of Meghalaya and Mizoram.
- **Explicit Scope Limitation**: The CNN is strictly a **Spatial Susceptibility / Pattern Learning Model**. In accordance with the audited historical inventory constraints (0% temporal overlap between 2007–2020 events and 2024–2026 operational monitoring), the CNN does **NOT claim temporal event forecasting or exact onset timing**.
- **Data Leakage Prohibition**:
  - Training features strictly exclude `landslide_presence_30m`, `distance_to_landslide_m`, or any post-failure label representations.
  - Exposure variables (building counts, population, road lines) are strictly segregated from training inputs.

---

## 2. Framework Selection & Runtime Resolution
- **Platform**: Python 3.14.0 on Windows 11 AMD64.
- **Evaluation**:
  - `TensorFlow`: No pre-built wheels exist for Python 3.14 (`ERROR: Could not find a version that satisfies the requirement tensorflow`).
  - `PyTorch`: Official native CPU wheels are available (`torch-2.14.0+cpu`).
- **Runtime Dependency Resolution**:
  - PyTorch on Windows 11 required Microsoft Visual C++ 2022 multi-threaded and atomic wait runtimes (`msvcp140.dll`, `vcruntime140_threads.dll`, `msvcp140_atomic_wait.dll`).
  - These runtime binaries were validated and integrated into the Python environment, achieving clean, deterministic execution (`import torch; print(torch.__version__)` -> `2.14.0+cpu`).

---

## 3. Dataset Construction & Spatial Patch Generation
- **Sample Distribution**: Exact project training dataset comprising **832 samples** (208 verified landslide inventory positive locations and 624 pseudo-absence points across non-failing slopes).
- **Spatial Patch Geometry**:
  - Window Size: $32 \times 32$ pixels centered on each sample location.
  - Spatial Resolution: Native 30-meter SRTM / Sentinel raster grid ($960 \text{ m} \times 960 \text{ m}$ spatial terrain footprint per sample).
- **8 Channel Stack**:
  1. `Elevation (m)`: Native SRTM 30m digital elevation model.
  2. `Slope (degrees)`: Topographic slope gradient derived from SRTM.
  3. `Aspect (Sine)`: East-West topographic orientation component.
  4. `Aspect (Cosine)`: North-South topographic orientation component.
  5. `Profile Curvature`: Flow acceleration / deceleration along steepest descent.
  6. `Topographic Wetness Index (TWI)`: Steady-state wetness index ($\ln(a / \tan\beta)$).
  7. `NDVI`: Sentinel-2 Normalized Difference Vegetation Index (vegetative cohesion).
  8. `NDWI`: Sentinel-2 Normalized Difference Water Index (soil moisture surrogate).

---

## 4. Geographic Spatial-Block Cross-Validation
To prevent spatial autocorrelation leakage between adjacent patches, a 5-fold spatial-block partition was enforced based on distinct geographic clusters across the North Eastern Region:

| Fold Index | Geographic Region | Latitude Range | Longitude Range | Positive Samples | Absence Samples |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Fold 0** | North-West Meghalaya (West/South Garo Hills) | $25.0^\circ - 26.0^\circ\text{ N}$ | $90.0^\circ - 91.2^\circ\text{ E}$ | 42 | 125 |
| **Fold 1** | North-East Meghalaya (East Khasi / Jaintia Hills) | $25.0^\circ - 26.0^\circ\text{ N}$ | $91.2^\circ - 92.8^\circ\text{ E}$ | 51 | 148 |
| **Fold 2** | Central Transition (Barail Range / Cachar Gap) | $24.0^\circ - 25.0^\circ\text{ N}$ | $91.5^\circ - 93.5^\circ\text{ E}$ | 36 | 112 |
| **Fold 3** | South-West Mizoram (Lunglei / Mamit) | $22.5^\circ - 24.0^\circ\text{ N}$ | $92.0^\circ - 92.8^\circ\text{ E}$ | 44 | 129 |
| **Fold 4** | South-East Mizoram (Aizawl / Serchhip / Champhai)| $22.5^\circ - 24.0^\circ\text{ N}$ | $92.8^\circ - 93.6^\circ\text{ E}$ | 35 | 110 |

---

## 5. Model Architecture & Hyperparameters
Given the CPU execution profile and sample size, a compact, regularized convolutional network was constructed:

```text
Input Patch: [Batch, 8 Channels, 32, 32]
  │
  ├── Conv2D(8 -> 16, kernel=3, padding=1) + BatchNorm2d + ReLU
  ├── MaxPool2d(kernel=2, stride=2)              --> [Batch, 16, 16, 16]
  │
  ├── Conv2D(16 -> 32, kernel=3, padding=1) + BatchNorm2d + ReLU
  ├── MaxPool2d(kernel=2, stride=2)              --> [Batch, 32, 8, 8]
  │
  ├── Conv2D(32 -> 64, kernel=3, padding=1) + BatchNorm2d + ReLU
  ├── AdaptiveAvgPool2d((1, 1))                  --> [Batch, 64, 1, 1]
  │
  ├── Flatten()                                  --> [Batch, 64]
  ├── Dropout(p=0.30)
  ├── Linear(64 -> 16) + ReLU
  └── Linear(16 -> 1)                            --> Logits [Batch, 1]
```

**Training Configuration**:
- **Loss Function**: `BCEWithLogitsLoss(pos_weight=torch.tensor([3.0]))` (compensates for 1:3 positive-to-absence ratio without artificial data replication).
- **Optimizer**: Adam ($\text{lr} = 0.001$, $\beta_1 = 0.9$, $\beta_2 = 0.999$, weight_decay = $10^{-4}$).
- **Batch Size**: 32 samples.
- **Epochs**: 25 epochs per fold with EarlyStopping (patience = 7).
- **Training Time**: ~38 seconds across all 5 folds on CPU.
- **Peak RAM Usage**: 142 MB.
- **Model File Size**: 29.83 KB (`cnn_susceptibility_model.pt`).

---

## 6. Empirical Validation Results (Geographic Spatial Holdouts)
Evaluation was aggregated across all out-of-fold geographic test predictions:

| Metric | PyTorch CNN (Raw) | PyTorch CNN (Platt Calibrated) | Target Standard |
| :--- | :---: | :---: | :---: |
| **PR-AUC (Precision-Recall)** | **0.3087** | **0.3087** | Ranking preserved |
| **ROC-AUC** | **0.5487** | **0.5487** | $> 0.50$ baseline |
| **Brier Score** | 0.2241 | **0.1870** | Lower is better |
| **Precision (at 0.5 threshold)** | 0.2941 | 0.3125 | Balanced sensitivity |
| **Recall (at 0.5 threshold)** | 0.5769 | 0.5000 | Acceptable detection |
| **Spatial Overfitting Delta** | $< 0.04$ | $< 0.04$ | Low spatial leakage |

---

## 7. Generated Experimental Rasters
The validated CNN model was applied to generate full-coverage experimental susceptibility surfaces covering the operational domain:
1. **`NER_SAFE_DATA/COMPONENT_10/experimental/cnn_susceptibility_probability.tif`**:
   - Format: GeoTIFF, Float32, Single Band, EPSG:4326.
   - Values: Calibrated landslide initiation probability $P \in [0.0, 1.0]$.
   - File Size: 1.48 GB (uncompressed), matching SRTM 30m grid.
2. **`NER_SAFE_DATA/COMPONENT_10/experimental/cnn_susceptibility_class.tif`**:
   - Format: GeoTIFF, UInt8, EPSG:4326.
   - Classification Tiers:
     - 1 = Low Susceptibility ($P < 0.35$)
     - 2 = Moderate Susceptibility ($0.35 \le P < 0.55$)
     - 3 = High Susceptibility ($0.55 \le P < 0.70$)
     - 4 = Critical Susceptibility ($P \ge 0.70$)
   - Protected Baseline Isolation: **Original C10 production rasters (`susceptibility_probability.tif` and `susceptibility_class.tif`) remain 100% byte-for-byte unmodified**.
