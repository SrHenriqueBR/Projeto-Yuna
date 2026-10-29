import unittest
from hardware_profiles import recommend_profile, select_profile


class HardwareProfilesTests(unittest.TestCase):
    def test_eight_gb_is_light(self):
        self.assertEqual(recommend_profile(8, 0).name, "leve")

    def test_alienware_3070_is_advanced(self):
        self.assertEqual(recommend_profile(16, 8).name, "avancado")

    def test_midrange_is_balanced(self):
        self.assertEqual(recommend_profile(16, 4).name, "equilibrado")

    def test_missing_gpu_is_not_assumed(self):
        self.assertEqual(recommend_profile(16).name, "equilibrado")

    def test_bad_values_fall_back_safely(self):
        for ram, vram in [(None, 8), (8, -1), (0, 0), ("oops", 8)]:
            self.assertEqual(recommend_profile(ram, vram).name, "leve")

    def test_manual_profile_override(self):
        self.assertEqual(select_profile(8, 0, {"YUNA_PERFIL": "AVANCADO"}).name,
                         "avancado")
        self.assertEqual(select_profile(8, 0, {"YUNA_PERFIL": "invalid"}).name,
                         "leve")

    def test_advanced_is_not_prematurely_3d(self):
        self.assertEqual(recommend_profile(16, 8).renderer, "qt2d")
