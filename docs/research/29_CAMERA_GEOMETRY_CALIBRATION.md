# 29 — Camera Geometry and Calibration for CCTV Analytics

*Where this sits:* R02 (multi-camera tracking/ReID) and 18 (perception stack) assume that a pixel can be turned into a position on the ground and back. This dossier covers what that assumption rests on: the pinhole model, how K and [R|t] are estimated, lens distortion, how a PTZ head changes the maths, the pixel-density levels that procurement writes into contracts (DORI and its 2025 replacement), coverage and footprint arithmetic, how errors spread, and how several cameras are put into one world frame. Every worked number is computed from the repo's own rig (`configs/scenarios/disguise_and_tamper.yaml`) using `survsim/core/geometry.py`, the same code the simulator uses to decide what counts as "visible".

Tagging: `[n]` = a primary source fetched this session (see References). `[derived]` = arithmetic done here from cited or repo quantities. `[VERIFY]` = not confirmed against a fetched primary source. `[repo]` = read from this repository's code or configs.

---

## 1. The pinhole model, from intuition to matrices

### 1.1 Intuition

A camera turns a 3-D ray into a 2-D point. Every world point along the same line through the optical centre lands on the same pixel. That one fact gives you three things. **Depth is lost**: one pixel stands for a whole ray, so a single camera cannot tell range without another constraint. **Size shrinks as 1/range**: a person twice as far away is half as tall in pixels. **Straight lines stay straight**, but only for an ideal lens. Real lenses bend lines, and that is what the distortion model in §3 corrects.

### 1.2 The equations

Take a world point **X**_w (metres). The camera first moves it into its own frame, then projects it:

```
X_c = R · X_w + t                       (extrinsics: 3x3 rotation, 3x1 translation)
x_n = X_c / Z_c, y_n = Y_c / Z_c         (perspective divide -> "normalised" coordinates)
[u v 1]^T = K · [x_n y_n 1]^T            (intrinsics)

      | f_x   s   c_x |
K  =  |  0   f_y  c_y |
      |  0    0    1  |
```

- `f_x, f_y` are the focal length **in pixels**, so they already fold together the physical focal length and the pixel pitch.
- `(c_x, c_y)` is the principal point, the pixel where the optical axis meets the sensor.
- `s` is skew. It is effectively zero on modern sensors. Zhang's real-data experiment found the aspect ratio "very close to 1, i.e., the pixels are square" [1].
- `t = −R·C`, where `C` is the camera centre in world coordinates.

Together these are `P = K[R|t]`, a 3×4 matrix with 11 degrees of freedom (5 intrinsic + 3 rotation + 3 translation).

**How FOV becomes a focal length.** Spec sheets quote a horizontal field of view, not `f_x`. For an image `W` pixels wide:

```
f_x = (W/2) / tan(HFOV/2)
```

That is exactly what `survsim/core/geometry.py::intrinsics` computes. It sets `f_y = f_x` (square pixels), puts the principal point at the image centre and uses zero skew [repo].

**Worked number (cam_gate).** 1920×1080 with a 70° HFOV gives `f_x = 960 / tan 35° = 1371 px` [derived]. The repo's `intrinsics()` returns `K = [[1371,0,960],[0,1371,540],[0,0,1]]` [repo, run this session]. The vertical FOV follows as `2·atan(540/1371) = 43.0°` [derived].

### 1.3 Conventions in this repo

This is where most real bugs come from, so it helps to state them precisely.

- **World frame:** right-handed, Z up, metres. The camera's forward axis before mounting is +X [repo, geometry.py docstring].
- **Mount rotation:** `R_mount = Rz(yaw)·Ry(−pitch)·Rx(roll)`. Pitch is **negated** so that `pitch: −20` tilts the camera *down*, the way CCTV specs write it. The docstring records the bug that motivated this: "without this a `pitch: -20` camera looks at the sky" [repo]. CLAUDE.md notes that the inverted-pitch bug "survived a self-consistent test", which is why a test now pins the sign.
- **World → optical axes:** a fixed permutation maps (forward, left, up) to (right, down, forward). The code then forms `R = to_optical · R_mountᵀ` and `t = −R·C` [repo].
- **Unreal boundary:** `survsim/backends/unreal/backend.py` states that SurvSim uses "metres, Z up, right-handed, yaw measured CCW from +X", while Unreal uses "centimetres, Z up, left-handed, yaw measured CW from +X". So `M_TO_CM = 100`, Y flips sign and `to_ue_yaw(y) = −y` [repo].
- **The Rotator pitfall:** Epic's Python API signature is `unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0)`, so the positional order is **roll, pitch, yaw** [10]. `Rotator(-20, 135, 0)`, written with "pitch, yaw, roll" in mind, actually produces roll = −20 and pitch = 135, which points the camera past vertical. CLAUDE.md records a day-long "pure black render" traced to exactly this. The rule is to always pass keywords.


---

## 2. Homography to the ground plane: derivation from K[r1 r2 t]

### 2.1 Intuition

