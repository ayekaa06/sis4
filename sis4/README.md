# BB84 Quantum Key Distribution Simulator

This project is a hand-written simulation of the BB84 quantum key distribution protocol. It was built to satisfy the assignment in `SIS4_BB84_Simulation.docx` without using any quantum computing frameworks or third-party visualization libraries.

The application uses:

- Python standard library only
- `tkinter` for the desktop user interface
- `random` and `math` for probabilistic measurement and polarization math
- `unittest` for validation tests

All quantum-state handling, photon encoding, measurement, intercept-resend eavesdropping, basis reconciliation, error checking, and privacy amplification logic were implemented manually in this repository.

## Features

- Hand-written BB84 photon and qubit model
- Rectilinear (`+`) and diagonal (`x`) polarization bases
- Probabilistic measurement when bases differ
- Complete BB84 flow:
  - quantum transmission
  - basis reconciliation
  - error checking
  - simplified reconciliation
  - privacy amplification
- Optional Eve intercept-resend attack
- Optional channel noise
- Step-by-step playback mode
- Real-time statistics and key-evolution charts
- Validation tests covering physics rules and protocol behavior

## Project Structure

```text
app.py                  Tkinter launcher
bb84_sim/
  __init__.py
  __main__.py           Package launcher
  protocol.py           BB84 orchestration, Eve, privacy amplification, statistics
  quantum.py            Qubit states, photon encoding, measurement model
  ui.py                 Desktop application
tests/
  test_protocol.py
  test_quantum.py
TECHNICAL_REPORT.md
DEMO_SCRIPT.md
README.md
```

## How to Run

Use a standard Python 3 installation with Tk support.

```bash
python app.py
```

You can also run the package directly:

```bash
python -m bb84_sim
```

## How to Test

```bash
python -m unittest discover -s tests -v
```

## Configuration Options

The UI exposes the assignment parameters directly:

- Number of photons
- Error-check percentage
- Abort threshold
- Eve enabled/disabled
- Channel noise percentage
- Random seed
- Step playback speed

## Requirement Mapping

The implementation maps to the assignment like this:

- Quantum state representation:
  - `bb84_sim/quantum.py`
- Photon polarization encoding:
  - `prepare_photon()` in `bb84_sim/quantum.py`
- Quantum measurement simulation:
  - `measure_photon()` in `bb84_sim/quantum.py`
- BB84 protocol phases:
  - `BB84Protocol.run()` in `bb84_sim/protocol.py`
- Eve intercept-resend attack:
  - `_transmit_single_photon()` in `bb84_sim/protocol.py`
- Error-rate calculation and statistics:
  - `ProtocolStats` and `run_trials()` in `bb84_sim/protocol.py`
- Visualization and step mode:
  - `BB84App` in `bb84_sim/ui.py`

## Notes About the Simulation

This is a classical simulation of BB84 behavior, not a real quantum-hardware implementation. The qubit model is deliberately restricted to the four BB84 states:

- rectilinear bit 0 -> 0 deg
- rectilinear bit 1 -> 90 deg
- diagonal bit 0 -> 45 deg
- diagonal bit 1 -> 135 deg

To keep the project aligned with the assignment and still guarantee identical final keys on successful runs, the protocol models a simplified ideal reconciliation step after error sampling and before privacy amplification.

## Deliverables Included

- Source code
- README
- Validation tests
- Technical report draft in `TECHNICAL_REPORT.md`
- Demo/video outline in `DEMO_SCRIPT.md`

## Suggested Submission Packaging

If you need to submit a zip or Git repository, include the whole project folder so the instructor sees:

- the code
- the tests
- the report
- the demo outline

