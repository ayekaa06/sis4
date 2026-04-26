"""Hand-written photon and qubit primitives for the BB84 simulation."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Tuple

RECTILINEAR = "+"
DIAGONAL = "x"
SQRT_HALF = 1.0 / math.sqrt(2.0)

BASIS_LABELS = {
    RECTILINEAR: "Rectilinear (+)",
    DIAGONAL: "Diagonal (x)",
}

POLARIZATION_LABELS = {
    0: "Horizontal 0 deg",
    45: "Diagonal 45 deg",
    90: "Vertical 90 deg",
    135: "Diagonal 135 deg",
}


@dataclass(frozen=True)
class QuantumState:
    """Real-amplitude qubit state |psi> = alpha|0> + beta|1>."""

    alpha: float
    beta: float

    def normalized(self) -> "QuantumState":
        magnitude = math.sqrt((self.alpha * self.alpha) + (self.beta * self.beta))
        if magnitude == 0.0:
            raise ValueError("Quantum state magnitude cannot be zero.")
        return QuantumState(self.alpha / magnitude, self.beta / magnitude)

    def amplitudes_in_basis(self, basis: str) -> Tuple[float, float]:
        if basis == RECTILINEAR:
            return self.alpha, self.beta
        if basis == DIAGONAL:
            plus_amplitude = (self.alpha + self.beta) * SQRT_HALF
            minus_amplitude = (self.alpha - self.beta) * SQRT_HALF
            return plus_amplitude, minus_amplitude
        raise ValueError(f"Unsupported basis: {basis}")

    def measurement_probabilities(self, basis: str) -> Tuple[float, float]:
        amplitude_zero, amplitude_one = self.amplitudes_in_basis(basis)
        probability_zero = amplitude_zero * amplitude_zero
        probability_one = amplitude_one * amplitude_one
        total = probability_zero + probability_one
        if total == 0.0:
            return 0.5, 0.5
        probability_zero /= total
        probability_one /= total
        probability_zero = min(max(probability_zero, 0.0), 1.0)
        probability_one = min(max(probability_one, 0.0), 1.0)
        return probability_zero, probability_one


@dataclass(frozen=True)
class PhotonState:
    """Photon encoded with a BB84 basis, bit, polarization, and qubit state."""

    bit_value: int
    basis: str
    polarization_degrees: int
    state: QuantumState

    @property
    def polarization_label(self) -> str:
        return POLARIZATION_LABELS[self.polarization_degrees]


@dataclass(frozen=True)
class MeasurementOutcome:
    """Result of measuring a photon in one of the BB84 bases."""

    bit_value: int
    basis: str
    probability_zero: float
    probability_one: float
    deterministic: bool
    collapsed_photon: PhotonState


def basis_symbol(basis: str) -> str:
    if basis not in BASIS_LABELS:
        raise ValueError(f"Unsupported basis: {basis}")
    return basis


def prepare_photon(bit_value: int, basis: str) -> PhotonState:
    if bit_value not in (0, 1):
        raise ValueError("Bit value must be 0 or 1.")
    if basis == RECTILINEAR:
        if bit_value == 0:
            return PhotonState(
                bit_value=0,
                basis=RECTILINEAR,
                polarization_degrees=0,
                state=QuantumState(1.0, 0.0),
            )
        return PhotonState(
            bit_value=1,
            basis=RECTILINEAR,
            polarization_degrees=90,
            state=QuantumState(0.0, 1.0),
        )
    if basis == DIAGONAL:
        if bit_value == 0:
            return PhotonState(
                bit_value=0,
                basis=DIAGONAL,
                polarization_degrees=45,
                state=QuantumState(SQRT_HALF, SQRT_HALF).normalized(),
            )
        return PhotonState(
            bit_value=1,
            basis=DIAGONAL,
            polarization_degrees=135,
            state=QuantumState(SQRT_HALF, -SQRT_HALF).normalized(),
        )
    raise ValueError(f"Unsupported basis: {basis}")


def measure_photon(photon: PhotonState, basis: str, rng: random.Random) -> MeasurementOutcome:
    probability_zero, probability_one = photon.state.measurement_probabilities(basis)
    roll = rng.random()
    bit_value = 0 if roll < probability_zero else 1
    collapsed = prepare_photon(bit_value, basis)
    deterministic = (
        math.isclose(probability_zero, 1.0, rel_tol=0.0, abs_tol=1e-9)
        or math.isclose(probability_one, 1.0, rel_tol=0.0, abs_tol=1e-9)
    )
    return MeasurementOutcome(
        bit_value=bit_value,
        basis=basis,
        probability_zero=probability_zero,
        probability_one=probability_one,
        deterministic=deterministic,
        collapsed_photon=collapsed,
    )
