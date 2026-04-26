import random
import unittest

from bb84_sim.quantum import DIAGONAL, RECTILINEAR, measure_photon, prepare_photon


class QuantumMeasurementTests(unittest.TestCase):
    def test_same_basis_measurement_is_deterministic(self) -> None:
        rng = random.Random(1)
        for basis in (RECTILINEAR, DIAGONAL):
            for bit in (0, 1):
                photon = prepare_photon(bit, basis)
                for _ in range(50):
                    outcome = measure_photon(photon, basis, rng)
                    self.assertEqual(outcome.bit_value, bit)
                    self.assertTrue(outcome.deterministic)

    def test_different_basis_measurement_is_approximately_random(self) -> None:
        rng = random.Random(9)
        photon = prepare_photon(0, RECTILINEAR)
        ones = 0
        trials = 6000
        for _ in range(trials):
            outcome = measure_photon(photon, DIAGONAL, rng)
            ones += outcome.bit_value
        one_rate = ones / trials
        self.assertGreater(one_rate, 0.47)
        self.assertLess(one_rate, 0.53)


if __name__ == "__main__":
    unittest.main()
