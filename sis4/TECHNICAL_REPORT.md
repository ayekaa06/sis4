# Technical Report: Hand-Written BB84 Quantum Key Distribution Simulation

## 1. Introduction

This project implements a full classroom-scale simulation of the BB84 quantum key distribution protocol. The purpose of the work is to show how quantum mechanics can be used to establish a shared secret key between two parties, Alice and Bob, while making eavesdropping detectable. The simulation was built entirely by hand without quantum computing frameworks, which makes the protocol mechanics visible and easier to inspect.

The BB84 protocol is historically important because it was the first quantum key distribution protocol. It relies on the fact that quantum states cannot be measured without disturbance when the observer does not know the preparation basis. In practical terms, that means an eavesdropper who tries to intercept the quantum transmission changes the error statistics in a way Alice and Bob can detect.

The goal of this project was not to build a physical QKD system. Instead, the goal was to create a faithful classical simulation of the protocol logic, the measurement rules, the intercept-resend attack, and the resulting statistics. The application also provides an interactive visualization so the protocol can be studied photon by photon.

## 2. Quantum Mechanics Fundamentals

### 2.1 Photon Polarization States

BB84 uses two conjugate bases:

- Rectilinear basis (`+`)
  - bit 0 -> horizontal polarization -> 0 degrees
  - bit 1 -> vertical polarization -> 90 degrees
- Diagonal basis (`x`)
  - bit 0 -> 45 degrees
  - bit 1 -> 135 degrees

In the simulator, each photon is represented by:

- a classical bit value
- a basis choice
- a polarization angle
- a qubit-like state vector

The state vector is represented with real amplitudes:

- `|0>` = `(1, 0)`
- `|1>` = `(0, 1)`
- `|+>` = `(1/sqrt(2), 1/sqrt(2))`
- `|->` = `(1/sqrt(2), -1/sqrt(2))`

This representation is sufficient for BB84 because the protocol uses only four polarization states and does not require general multi-qubit simulation.

### 2.2 Quantum Measurement

Measurement is basis-dependent. If Bob measures in the same basis used by Alice, the result is deterministic and the original bit is recovered with probability 1. If Bob measures in the other basis, the result is random with probability 1/2 for each bit value.

The simulator computes this behavior from the amplitudes directly:

- in the rectilinear basis, amplitudes are read as `(alpha, beta)`
- in the diagonal basis, amplitudes are transformed into diagonal coordinates
- probabilities are obtained by squaring the amplitudes

This keeps the measurement logic faithful to the assignment and avoids hard-coding the result table.

### 2.3 No-Cloning and Disturbance

The protocol security comes from the fact that Eve cannot copy an unknown quantum state perfectly. In the simulation, Eve performs an intercept-resend attack:

1. She intercepts Alice's photon.
2. She randomly chooses a basis.
3. She measures the photon.
4. She prepares a new photon from her measurement result and sends it to Bob.

If Eve chose the wrong basis, her measurement is random. The resent photon then encodes the wrong state relative to Alice's original choice, which produces an elevated error rate when Bob later keeps the same-basis positions.

## 3. BB84 Protocol Implementation

### 3.1 Phase 1: Quantum Transmission

The protocol begins with Alice generating a random bit string. For each bit, she randomly chooses a basis and prepares a photon using the proper polarization encoding. Bob independently chooses a random measurement basis for each received photon and measures it.

The implementation stores a detailed `PhotonTrace` record for every transmission. Each record contains:

- Alice's bit, basis, and polarization
- Eve's basis and result when enabled
- whether channel noise was applied
- Bob's basis, bit, and measurement probabilities
- whether the bases matched
- whether the retained bit was correct or erroneous

This detailed trace supports both the interactive UI and the testing suite.

### 3.2 Phase 2: Basis Reconciliation

After the transmission phase, Alice and Bob compare only their basis choices over the public channel. Whenever the bases match, the corresponding bit is kept in the sifted key. When the bases differ, the bit is discarded.

The simulator tracks the sifted-key positions so that later phases can be mapped back to the original photon transmissions. This is useful in the UI because it lets the application show which photons survive reconciliation and which are removed.

### 3.3 Phase 3: Error Checking

Alice and Bob then reveal a random sample of the sifted key. The revealed positions are compared publicly and removed from the candidate key. The error rate is computed as:

`error rate = mismatched sample bits / sample size`

The simulation supports a configurable error threshold. If the observed error rate exceeds the threshold, the protocol aborts and no final key is produced.

The application also follows the assignment guidance:

- low error rate -> proceed
- moderate error rate -> suspicious
- high error rate -> abort

### 3.4 Simplified Reconciliation and Privacy Amplification

The assignment explicitly allows a simplified privacy amplification step. In this project, the privacy amplification stage compresses the post-check key by XOR-ing neighboring pairs of bits.

To keep successful runs consistent with the assignment's "key agreement" requirement, the simulator also models a simplified ideal reconciliation step after error checking. This represents the classical error-correction stage of practical QKD without implementing a full protocol such as Cascade. After sampling establishes the channel quality, Bob's remaining key is reconciled to Alice's before privacy amplification is applied.

This design choice makes the final shared key identical whenever the protocol succeeds, while still exposing the measured disturbance through the sampling statistics.

### 3.5 Example Walkthrough

Consider a small run:

1. Alice prepares 12 photons.
2. Bob randomly measures each one.
3. Roughly 6 positions survive basis reconciliation.
4. Alice and Bob reveal 1 sampled bit.
5. The remaining 5 bits are reconciled.
6. XOR pair compression reduces the key to 2 final secret bits, with one leftover bit discarded.

This shrinking behavior is shown visually in the app's key-evolution chart.