Most CCTV analytics care about where people stand, and people stand on the ground. If you only map ground points, you are mapping one plane to another plane (the image). Plane-to-plane projection is a 3×3 **homography**. It is invertible, so a detected foot pixel maps back to metres on the ground with a single matrix multiply. That is the basis of a top-down tracker, of cross-camera association by position, and of the "geo-registration" in §8.

### 2.2 Derivation

Choose world coordinates so the ground is `Z = 0`. Then for a ground point `(X, Y, 0)`:

```
s·[u v 1]^T = K [r1 r2 r3 t] [X Y 0 1]^T = K [r1 r2 t] [X Y 1]^T
```

The third rotation column `r3` multiplies zero and drops out. So

```
H = K [r1 r2 t]        (defined up to scale; 8 DoF)
```

Zhang writes exactly this, `H = λK[r1 r2 t]`, as the starting point of his calibration method [1]. To go from image to ground, compute `[X Y 1]^T ∝ H^{-1}[u v 1]^T` and divide by the third component.

Why 8 DoF: nine entries minus one overall scale. Each 2-D↔2-D correspondence gives two equations, so **four non-collinear points** determine H, and more points give a least-squares or RANSAC fit.

**When H is invalid:**
1. The point is **off the plane.** A head, a car roof or a raised platform maps to the wrong place. This is why you back-project the *foot point* (bottom-centre of the box) and never the box centre.
2. **Lens distortion is uncorrected.** H assumes a straight-line projection, so you must undistort first (§3).
3. **The ground is not flat**: ramps, kerbs, stairs.
4. **The camera moved**: a PTZ head slewed or someone knocked the camera. H is tied to a single `R` (§4).

### 2.3 Worked number from the repo

For `cam_gate` (pos (22, −10, 4.5), yaw 135°, pitch −20°) the repo's `K`, `R`, `t` give, after normalising `H[2,2] = 1`:

```
H ≈ [[14.54, 70.49, 449.8],
     [-1.194, 1.194, 328.9],
     [-0.029, 0.029, 1.0 ]]
```
[derived, computed with `geometry.intrinsics/extrinsics` this session]. The bottom row is non-zero, and that is the perspective: the "vanishing" row of H describes where the ground's horizon falls in the image.

**Geometric sanity check.** The camera sits 4.5 m up and tilts 20° down, with a 43.0° vertical FOV. The bottom image edge looks down at 20 + 21.5 = 41.5°, so the nearest visible ground is `4.5 / tan 41.5° = 5.1 m` away. The top edge looks at 20 − 21.5 = −1.5°, i.e. *above* the horizon, so the far edge of the footprint is at **infinity**: the sky is in frame [derived]. This matters for the analytics: everything near the top rows is at very long range and very small, and the homography there is very sensitive to tiny errors (§7).

---

## 3. Lens distortion: Brown–Conrady and fisheye

### 3.1 Intuition

A wide CCTV lens bends rays more the further they are from the centre. Straight fence lines become barrels. If the rendered or real pixels are distorted but ground truth is projected with an ideal pinhole, the boxes drift away from people toward the frame edge. The docstring of `distortion_coeffs` says as much: "boxes drift from people toward the frame edge, and any calibration or multi-view experiment built on it is wrong" [repo].

### 3.2 Brown–Conrady (OpenCV's "standard" model)

Distortion acts on normalised coordinates `(x', y')` before `K` is applied. With `r² = x'² + y'²`, OpenCV's full model is [2]:

```
x'' = x'·(1 + k1 r² + k2 r⁴ + k3 r⁶)/(1 + k4 r² + k5 r⁴ + k6 r⁶) + 2 p1 x'y' + p2 (r² + 2x'²) + s1 r² + s2 r⁴
y'' = y'·(1 + k1 r² + k2 r⁴ + k3 r⁶)/(1 + k4 r² + k5 r⁴ + k6 r⁶) + p1 (r² + 2y'²) + 2 p2 x'y' + s3 r² + s4 r⁴
```

The coefficient vector is ordered `(k1, k2, p1, p2[, k3[, k4, k5, k6[, s1, s2, s3, s4[, τx, τy]]]])` [2].

- `k1…k3` are **radial** terms, from the lens being rotationally symmetric. Negative `k1` is **barrel** distortion and positive is **pincushion**. Zhang's paper uses exactly these words and notes the MLE recovered the correct barrel (negative `k1`) sign where the closed-form stage had guessed pincushion [1].
- `k4…k6` form a rational denominator for very wide lenses.
- `p1, p2` are **tangential** terms, from a lens element that is not quite parallel to the sensor.
- `s1…s4` are thin-prism terms.

Zhang himself modelled only `k1, k2` ("the first two terms of radial distortion") [1].

The repo implements the 5-term form (`k1, k2, p1, p2, k3`) in `apply_distortion`, using the same OpenCV ordering. It is applied by default in `project()`, and `distort=False` gives the ideal pinhole "which is what a calibration algorithm is trying to recover" [repo].

### 3.3 Fisheye (Kannala–Brandt style)

When HFOV approaches 180°, a polynomial in `r` breaks down because `r = tan θ` goes to infinity. The fisheye model is polynomial in the **angle** `θ` instead [2]:

