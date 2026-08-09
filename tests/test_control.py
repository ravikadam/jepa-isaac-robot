import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from jepa_robot.control import CartesianAction, reached


class ControlTests(unittest.TestCase):
    def test_translation_is_clipped_by_norm(self):
        action = CartesianAction.from_sequence([0.3, 0.4, 0, 0, 0, 0, 0], 0.05)
        self.assertAlmostEqual(np.linalg.norm(action.translation), 0.05, places=6)

    def test_small_translation_is_unchanged(self):
        action = CartesianAction.from_sequence([0.01, -0.02, 0, 0, 0, 0, 0])
        np.testing.assert_allclose(action.translation, [0.01, -0.02, 0])

    def test_reach_threshold_is_inclusive(self):
        self.assertTrue(reached([0, 0, 0], [0.03, 0.04, 0], 0.05))
        self.assertFalse(reached([0, 0, 0], [0.051, 0, 0], 0.05))


if __name__ == "__main__":
    unittest.main()
