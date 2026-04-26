# Demonstration Video Outline

This file is a ready-to-use outline for the required 7-12 minute demonstration video.

## 1. Opening (30-45 seconds)

- Introduce the project: "This is a hand-written simulation of the BB84 quantum key distribution protocol."
- State the core constraint: no quantum simulation libraries were used.
- Mention the stack: Python standard library and Tkinter only.

## 2. Show the Project Structure (45-60 seconds)

Open the project folder and briefly point out:

- `bb84_sim/quantum.py`
- `bb84_sim/protocol.py`
- `bb84_sim/ui.py`
- `tests/`
- `TECHNICAL_REPORT.md`

Say that the simulation core, UI, and validation suite are separated into modules.

## 3. Demonstrate a Successful Run Without Eve (2-3 minutes)

Suggested settings:

- photons: 512
- Eve: off
- channel noise: 0%
- error check: 12%
- threshold: 11%

Steps to show:

1. Click `Run Full Simulation`.
2. Point out:
   - basis match rate is close to 50%
   - error rate is near 0%
   - protocol status is success
   - Alice and Bob share a final key
3. Mention that the chart shows the key shrinking from raw bits to sifted key to final key.

## 4. Demonstrate Step-by-Step Mode (2-3 minutes)

Suggested settings:

- photons: 32
- Eve: on or off
- playback speed: 150 ms

Steps to show:

1. Click `Prepare Step Mode`.
2. Use `Next Photon` a few times.
3. Explain:
   - Alice's basis and bit
   - Bob's basis choice
   - why some photons are discarded
   - how same-basis measurements keep the correct bit
4. Press `Play` to show the animation through the remaining photons.

## 5. Demonstrate Eavesdropping Detection (2-3 minutes)

Suggested settings:

- photons: 1024
- Eve: on
- channel noise: 0%
- error check: 12%
- threshold: 11%

Steps to show:

1. Click `Run Full Simulation`.
2. Point out:
   - Eve's basis match statistics
   - elevated error rate
   - protocol abort status
   - no final secret key is accepted
3. Explain that intercept-resend introduces detectable disturbance.

## 6. Mention the Test Suite (45-60 seconds)

Show the test files and say they verify:

- deterministic same-basis measurements
- random different-basis measurements
- basis match rate near 50%
- success without Eve
- abort with Eve
- high detection rate across repeated trials

## 7. Closing (20-30 seconds)

Wrap up with:

- the project simulates BB84 from scratch
- it demonstrates quantum disturbance and eavesdropping detection
- it meets the assignment requirement to avoid quantum simulation libraries