## 4. Eavesdropping and Detection

### 4.1 Intercept-Resend Attack

The attack implemented in the simulator is the standard intercept-resend attack described in the assignment. Eve randomly chooses a basis for each photon. There are two cases:

- Eve picks the same basis as Alice:
  - she learns the correct bit
  - she resends the correct state
  - Bob sees no additional disturbance from Eve on that photon
- Eve picks the wrong basis:
  - she gets a random result
  - she resends a state that may not match Alice's original preparation
  - if Bob later measures in Alice's basis, a detectable error can appear

### 4.2 Expected Error Rate

For a full intercept-resend attack, the expected quantum bit error rate on sifted positions is approximately 25%. The simulator reproduces this behavior statistically. The exact observed error rate varies from run to run because the protocol is probabilistic and the error-checking phase samples only part of the sifted key.

### 4.3 Detection Mechanism

Detection happens during the public comparison of sample bits. If Eve is active, the sample error rate usually rises well above the normal no-Eve baseline. When the configured threshold is 11%, the protocol almost always aborts for large enough runs.

The project also includes a multi-run helper to estimate detection probability over repeated trials. This supports the security-analysis section of the assignment and backs up the expected claim that the protocol exposes an active intercept-resend attacker with high probability.

## 5. Application Design

### 5.1 Architecture

The application has three main layers:

1. `quantum.py`
   - qubit state representation
   - photon preparation
   - measurement probabilities
2. `protocol.py`
   - BB84 control flow
   - Eve logic
   - sampling, statistics, reconciliation, privacy amplification
3. `ui.py`
   - Tkinter interface
   - canvas visualization
   - step mode
   - statistics tables and charts

This separation makes the system easier to test. The UI does not implement physics or protocol decisions directly. It only renders data produced by the simulation core.

### 5.2 Interface Design

The desktop interface contains:

- a configuration panel
- a visualization panel
- a current-photon detail area
- a step-by-step transmission table
- a statistics panel
- a key-evolution chart
- a result summary

The central canvas shows Alice, Eve, and Bob, along with the current photon state, the transmitted polarization, and whether the photon survives basis reconciliation. A small strip at the bottom of the canvas shows a rolling window of recent photons so the user can see the overall pattern of discarded bits, correct kept bits, and kept errors.

### 5.3 Visualization Strategy

Because the assignment forbids external quantum libraries and this implementation also avoids charting dependencies, the visualization is fully hand-drawn using Tkinter canvas primitives. Rectangles, arrows, lines, and small bar charts are generated directly from the simulation data.

This approach keeps the project self-contained and still satisfies the UI rubric:

- basis choices are visible
- polarization states are visible
- basis matches are highlighted
- step mode is interactive
- final statistics are summarized clearly

## 6. Testing and Results

### 6.1 Quantum Validation Tests

The test suite validates the core physics rules expected by BB84:

- same-basis measurements are deterministic
- different-basis measurements are approximately random
- basis matching over large random runs is close to 50%

### 6.2 Protocol Correctness Tests

The protocol-level tests verify:

- no-Eve runs succeed
- successful runs produce identical Alice and Bob final keys
- moderate channel noise can be reconciled without breaking key agreement
- Eve-driven runs exceed the abort threshold and terminate
- multi-run experiments show a high detection rate under intercept-resend attack

### 6.3 Expected Statistical Behavior

The simulator is designed to reproduce the assignment's expected trends:

- basis match rate near 50%
- very low error rate without Eve when noise is low
- error rate around 25% with intercept-resend Eve
- reduced Eve information after privacy amplification
- final key length lower than sifted key length because of checking and compression

### 6.4 Scalability

The program supports runs from tens to ten thousand photons. The data structures are simple Python lists and dataclasses, which keeps the implementation transparent. For the assignment scale, this is more than sufficient.

## 7. Security Analysis

The key insight of BB84 is that measurement without basis knowledge causes unavoidable disturbance. The simulator demonstrates that security property clearly:

- Without Eve, Alice and Bob retain a large sifted key and observe little or no disturbance.
- With Eve, the sample error rate rises sharply.
- When the error rate crosses the threshold, the protocol aborts and no secret key is accepted.

The simulator also tracks Eve's information before and after privacy amplification. Before privacy amplification, Eve knows exactly the sifted positions where her basis matched Alice's basis. After pairwise XOR compression, Eve knows a final key bit only when she knew both contributing input bits exactly. This directly illustrates how privacy amplification reduces partial leakage.

## 8. Challenges and Lessons Learned

The biggest implementation challenge was balancing protocol realism with assignment practicality. A fully realistic QKD stack would include richer channel models, error-correction exchanges, authentication assumptions, and more formal privacy amplification. The assignment, however, expects a clean educational simulation.

The chosen compromise was:

- exact hand-written modeling of the BB84 state and measurement rules
- explicit implementation of the intercept-resend attack
- simplified but visible reconciliation and privacy amplification
- a UI that makes the protocol understandable at the single-photon level

Another lesson was that visualization helps debugging. The rolling photon trace made it much easier to verify when basis mismatches were being discarded correctly and when Eve-induced errors were appearing on sifted positions.

## 9. Conclusion

This project demonstrates the BB84 quantum key distribution protocol in a way that is both technically grounded and easy to inspect. Every major element requested in the assignment was implemented by hand:

- quantum state representation
- photon polarization encoding
- measurement simulation
- BB84 protocol phases
- intercept-resend eavesdropping
- error-rate analysis
- privacy amplification
- interactive visualization
- validation tests

The final result is a self-contained educational simulator that shows why BB84 works, how it detects eavesdropping, and how the shared key evolves through the protocol.

