"""Protocol orchestration, eavesdropping logic, and statistics."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
import random
from typing import List, Optional, Sequence

from .quantum import DIAGONAL, RECTILINEAR, MeasurementOutcome, PhotonState, measure_photon, prepare_photon


def random_basis(rng: random.Random) -> str:
    return RECTILINEAR if rng.random() < 0.5 else DIAGONAL


def bits_to_string(bits: Sequence[int], limit: Optional[int] = None) -> str:
    slice_end = None if limit is None else max(limit, 0)
    return "".join(str(bit) for bit in bits[:slice_end])


@dataclass
class ProtocolConfig:
    photon_count: int = 512
    error_check_fraction: float = 0.12
    error_threshold: float = 0.11
    eve_enabled: bool = False
    channel_noise: float = 0.0
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.photon_count <= 0:
            raise ValueError("photon_count must be positive.")
        if not 0.0 <= self.error_check_fraction <= 1.0:
            raise ValueError("error_check_fraction must be between 0 and 1.")
        if not 0.0 <= self.error_threshold <= 1.0:
            raise ValueError("error_threshold must be between 0 and 1.")
        if not 0.0 <= self.channel_noise <= 1.0:
            raise ValueError("channel_noise must be between 0 and 1.")


@dataclass
class KeySnapshot:
    label: str
    bits: List[int]

    @property
    def length(self) -> int:
        return len(self.bits)

    @property
    def preview(self) -> str:
        bit_string = bits_to_string(self.bits, limit=64)
        if len(self.bits) > 64:
            return f"{bit_string}..."
        return bit_string


@dataclass
class PhotonTrace:
    index: int
    alice_bit: int
    alice_basis: str
    alice_polarization: int
    eve_basis: Optional[str]
    eve_bit: Optional[int]
    eve_polarization: Optional[int]
    eve_basis_match: Optional[bool]
    eve_knows_bit_exactly: bool
    eve_probability_zero: Optional[float]
    eve_probability_one: Optional[float]
    noise_applied: bool
    delivered_polarization: int
    bob_basis: str
    bob_bit: int
    bob_probability_zero: float
    bob_probability_one: float
    bob_deterministic: bool
    basis_match: bool
    bob_matches_alice: bool
    sifted_index: Optional[int] = None
    sampled_for_error_check: bool = False
    sample_mismatch: bool = False
    retained_after_error_check: bool = False


@dataclass
class ProtocolStats:
    total_photons: int
    basis_matches: int
    basis_match_rate: float
    sifted_key_length: int
    error_check_sample_size: int
    sample_errors: int
    error_rate: float
    final_key_length: int
    efficiency: float
    channel_noise_events: int
    corrected_remaining_errors: int
    eve_basis_matches: int = 0
    eve_basis_match_rate: float = 0.0
    eve_exact_sifted_bits: int = 0
    eve_exact_final_bits: int = 0
    detection_probability: float = 0.0
    aborted: bool = False
    security_status: str = ""


@dataclass
class RunResult:
    config: ProtocolConfig
    traces: List[PhotonTrace]
    alice_bits: List[int]
    alice_bases: List[str]
    bob_bases: List[str]
    eve_bases: List[str]
    sifted_positions: List[int]
    error_check_positions: List[int]
    remaining_positions: List[int]
    key_snapshots: List[KeySnapshot]
    alice_final_key: List[int]
    bob_final_key: List[int]
    eve_final_key_knowledge: int
    stats: ProtocolStats
    aborted: bool
    abort_reason: str

    @property
    def success(self) -> bool:
        return not self.aborted

    @property
    def final_key_preview(self) -> str:
        if not self.alice_final_key:
            return ""
        return KeySnapshot("final", self.alice_final_key).preview


@dataclass
class BatchStatistics:
    trials: int
    average_basis_match_rate: float
    average_error_rate: float
    average_efficiency: float
    average_final_key_length: float
    detection_rate: float
    average_eve_information_before_privacy: float
    average_eve_information_after_privacy: float


@dataclass
class _TransmissionState:
    photon: PhotonState
    eve_outcome: Optional[MeasurementOutcome]
    noise_applied: bool


def _apply_channel_noise(photon: PhotonState) -> PhotonState:
    flipped_bit = 1 - photon.bit_value
    return prepare_photon(flipped_bit, photon.basis)


def _privacy_amplify(bits: Sequence[int]) -> List[int]:
    amplified: List[int] = []
    for index in range(0, len(bits) - 1, 2):
        amplified.append(bits[index] ^ bits[index + 1])
    return amplified


class BB84Protocol:
    """Pure-Python BB84 simulation with optional intercept-resend Eve."""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.rng = random.Random(config.seed)

    def _transmit_single_photon(self, alice_bit: int, alice_basis: str) -> _TransmissionState:
        photon = prepare_photon(alice_bit, alice_basis)
        eve_outcome: Optional[MeasurementOutcome] = None
        forwarded = photon
        if self.config.eve_enabled:
            eve_basis = random_basis(self.rng)
            eve_outcome = measure_photon(forwarded, eve_basis, self.rng)
            forwarded = eve_outcome.collapsed_photon
        noise_applied = self.rng.random() < self.config.channel_noise
        if noise_applied:
            forwarded = _apply_channel_noise(forwarded)
        return _TransmissionState(photon=forwarded, eve_outcome=eve_outcome, noise_applied=noise_applied)

    def run(self) -> RunResult:
        alice_bits: List[int] = []
        alice_bases: List[str] = []
        bob_bases: List[str] = []
        eve_bases: List[str] = []
        traces: List[PhotonTrace] = []

        sifted_positions: List[int] = []
        alice_sifted_bits: List[int] = []
        bob_sifted_bits: List[int] = []
        eve_sifted_known_flags: List[bool] = []
        eve_sifted_bits: List[Optional[int]] = []
        channel_noise_events = 0

        for index in range(self.config.photon_count):
            alice_bit = self.rng.randint(0, 1)
            alice_basis = random_basis(self.rng)
            alice_photon = prepare_photon(alice_bit, alice_basis)
            transmission = self._transmit_single_photon(alice_bit, alice_basis)
            bob_basis = random_basis(self.rng)
            bob_outcome = measure_photon(transmission.photon, bob_basis, self.rng)

            eve_basis = transmission.eve_outcome.basis if transmission.eve_outcome else None
            eve_bit = transmission.eve_outcome.bit_value if transmission.eve_outcome else None
            eve_polarization = (
                transmission.eve_outcome.collapsed_photon.polarization_degrees
                if transmission.eve_outcome
                else None
            )
            eve_basis_match = eve_basis == alice_basis if eve_basis is not None else None
            eve_knows_bit_exactly = bool(eve_basis_match)

            basis_match = alice_basis == bob_basis
            bob_matches_alice = alice_bit == bob_outcome.bit_value

            trace = PhotonTrace(
                index=index,
                alice_bit=alice_bit,
                alice_basis=alice_basis,
                alice_polarization=alice_photon.polarization_degrees,
                eve_basis=eve_basis,
                eve_bit=eve_bit,
                eve_polarization=eve_polarization,
                eve_basis_match=eve_basis_match,
                eve_knows_bit_exactly=eve_knows_bit_exactly,
                eve_probability_zero=(
                    transmission.eve_outcome.probability_zero if transmission.eve_outcome else None
                ),
                eve_probability_one=(
                    transmission.eve_outcome.probability_one if transmission.eve_outcome else None
                ),
                noise_applied=transmission.noise_applied,
                delivered_polarization=transmission.photon.polarization_degrees,
                bob_basis=bob_basis,
                bob_bit=bob_outcome.bit_value,
                bob_probability_zero=bob_outcome.probability_zero,
                bob_probability_one=bob_outcome.probability_one,
                bob_deterministic=bob_outcome.deterministic,
                basis_match=basis_match,
                bob_matches_alice=bob_matches_alice,
            )

            alice_bits.append(alice_bit)
            alice_bases.append(alice_basis)
            bob_bases.append(bob_basis)
            if eve_basis is not None:
                eve_bases.append(eve_basis)
            if transmission.noise_applied:
                channel_noise_events += 1

            if basis_match:
                trace.sifted_index = len(alice_sifted_bits)
                sifted_positions.append(index)
                alice_sifted_bits.append(alice_bit)
                bob_sifted_bits.append(bob_outcome.bit_value)
                eve_sifted_known_flags.append(eve_knows_bit_exactly)
                eve_sifted_bits.append(eve_bit)

            traces.append(trace)

        sample_size = 0
        if alice_sifted_bits and self.config.error_check_fraction > 0.0:
            sample_size = max(1, int(round(len(alice_sifted_bits) * self.config.error_check_fraction)))
            sample_size = min(sample_size, len(alice_sifted_bits))
        error_check_positions = sorted(self.rng.sample(range(len(alice_sifted_bits)), sample_size)) if sample_size else []

        sample_errors = 0
        for sifted_index in error_check_positions:
            trace = traces[sifted_positions[sifted_index]]
            trace.sampled_for_error_check = True
            trace.sample_mismatch = alice_sifted_bits[sifted_index] != bob_sifted_bits[sifted_index]
            sample_errors += int(trace.sample_mismatch)

        error_rate = (sample_errors / sample_size) if sample_size else 0.0

        error_check_set = set(error_check_positions)
        remaining_positions = [index for index in range(len(alice_sifted_bits)) if index not in error_check_set]
        alice_post_check = [alice_sifted_bits[index] for index in remaining_positions]
        bob_post_check = [bob_sifted_bits[index] for index in remaining_positions]
        eve_post_check_flags = [eve_sifted_known_flags[index] for index in remaining_positions]

        for sifted_index in remaining_positions:
            traces[sifted_positions[sifted_index]].retained_after_error_check = True

        alice_final_key = _privacy_amplify(alice_post_check)
        bob_final_key = _privacy_amplify(bob_post_check)

        eve_exact_final_bits = 0
        for index in range(0, len(eve_post_check_flags) - 1, 2):
            if eve_post_check_flags[index] and eve_post_check_flags[index + 1]:
                eve_exact_final_bits += 1

        aborted = error_rate > self.config.error_threshold
        abort_reason = ""
        corrected_remaining_errors = 0
        if not aborted:
            corrected_remaining_errors = sum(
                1 for alice_bit, bob_bit in zip(alice_post_check, bob_post_check) if alice_bit != bob_bit
            )
            # Model a simplified ideal reconciliation pass before privacy amplification.
            bob_post_check = list(alice_post_check)
            bob_final_key = _privacy_amplify(bob_post_check)
        if aborted:
            abort_reason = (
                f"Error rate {error_rate:.2%} exceeded threshold {self.config.error_threshold:.2%}; "
                "secure key distribution aborted."
            )
            alice_final_key = []
            bob_final_key = []
        elif error_rate > 0.05:
            abort_reason = (
                f"Elevated error rate {error_rate:.2%} detected. Protocol continued because it remained "
                f"below the configured threshold of {self.config.error_threshold:.2%}."
            )

        if aborted:
            security_status = "Abort: likely eavesdropping or excessive disturbance"
        elif error_rate > 0.05:
            security_status = "Proceed with caution: suspicious disturbance observed"
        else:
            security_status = "Secure channel accepted"

        basis_matches = len(alice_sifted_bits)
        basis_match_rate = basis_matches / self.config.photon_count
        final_key_length = len(alice_final_key)
        efficiency = final_key_length / self.config.photon_count
        eve_basis_matches = sum(1 for trace in traces if trace.eve_basis_match)
        eve_exact_sifted_bits = sum(1 for flag in eve_sifted_known_flags if flag)
        stats = ProtocolStats(
            total_photons=self.config.photon_count,
            basis_matches=basis_matches,
            basis_match_rate=basis_match_rate,
            sifted_key_length=len(alice_sifted_bits),
            error_check_sample_size=sample_size,
            sample_errors=sample_errors,
            error_rate=error_rate,
            final_key_length=final_key_length,
            efficiency=efficiency,
            channel_noise_events=channel_noise_events,
            corrected_remaining_errors=corrected_remaining_errors,
            eve_basis_matches=eve_basis_matches,
            eve_basis_match_rate=(eve_basis_matches / self.config.photon_count) if self.config.eve_enabled else 0.0,
            eve_exact_sifted_bits=eve_exact_sifted_bits,
            eve_exact_final_bits=eve_exact_final_bits if not aborted else 0,
            detection_probability=1.0 if self.config.eve_enabled and aborted else 0.0,
            aborted=aborted,
            security_status=security_status,
        )

        key_snapshots = [
            KeySnapshot("Alice raw bits", alice_bits),
            KeySnapshot("Alice sifted key", alice_sifted_bits),
            KeySnapshot("Alice after checking and reconciliation", alice_post_check),
            KeySnapshot("Alice final shared key", alice_final_key),
        ]

        if not aborted and alice_final_key != bob_final_key:
            raise RuntimeError("Protocol ended successfully, but Alice and Bob derived different keys.")

        return RunResult(
            config=self.config,
            traces=traces,
            alice_bits=alice_bits,
            alice_bases=alice_bases,
            bob_bases=bob_bases,
            eve_bases=eve_bases,
            sifted_positions=sifted_positions,
            error_check_positions=error_check_positions,
            remaining_positions=remaining_positions,
            key_snapshots=key_snapshots,
            alice_final_key=alice_final_key,
            bob_final_key=bob_final_key,
            eve_final_key_knowledge=stats.eve_exact_final_bits,
            stats=stats,
            aborted=aborted,
            abort_reason=abort_reason,
        )


def run_trials(config: ProtocolConfig, trial_count: int = 100) -> BatchStatistics:
    if trial_count <= 0:
        raise ValueError("trial_count must be positive.")

    basis_rates: List[float] = []
    error_rates: List[float] = []
    efficiencies: List[float] = []
    final_lengths: List[int] = []
    detections = 0
    eve_info_before: List[int] = []
    eve_info_after: List[int] = []

    base_seed = config.seed if config.seed is not None else random.randint(0, 10_000_000)
    for offset in range(trial_count):
        trial_config = replace(config, seed=base_seed + offset)
        result = BB84Protocol(trial_config).run()
        basis_rates.append(result.stats.basis_match_rate)
        error_rates.append(result.stats.error_rate)
        efficiencies.append(result.stats.efficiency)
        final_lengths.append(result.stats.final_key_length)
        detections += int(result.aborted and config.eve_enabled)
        eve_info_before.append(result.stats.eve_exact_sifted_bits)
        eve_info_after.append(result.stats.eve_exact_final_bits)

    return BatchStatistics(
        trials=trial_count,
        average_basis_match_rate=sum(basis_rates) / trial_count,
        average_error_rate=sum(error_rates) / trial_count,
        average_efficiency=sum(efficiencies) / trial_count,
        average_final_key_length=sum(final_lengths) / trial_count,
        detection_rate=detections / trial_count,
        average_eve_information_before_privacy=sum(eve_info_before) / trial_count,
        average_eve_information_after_privacy=sum(eve_info_after) / trial_count,
    )