```
θ_d = θ (1 + k1 θ² + k2 θ⁴ + k3 θ⁶ + k4 θ⁸)
```

The repo's `fisheye` branch computes `θ = atan(r)`, applies this formula, and rescales `(x_n, y_n)` by `θ_d / r` [repo]. Ceiling-mounted 360° domes need this model. `cam_yard`'s 95° dome can still be handled by Brown–Conrady [VERIFY for any specific lens].

### 3.4 Undistorting is not free

There is no closed-form inverse of the polynomial. Undistortion is iterative, or done with a precomputed remap table. A remapped image also has to be resampled, which blurs the edges, where the lens was already weakest. In a production pipeline, a common approach is to run detection on the raw image and undistort only the **foot points** before applying H [derived: engineering practice, not a cited claim].

---

## 4. Zhang's calibration method: how K, distortion and poses are recovered

### 4.1 Intuition

You cannot measure `f_x` with a ruler. But if you photograph a flat pattern whose geometry you know (a checkerboard), each photo gives a homography `H_i = λK[r1 r2 t]_i`. The unknown `K` is the same in every photo. The unknown `r1, r2` are always **orthonormal**, because they are columns of a rotation. So each photo yields two constraints on `K`, and a few photos pin it down.

### 4.2 The two constraints

Write `H = [h1 h2 h3]`. Then `r1 = λ⁻¹K⁻¹h1` and `r2 = λ⁻¹K⁻¹h2`. Orthonormality (`r1·r2 = 0` and `|r1| = |r2|`) gives [1]:

```
h1ᵀ B h2 = 0
h1ᵀ B h1 = h2ᵀ B h2        where B = K⁻ᵀ K⁻¹
```

`B` is symmetric, so it has 6 unknowns up to scale. Each image contributes 2 linear equations. Stack them for `n` images into a `2n × 6` system and solve by SVD. Zhang notes the closed-form solution "involves finding a singular value decomposition of a small 2n × 6 matrix" [1]. With 5 intrinsic unknowns, **three images** in general position are enough. Two are enough if skew is fixed at zero [1]. `K` then comes from a Cholesky-like factorisation of `B`, and each `[R|t]_i` comes from `K⁻¹H_i`.

### 4.3 Refinement

The closed-form answer minimises an algebraic error with no physical meaning. Zhang therefore uses it only as the initial guess for a **maximum-likelihood** refinement: minimise the sum of squared reprojection errors over all corners in all images, with Levenberg–Marquardt, jointly with `k1, k2` [1]. His Table 1 reports the RMS reprojection error, "the root of mean squared distances, in pixels, between detected image points and projected ones", and says "the MLE improves considerably this measure" [1]. The final (MLE) RMS values in that table are 0.295, 0.393, 0.361 and 0.335 px for 2, 3, 4 and 5 images, i.e. about **0.3–0.4 px**, 0.335 px with all five [1].

### 4.4 Numbers from Zhang's real-data experiment

- Camera: an off-the-shelf PULNiX CCD with a 6 mm lens at 640×480. The pattern was 8×8 squares (256 corners) on a 17 cm × 17 cm sheet on glass [1].
- Five images were used. The estimates were "very consistent with each other whether we use 2, 3, 4 or 5 images", and the uncertainty falls as images are added [1].
- In simulation, errors "decrease significantly" going from 2 to 3 images [1].

### 4.5 Why Zhang does not solve CCTV by itself

A camera already bolted 5 m up a pole cannot easily be shown a checkerboard at many angles, and a 17 cm board is a few pixels wide at 30 m. In practice, intrinsics are calibrated **on the bench** (or taken from the lens datasheet), and extrinsics are solved **in place** from known ground points. WILDTRACK did exactly this split: intrinsics "estimated once per camera", and extrinsics from "points on the ground between which we know the distances measured by hand in centimetres" [8]. They then ran a joint bundle adjustment over 1,398 hand-clicked multi-view points. The 15 per-camera parameters were 3 rotation, 3 translation, 2 focal, 2 principal point, 3 radial and 2 tangential [8]. They found that optimising intrinsics and extrinsics together "provided the best results" [8].

**For the simulator:** the repo can render a checkerboard into the scene and check that `cv2.calibrateCamera` recovers the configured `K` and `k1…k3`. That tests end-to-end that GT and pixels share one coordinate system. `project(..., distort=False)` exists for exactly this purpose [repo].

---

## 5. PTZ modelling

### 5.1 Intuition

A pan-tilt-zoom head rotates the camera about (approximately) its optical centre, and it changes the focal length. When the centre does not move, two views are related by a **pure homography** whatever the scene depth, because no parallax is created. That is what makes PTZ calibration tractable, and it is also why a slewed PTZ invalidates yesterday's ground homography.

### 5.2 The model

Sinha & Pollefeys make the standard assumption explicitly: "the center of rotation of the camera is fixed and coincides with the camera's center of projection". They note that cheap heads violate this, but outdoors "the deviation of the center is negligible compared to the average distance of the observed features" [9]. Given that assumption, with pan `θ`, tilt `φ` and zoom `z`:

