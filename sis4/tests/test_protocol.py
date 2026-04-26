import unittest

from bb84_sim.protocol import BB84Protocol, ProtocolConfig, run_trials


class BB84ProtocolTests(unittest.TestCase):
    def test_basis_match_rate_is_close_to_half(self) -> None:
        config = ProtocolConfig(photon_count=4000, seed=7)
        result = BB84Protocol(config).run()
        self.assertGreater(result.stats.basis_match_rate, 0.47)
        self.assertLess(result.stats.basis_match_rate, 0.53)

    def test_protocol_succeeds_without_eve(self) -> None:
        config = ProtocolConfig(photon_count=1200, error_check_fraction=0.12, seed=12)
        result = BB84Protocol(config).run()
        self.assertFalse(result.aborted)
        self.assertEqual(result.stats.error_rate, 0.0)
        self.assertEqual(result.alice_final_key, result.bob_final_key)
        self.assertGreater(result.stats.final_key_length, 0)

    def test_protocol_handles_channel_noise_with_reconciliation(self) -> None:
        config = ProtocolConfig(
            photon_count=4000,
            error_check_fraction=0.12,
            error_threshold=0.11,
            channel_noise=0.02,
            seed=25,
        )
        result = BB84Protocol(config).run()
        self.assertFalse(result.aborted)
        self.assertEqual(result.alice_final_key, result.bob_final_key)
        self.assertLess(result.stats.error_rate, 0.11)
        self.assertGreaterEqual(result.stats.corrected_remaining_errors, 0)

    def test_protocol_aborts_with_eavesdropper(self) -> None:
        config = ProtocolConfig(
            photon_count=4000,
            error_check_fraction=0.12,
            error_threshold=0.11,
            eve_enabled=True,
            seed=21,
        )
        result = BB84Protocol(config).run()
        self.assertTrue(result.aborted)
        self.assertGreater(result.stats.error_rate, 0.18)
        self.assertLess(result.stats.error_rate, 0.32)
        self.assertEqual(result.stats.final_key_length, 0)

    def test_multi_run_detection_rate_is_high_with_eve(self) -> None:
        config = ProtocolConfig(
            photon_count=1500,
            error_check_fraction=0.12,
            error_threshold=0.11,
            eve_enabled=True,
            seed=100,
        )
        summary = run_trials(config, trial_count=30)
        self.assertGreater(summary.average_basis_match_rate, 0.47)
        self.assertLess(summary.average_basis_match_rate, 0.53)
        self.assertGreater(summary.detection_rate, 0.95)
        self.assertGreater(summary.average_error_rate, 0.18)


if __name__ == "__main__":
    unittest.main()
