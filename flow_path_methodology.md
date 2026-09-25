# Component 11: DEM-Based Landslide Flow-Path & Empirical Runout Methodology

## 1. Executive Summary
Component 11 provides the first actionable consequence-analysis layer for the **NER-SAFE** platform. Using high-risk landslide candidate areas identified by Component 10, the engine traces potential downhill flow trajectories, delineates lateral runout corridors, and performs spatial intersection against cataloged exposure infrastructure across Meghalaya and Mizoram.

## 2. Downhill Flow-Routing Formulation

### 2.1 D8 Steepest-Descent Gradient Routing
Starting from a candidate initiation scarp $(r_0, c_0)$, the engine evaluates the 8-connected neighborhood $N_8(r, c)$:

$$\nabla z_i = \frac{z(r, c) - z(r + \Delta r_i, c + \Delta c_i)}{\Delta s_i}$$

where the horizontal step distance $\Delta s_i$ accounts for grid resolution:
$$\Delta s_i = \begin{cases} \Delta x & \text{for cardinal neighbors } (\Delta r_i = 0 \lor \Delta c_i = 0) \\ \sqrt{2} \cdot \Delta x & \text{for diagonal neighbors } (\Delta r_i \ne 0 \land \Delta c_i \ne 0) \end{cases}$$
with nominal ground cell dimension $\Delta x = 30.89\,\text{meters}$.

### 2.2 Strict Downhill Constraint
To eliminate impossible uphill trajectories, transition is strictly permitted only if:
$$\nabla z_i > 0 \iff z(r + \Delta r_i, c + \Delta c_i) < z(r, c)$$
If multiple neighbors exhibit $\nabla z_i > 0$, the algorithm deterministically selects the neighbor maximizing the gradient:
$$\text{next} = \arg\max_{i \in N_8} (\nabla z_i)$$

### 2.3 Physical Stopping Criteria
Flow tracing continues until one of four physically defensible termination conditions is met:
1. **Slope Flattening (Deposition Zone)**: Local slope drops below $3.5^\circ$ (gradient $\nabla z < 0.061$), representing arrival at an alluvial valley floor or floodplain.
2. **Local Pit / Depression**: All 8 neighbors have $\nabla z \le 0$, indicating a topographic sink.
3. **Fahrböschung Energy Reach Limit**: Empirical travel angle $\tan(\alpha) = \frac{\Delta H}{L} \le 0.176$ ($10^\circ$), consistent with empirical subaerial debris slide energy lines (Corominas 1996).
4. **Maximum Runout Cap**: Cumulative path length exceeds $L_{\max} = 2,500\,\text{meters}$.

## 3. Empirical Runout Corridor Delineation

Landslides rarely travel as a 1D line; channel entrainment and lateral spreading create an expanding swath. An empirical lateral spreading envelope is applied along the path vertices:

$$W(s) = W_0 + (W_{\text{toe}} - W_0) \cdot \frac{s}{L}$$

- **Initiation Scarp Half-Width ($W_0$)**: $35.0\,\text{meters}$ ($70\,\text{meters}$ total width).
- **Deposition Toe Half-Width ($W_{\text{toe}}$)**: $60.0\,\text{meters}$ ($120\,\text{meters}$ total width).

The resulting dilated discs are merged via unary union into a contiguous, GIS-valid polygon corridor.

## 4. Exposure Intersection & Spatial Indexing

Intersection against the large vector catalogs of Component 9 is accelerated using C-accelerated Spatial R-Trees (`shapely.strtree.STRtree`):
- **Road Transportation (45,315 segments)**: Computes intersecting segments, exposed road length in meters, and highway hierarchy (National Highway NH-06/NH-54, State Highway, Major District Road).
- **Building Footprints (296,690 structures)**: Intersects building polygons to count exposed structures and aggregate footprint area.
- **Settlements (976 populated places)**: Evaluates community proximity and derives estimated potentially exposed population ($4.6\,\text{persons/household}$).
- **Critical Transport (75 facilities)**: Identifies threatened helipads, emergency airstrips, and logistics terminals.

## 5. Multi-Criteria Impact Prioritization

$$\text{Impact Score} = 0.50 \times \text{Hazard Risk} + 0.50 \times \text{Consequence Score}$$

- **CRITICAL**: $\text{Impact Score} \ge 0.50$ OR National Highway directly in runout path OR $\ge 10$ buildings exposed.
- **HIGH**: $\text{Impact Score} \ge 0.38$ OR State Highway in runout path OR $\ge 3$ buildings exposed.
- **MODERATE**: $\text{Impact Score} \ge 0.28$ OR Any road/building exposed.
- **LOW**: $\text{Impact Score} < 0.28$ (Wilderness / unpopulated mountain slope).

## 6. Confidence Formulation
Every event record carries a multi-dimensional confidence vector:
1. **Hazard Confidence**: $1.0 - \text{Component 10 Uncertainty}$.
2. **Flow-Path Confidence**: $f(\Delta H, L, \text{slope monotonicity})$.
3. **Runout Confidence**: $f(\text{path length confinement})$.
4. **Impact Confidence**: $f(\text{exposure layer completeness})$.
5. **Overall Confidence**: Weighted combination ($30\% \text{ Haz} + 30\% \text{ Flow} + 20\% \text{ Run} + 20\% \text{ Imp}$).