```
P(θ, φ, z) = K(z) · R(θ, φ) · [I | −C]
H_{a→b} = K(z_b) · R_b · R_aᵀ · K(z_a)⁻¹          (inter-view homography, any depth)
```

Two facts their experiments established [9]:
- **Focal length vs zoom is camera-specific**: the Canon VB-C10 "had a linear mapping of focal length to zoom whereas the SNC-RZ30's focal length was non-linear". So `f(z)` must be calibrated as a lookup table or curve, not assumed.
- **Distortion depends on zoom.** Radial distortion "becomes more prominent as the focal length of the camera decreases", so their model makes distortion "also a function of zoom". The principal point also moved "in a straight line", most visibly at high zoom.

Their procedure: build a panorama at the widest zoom to recover `K` and distortion from rotation-induced homographies plus bundle adjustment, then step through the zoom range, calibrating each step from the previous one [9].

### 5.3 How the repo models PTZ

`cam_ptz` sits at (0, 0, 9) m with `hfov_deg: [3.0, 60]`, a slew speed of 40°/s, and three presets: gate (hfov 30°), fence (35°) and substation (30°) [repo]. `camera_director._step_ptz` moves yaw and pitch toward the preset at the rate limit. It moves the FOV with a first-order lag, `hfov += (target − hfov)·min(1, 4·dt)`, and then writes the live `hfov_deg` back into the camera used for ground truth [repo]. This follows CLAUDE.md principle 2: **ground truth must follow the live camera.**

The model is simplified in known ways:
- Focal length comes from HFOV through the same `f_x = (W/2)/tan(HFOV/2)`. That is exact for a pinhole but ignores the non-linear zoom mapping and the principal-point drift that [9] measured.
- Distortion is not zoom-dependent.

Both would be one-line extensions (a per-camera `f(z)` table and `k1(z)`) if a sim-to-real study needed them [derived].

**Worked numbers, cam_ptz.** All at 1920 px width [derived]:
- At 60°: `f_x = 960/tan 30° = 1663 px`. At 9 m height and −25° pitch (VFOV 36.0°), the ground footprint runs from 9.7 m to 73.2 m.
- At the 30° gate preset: `f_x = 960/tan 15° = 3583 px`.
- At the 3° tele end: `f_x ≈ 36,661 px`, a 22× focal ratio. The VFOV is 1.7° and, at −25° pitch, the footprint is a sliver from 18.6 m to 20.1 m.

That is the PTZ trade-off in one line: at full zoom you get about 1,470 px/m at 25 m, enough to scrutinise a face, over a strip about 1.5 m deep.

### 5.4 Slew and why it matters for GT

At 40°/s, gate→fence is a 100° pan and takes 2.5 s. For those 2.5 s, motion blur and a changing `R` make every frame's homography different. The recorder must write per-frame calibration, not per-camera calibration, or cross-camera association breaks during every patrol step [derived].

---

## 6. Pixel density: DORI (2014) and the 2025 visual-performance levels

### 6.1 Intuition

Operators and procurement do not ask for "IoU". They ask whether they can *identify* the person. IEC 62676-4 turns that into a **pixel density** at the target (pixels per metre, horizontally across the scene at the target's range). The basis is how many pixels land on a human face, which is assumed to be **16 cm** wide [3][4].

### 6.2 The 2014 DORI levels [3]

| Level | px per face | px/m | px/ft |
|---|---|---|---|
| Detection | 4 | 25 | 8 |
| Observation | 10 | 63 (62.5) | 20 (19) |
| Recognition | 20 | 125 | 40 (38) |
| Identification | 40 | 250 | 80 (76) |

The px/face column is the px/m column times 0.16 m: `250 × 0.16 = 40`, for example [derived].

- The model is "a simplified model of a complex reality".
- Compliance does not guarantee that the operational requirement is met.
- "Light direction, optics quality, and image compression" matter.
- Results depend on the display.
- It applies where images "are interpreted by human operators".

**That last point matters for an ML company.** DORI is a human-viewing standard. A detector's usable threshold is a separate empirical question, and it is the reason the repo has its own 20 px rule (§7).

### 6.3 What IEC 62676-4:2025 changed

The Axis white paper for the 2025 edition lists **seven** operational requirements [4]:

| 2025 level | px/m |
|---|---|
| Overview | 20 |
| Outline | 40 |
| Discern | 80 |
| Perceive | 125 |
| Characterize | 250 |
| Validate | 500 |
| Scrutinize | 1500 |

The Axis newsroom post gives Overview as 3 px/face and Scrutinize as 240 px/face, and a publication date of **20 November 2025** [5]. Those per-face figures agree with the 16 cm face: 20 × 0.16 = 3.2 and 1500 × 0.16 = 240 [derived].

According to [4], the edition also changes:
- monitor-conversion guidance
- "scene requirements relating to frames per second"
- IR and white-light lighting specifications
- "the required angle to reach the level of scrutinize"
- an LPDO/HPDO categorisation: Low Pixel Density Object (Overview/Outline/Discern) and High Pixel Density Object (Perceive to Scrutinize) [4]

Axis's blog also mentions strengthened cybersecurity [5].

**Is DORI retired or kept alongside?** On re-fetch (audit 2026-09-26) neither Axis source says DORI was "replaced": the blog describes the 2025 levels as an evolution beyond the 2014 DORI framework [5], and the 2025 white paper keeps DORI available alongside the new levels in Axis's design tools [4]. Treat them as parallel ladders; the standard text itself was not read [VERIFY].

What the numbers do show is that two of the new levels coincide with old ones: Perceive = 125 = Recognition, and Characterize = 250 = Identification [derived]. So designs specified to DORI translate directly. The standard text itself is paywalled at the IEC webstore and was not read [VERIFY].

### 6.4 From px/m to range

At range `R` (along the ray), a pinhole gives `px/m ≈ f_x / R`, so the maximum range for a level `D` is `R_max = f_x / D` [derived]. For the repo's cameras:

| Camera | f_x (px) | Detect 25 | Observe 62.5 | Recognise 125 | Identify 250 | Scrutinize 1500 |
|---|---|---|---|---|---|---|
| cam_gate (1920, 70°) | 1371 | 55 m | 22 m | 11 m | 5.5 m | 0.9 m |
| cam_yard (1280, 95°) | 586 | 23 m | 9.4 m | 4.7 m | 2.3 m | — |
| cam_sub (1920, 60°) | 1663 | 67 m | 27 m | 13 m | 6.7 m | 1.1 m |
| cam_ptz wide (60°) | 1663 | 67 m | 27 m | 13 m | 6.7 m | 1.1 m |
| cam_ptz tele (3°) | 36,661 | 1.47 km | 587 m | 293 m | 147 m | 24 m |

[derived, computed this session]

**Reading the table.**
- cam_yard's wide 720p dome cannot *identify* anyone beyond about 2.3 m. It is a detection and overview camera, and a spec that expected faces from it would fail.
- cam_gate identifies only within about 5.5 m. Its nearest visible ground is 5.1 m (§2.3), so the identification zone is a thin strip at the bottom of the frame.
- The PTZ at full tele is the only camera that can meet 2025 *Scrutinize* at a useful range.

**Caveat on the formula.** `f_x / R` uses slant range. For a camera looking steeply down, the foreshortening of vertical extent differs from horizontal, which is why the standard defines density horizontally [3][4]. Measured density also falls off toward the image edges with distortion.

---

## 7. Footprint, pixel height and the 20-pixel rule

### 7.1 Ground footprint of a tilted camera

Take a camera at height `h`, depression `τ` (the positive down-tilt) and vertical FOV `V`. The near and far edges of its footprint along the centreline are [derived, plain trigonometry]:

```
d_near = h / tan(τ + V/2)
d_far  = h / tan(τ − V/2)       (infinite if τ ≤ V/2: horizon in frame)
```

The width at distance `d` is about `2·√(d² + h²)·tan(HFOV/2)`. The footprint is a trapezoid.

Repo rig [derived]:

| Camera | h | τ | VFOV | near | far |
|---|---|---|---|---|---|
| cam_gate | 4.5 m | 20° | 43.0° | 5.1 m | ∞ (horizon visible) |
| cam_yard | 5.0 m | 18° | 63.1° | 4.3 m | ∞ |
| cam_sub | 4.0 m | 15° | 36.0° | 6.2 m | ∞ |
| cam_ptz @60° | 9.0 m | 25° | 36.0° | 9.7 m | 73.2 m |

Every fixed camera in this scenario has the horizon in frame. That is realistic for perimeter cameras. It also means the geometric footprint is unbounded, and coverage is limited by **pixel height**, not by the frustum. That is why the repo defines visibility by pixel size.

### 7.2 Pixel height of a person vs range

For a person of height `H` at slant range `R`, roughly `px ≈ f_x · H / R` [derived]. The exact value depends on tilt, because the head and foot rays are not symmetric about the axis. The repo computes it properly: `pixel_height()` projects the foot and the head (foot + H·ẑ) and takes the difference in `v` [repo].

cam_gate, walking straight out along the camera's yaw, H = 1.75 m (computed with the repo's function this session):

| Ground range | px height (repo) | f·H/R approx | usably_visible |
|---|---|---|---|
| 6 m | 305 | 320 | yes |
| 10 m | 212 | 219 | yes |
| 20 m | 120 | 117 | yes |
| 40 m | 64 | 60 | yes |
| 80 m | 33 | 30 | yes |
| 120 m | 22 | 20 | yes |
| 150 m | 18 | 16 | **no** |

The approximation is good to about 10%. The residual comes from tilt: near the bottom edge the person is foreshortened, and near the horizon they stand more upright relative to the image plane.

### 7.3 The 20 px threshold

`MIN_USABLE_PX_HEIGHT = 20.0`. `usably_visible` requires the point to be in the image, in front of the camera, and `pixel_height ≥ 20` [repo]. CLAUDE.md principle 5 makes this **the** one definition of visible, so coverage analysis and "was this act observed?" cannot disagree.

Converting that to range [derived]:
- `R_20 = f_x · 1.75 / 20`, which is about 120 m for cam_gate, 51 m for cam_yard and 145 m for cam_sub.
- At a 20 px body height, the whole 1.75 m person occupies the same pixels DORI assigns to about 11 px/m. That is *below* DORI Detection (25 px/m) and roughly at 2025 Overview (20 px/m).

So the repo's "visible" is deliberately a **detector-reachable** threshold, not an operator standard. When presenting coverage numbers, you have to say which one you mean. A "39.6% blind" figure under the 20 px rule would be far larger under a DORI-Recognition rule.

### 7.4 What `survsim rig` reports

Running `survsim rig configs/scenarios/disguise_and_tamper.yaml` this session printed:

```
disguise_and_tamper  blind=39.6%  mean cameras/cell=1.14  2+ cameras=44.8%
```

- The overlap matrix is asymmetric: cam_sub → cam_gate is 1.00, but cam_gate → cam_sub is 0.17.
- Two blind regions were reported: 1,652 m² centred at (−3.2, −23.2) and 346 m² at (25.5, 27.1). Both are flagged "can change clothes here" [repo, run output].

The asymmetry reads as the fraction of camera A's usable cells that camera B also covers. cam_sub sees a small area that cam_gate fully contains, while cam_gate sees far more [repo: `survsim/director/rig.py::overlap_matrix`, "Fraction of camera i's footprint that camera j also sees (asymmetric)"]. Note that `survsim rig` uses a 1.7 m person (`PERSON_H`), not the 1.75 m used in the worked tables above. The 44.8% figure for "2+ cameras" is the share of ground where cross-camera triangulation, and therefore height and position checks, is even possible. For comparison, WILDTRACK's seven cameras average **3.92** views per ground position [8]. It was designed as a multi-view benchmark, and this site was designed as a realistic under-covered perimeter.

---

## 8. Error propagation: what 1° costs at range

### 8.1 Intuition

A small angular error is a **pixel** error that scales with `f_x`. On the ground, it is a **position** error that scales with range, and much worse than linearly for pitch, because at grazing angles a tiny change in ray angle slides the foot point a long way along the ground.

### 8.2 Yaw (pan) and roll-free lateral error

A 1° yaw error shifts every pixel by about `f_x · tan 1° ≈ 0.01745 · f_x` pixels. On the ground at range `R`, it shifts the point laterally by `R · tan 1°` [derived]:
- At 50 m that is 0.87 m.
- cam_gate at 40 m: the repo projection shows a **24.5 px** horizontal shift in the image and **0.70 m** on the ground after back-projecting through the true H [derived, computed this session].

### 8.3 Pitch (tilt): the dangerous one

Ground distance is `d = h / tan α`, where α is the depression angle of the ray, so

```
∂d/∂α = −h / sin²α ≈ −d²/h     (for small α)
```

For cam_gate (h = 4.5 m), a person at 40 m has α ≈ 6.4°. A 1° (0.01745 rad) pitch error gives a ground error of about 40²/4.5 × 0.01745 ≈ **6.2 m** [derived]. The repo's full projection gives a 25.4 px vertical shift and **7.4 m** of ground error at 40 m (the exact value is larger than the small-angle estimate because 1° is not small relative to 6.4°) [derived]. Evaluated the other way, a ray tilted 1° further down moves the point about 5.4 m closer [derived]. The error is asymmetric, and it goes to infinity at the horizon.

**Implications to say out loud:**
1. The same 1° costs 0.7 m sideways but 7 m in depth. Cross-camera association gates must be **anisotropic**: an elongated covariance along the viewing ray, not a circle.
2. Mounting height is the lever. Doubling `h` halves the depth error at a given range. A 9 m PTZ mast is geometrically much better for ground positioning than a 4 m bullet.
3. Standard practice is to propagate pixel noise through H with a Jacobian, `Σ_ground = J Σ_px Jᵀ`, where `J = ∂(H⁻¹ ·)/∂(u,v)`, and use that as the tracker's measurement covariance [derived; standard first-order error propagation].
4. **Foot-point noise itself** (a box bottom that is off by 5 px because of occlusion or shadow) enters the same way. At 40 m, 5 px of vertical noise is about 1.2 m of depth for cam_gate [derived: 7.4 m / 25.4 px × 5 px].

### 8.4 Real-world scale of these errors

- **CityFlow** (40 cameras, 10 intersections, up to 2.5 km apart [7]) estimated each camera's image-to-GPS homography from "5 to 14 landmark points" with GPS positions taken from Google Maps. It reports a converged reprojection error of **11.52 pixels on average, caused by the limited precision of Google Maps** [7]. Radially distorted cameras were corrected first "by straightening curved traffic lane lines" [7].
- **WILDTRACK**, with hand-measured ground distances and bundle adjustment, reports high "joint-accuracy" [8]. For comparison, Zhang's bench calibration reached about 0.3–0.4 px (0.335 px with five images) [1].

The spread from about 0.3 px to more than 10 px is the difference between a lab and a city deployment. It is also why a simulator's perfect calibration flatters multi-camera trackers unless noise is injected deliberately [derived].

---

## 9. Multi-camera geo-registration

### 9.1 The goal

Put every camera into **one** metric world frame, so that a person at (x, y) in camera A's back-projection is the same (x, y) in camera B's. This is the foundation of multi-camera tracking by position, of spatio-temporal ReID constraints, and of fusing RF or audio bearings with vision.

### 9.2 Options, cheapest first

1. **Per-camera ground homography to a map** (CityFlow's approach [7]). Click 4 or more ground landmarks visible in both the image and an orthophoto or site plan, then fit H with RANSAC. It is cheap and needs no intrinsics, but it is only as good as the map and valid only on the ground plane. Use a local tangent plane (ENU), not raw latitude/longitude: CityFlow uses a "flat-earth approximation" [7].
2. **Intrinsics on the bench plus PnP in the field.** With `K` and distortion known, 4 or more surveyed 3-D points give `[R|t]` through PnP. This recovers mount height and tilt, so heads and roofs project correctly too.
3. **Joint bundle adjustment across cameras** (WILDTRACK [8]). Solve all cameras and shared 3-D points together, which is what makes the calibrations **mutually** consistent in overlap regions. WILDTRACK's own review of prior datasets notes that others showed "notable calibration inaccuracy" [8].
4. **Self-calibration from people.** Walking people are vertical sticks of roughly known height. Vanishing points from head–foot lines give tilt and focal length, and tracklets seen in overlapping cameras give the relative pose [VERIFY: well-established idea, specific papers not fetched this session].

### 9.3 Keeping it registered

Cameras move over time: wind, thermal expansion, maintenance knocks. This is the tamper taxonomy's "shift/rotate" case. A deployed system should monitor residuals, for example by re-detecting static keypoints against the reference frame and alarming when the median reprojection error exceeds a threshold. The repo's camera director already applies tampers to the **live** pose, so ground truth follows the moved camera (principle 2) [repo]. The analytics under test do *not* get told, which is exactly the test you want.

### 9.4 PTZ in a registered network

For a PTZ, register the **mount** (C and base R) once. At run time, compose `R = R_mount · R(pan, tilt)` and `K = K(z)`, using the reported pan, tilt and zoom plus the calibrated `f(z)` [9]. Encoder backlash and reporting latency during a slew cause temporary registration error. The standard mitigation is to down-weight or ignore positions from a PTZ while it is moving [derived].

---

## 10. Checklist: turning this into simulator features and tests

| Item | Status in repo | Suggested next step |
|---|---|---|
| Pinhole K from HFOV, square pixels, centred principal point | [repo] `intrinsics()` | Optional per-camera `c_x, c_y` offset to mimic real sensors |
| Brown–Conrady 5-term + fisheye 4-term | [repo] `apply_distortion()` | Checkerboard round-trip test via `cv2.calibrateCamera` |
| Pitch sign, Unreal ×100 / −Y / −yaw, Rotator keywords | [repo] + CLAUDE.md | Already tested; keep the tests |
| Per-frame live calibration for PTZ/tamper | [repo] `camera_director` writes live `hfov_deg` | Export per-frame K, R, t in `calib` |
| Zoom-dependent f(z), distortion(z), principal-point drift | not modelled | Per-camera LUT from [9]-style data |
| Calibration noise injection | not modelled | Perturb yaw/pitch by N(0, 0.5°) at export to stress MCT gates |
| DORI / 2025 levels in `survsim rig` | 20 px rule only | Add px/m heat-maps at 25/62.5/125/250 and 20…1500 |

---


- **"What is a homography and when does it break?"** "For points on the ground plane, `K[r1 r2 t]` maps metres to pixels because the Z column drops out. It has 8 DoF, so four points fix it. It breaks for anything off the plane, for uncorrected distortion, on slopes, and the moment a PTZ moves. That's why I back-project foot points, not box centres, and store calibration per frame."
- **"How does Zhang's method work?"** "Each checkerboard view gives a homography. Because r1 and r2 are orthonormal, each view gives two linear constraints on `B = K⁻ᵀK⁻¹`. Three views solve five intrinsics by SVD, then Levenberg–Marquardt refines everything, distortion included, on reprojection error. Zhang got about a third of a pixel RMS. In the field you do intrinsics on the bench and extrinsics from surveyed ground points, like WILDTRACK."
- **"What's DORI?"** "Pixel density at the target, based on a 16 cm face: 25, 62.5, 125 and 250 px/m for detect, observe, recognise and identify. The 2025 edition of 62676-4 moved to seven levels, from 20 px/m Overview to 1500 px/m Scrutinize, and added frame-rate, lighting and angle guidance. Range for a level is just `f_x / D`: a 1080p 70° bullet identifies to about 5.5 m. And DORI is a *human operator* standard. A detector's floor is a separate number. We use 20 px of body height."
- **"How accurate does calibration need to be?"** "Yaw error is linear, 1° is about 0.9 m at 50 m. Pitch error grows as `d²/h`: on a 4.5 m pole, 1° is about 7 m at 40 m. So association gates must be elongated along the viewing ray, and mounting height buys you accuracy. CityFlow's Google-Maps homographies average 11.5 px of reprojection error, which is the realistic floor for map-based registration."
- **"How do you model a PTZ?"** "Rotation about the optical centre, so view-to-view is `K_b R_b R_aᵀ K_a⁻¹` whatever the depth. Focal length vs zoom is per-model and can be non-linear, and distortion shrinks as you zoom in. In our sim the PTZ slews at 40°/s, and ground truth follows the live head, not the configured pose."
- **One sentence on why the simulator matters:** "Real CCTV never gives you the true K and R, or the true foot position. The simulator does. So you can measure exactly how much a 0.5° calibration error or a 5 px foot jitter costs your multi-camera tracker, before a customer finds out."

---

## References

[1] Z. Zhang, "A Flexible New Technique for Camera Calibration," Microsoft Research Tech. Report MSR-TR-98-71 (1998). https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr98-71.pdf. *Used:* `H = λK[r1 r2 t]`; constraints `h1ᵀBh2 = 0`, `h1ᵀBh1 = h2ᵀBh2`; the 2n×6 SVD; closed-form then Levenberg–Marquardt MLE; the k1, k2 radial model; real data (PULNiX 6 mm lens, 640×480, 8×8 squares / 256 corners, 17 cm pattern, 5 images, final RMS 0.295–0.393 px, 0.335 px with 5 images); square pixels; barrel vs pincushion remark; errors drop sharply from 2 to 3 images.

[2] OpenCV, `modules/calib3d/include/opencv2/calib3d.hpp` (4.x documentation source). https://raw.githubusercontent.com/opencv/opencv/4.x/modules/calib3d/include/opencv2/calib3d.hpp. *Used:* the full rational/tangential/thin-prism distortion equations, the coefficient ordering `(k1,k2,p1,p2[,k3[,k4,k5,k6[,s1..s4[,τx,τy]]]])`, and the fisheye `θ_d` polynomial. (The rendered docs.opencv.org page returned 403, so the header source was fetched instead.)

[3] Axis Communications, "Pixel density based on IEC 62676-4:2014," white paper. https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2014. *Used:* DORI px/face, px/m and px/ft table; 16 cm face-width basis; caveats (simplified model, light/optics/compression, display dependency, human operators only).

[4] Axis Communications, "Pixel density based on IEC 62676-4:2025," white paper. https://whitepapers.axis.com/en-us/pixel-density-based-on-iec-62676-4-2025. *Used:* seven 2025 levels and px/m values (20/40/80/125/250/500/1500); 16 cm face basis; list of 2025 changes (monitor conversion, fps, IR/white light, angle for scrutinize, LPDO/HPDO).

[5] Axis Communications newsroom, "From DORI to Visual Performance in IEC 62676-4:2025." https://newsroom.axis.com/blog/iec-62676-4-video-surveillance. *Used:* the 2025 levels as an evolution beyond 2014 DORI (it does not say "replaced"); Overview 3 px/face and Scrutinize 240 px/face; publication date 20 Nov 2025; cybersecurity and compression/noise refinements.

[7] Z. Tang et al., "CityFlow: A City-Scale Benchmark for Multi-Target Multi-Camera Vehicle Tracking and Re-Identification," CVPR 2019, arXiv:1903.09254. https://arxiv.org/abs/1903.09254 (PDF text extracted). *Used:* 40 cameras, 10 intersections, 2.5 km span; image→GPS homographies with a flat-earth approximation; 5–14 manual landmarks from Google Maps; 8-DoF homography by LMedS/RANSAC; 11.52 px mean reprojection error; distortion corrected by straightening lane lines.

[8] T. Chavdarova et al., "WILDTRACK: A Multi-camera HD Dataset for Dense Unscripted Pedestrian Detection," arXiv:1707.09299. https://arxiv.org/abs/1707.09299 (PDF text extracted). *Used:* 7 static 1920×1080 cameras; per-camera intrinsics; extrinsics from hand-measured ground distances in cm; bundle adjustment over 1,398 annotated points; 15 parameters per camera; joint I+E optimisation best; 1440×480 grid; 3.92 mean views per position; 50 ms initial sync.

[9] S. N. Sinha and M. Pollefeys, "Towards Calibrating a Pan-Tilt-Zoom Camera Network," OMNIVIS 2004. https://snsinha.github.io/pdfs/SinhaOMNI2004.pdf. *Used:* rotation-about-projection-centre PTZ model and its justification; distortion stronger at short focal length and modelled as a function of zoom; principal point moves linearly with zoom; VB-C10 linear vs SNC-RZ30 non-linear focal–zoom mapping; panorama + bundle-adjustment procedure.

[10] Epic Games, Unreal Engine Python API, `unreal.Rotator`. https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Rotator?application_version=5.4. *Used:* signature `Rotator(roll=0.0, pitch=0.0, yaw=0.0)`, positional order roll, pitch, yaw, in degrees.

(Reference [6] intentionally unused: a secondary vendor page on the DORI/OODPCVS relationship appeared in search but was not fetched as a primary source; the claim it supports is tagged [VERIFY] in §6.3.)

**Repo files read:** `survsim/core/geometry.py`, `configs/scenarios/disguise_and_tamper.yaml`, `survsim/director/camera_director.py`, `survsim/backends/unreal/backend.py`, `CLAUDE.md`; `survsim rig` executed this session.
