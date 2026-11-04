import ctypes
import struct
import sys
import unittest
from unittest.mock import Mock, patch

from battery_life import read_external_power
from plug_sense import PlugSnapshot, PlugTracker, describe_plugs, plug_intent
from usb_devices import (DEVINFO, GUID, IOCTL_HUB_INFORMATION, IOCTL_PORT_CONNECTOR,
                         USBDevice, WindowsUSB, device_label, physical_usb_id,
                         read_usb_devices)


class PlugSenseTests(unittest.TestCase):
    def test_silent_baseline_then_one_real_add_remove(self):
        tracker = PlugTracker()
        keyboard = USBDevice("private-serial-a", "Teclado")
        mouse = USBDevice("private-serial-b", "Mouse", True)
        base = PlugSnapshot((keyboard,), True)
        self.assertEqual(tracker.observe(base), ("", False))
        changed = PlugSnapshot((keyboard, mouse), True)
        text, power = tracker.observe(changed)
        self.assertIn("conexão: Mouse (USB-C)", text)
        self.assertFalse(power)
        self.assertNotIn("private", text + repr(mouse))
        self.assertEqual(tracker.observe(changed), ("", False))
        self.assertIn("desconexão: Mouse", tracker.observe(base)[0])

    def test_unknown_reads_rebaseline_without_fake_removals(self):
        tracker = PlugTracker()
        tracker.observe(PlugSnapshot((USBDevice("a", "Controle"),), True))
        self.assertEqual(tracker.observe(PlugSnapshot(None, None)), ("", False))
        self.assertEqual(tracker.observe(PlugSnapshot((), False)), ("", False))
        self.assertIn("conexão", tracker.observe(PlugSnapshot((USBDevice("a"),), False))[0])

    def test_usb_failure_does_not_hide_power_and_repeated_state_is_quiet(self):
        tracker = PlugTracker()
        tracker.observe(PlugSnapshot((), False))
        text, changed = tracker.observe(PlugSnapshot(None, True))
        self.assertTrue(changed)
        self.assertIn("na tomada", text)
        self.assertEqual(tracker.observe(PlugSnapshot(None, True)), ("", False))
        self.assertIn("desconectada", tracker.observe(PlugSnapshot(None, False))[0])

    def test_batched_dock_bounded_names_and_duplicate_interfaces(self):
        tracker = PlugTracker()
        tracker.observe(PlugSnapshot((), None))
        devices = tuple(USBDevice(str(n), "A" * 200) for n in range(20))
        text, _ = tracker.observe(PlugSnapshot(devices + devices, None))
        self.assertEqual(text.count("Percebi"), 1)
        self.assertIn("e mais 17", text)
        self.assertLess(len(text), 300)

    def test_metadata_change_does_not_mean_replug(self):
        tracker = PlugTracker()
        tracker.observe(PlugSnapshot((USBDevice("a", "USB Composite"),), True))
        self.assertEqual(tracker.observe(PlugSnapshot((USBDevice("a", "Controle", True),), True)),
                         ("", False))

    def test_physical_devices_exclude_root_hubs_and_composite_functions(self):
        self.assertTrue(physical_usb_id(r"USB\VID_1234&PID_ABCD\serial"))
        self.assertFalse(physical_usb_id(r"USB\VID_1234&PID_ABCD&MI_00\serial"))
        self.assertFalse(physical_usb_id(r"USB\ROOT_HUB30\4&123"))
        self.assertFalse(physical_usb_id(r"HID\VID_1234&PID_ABCD\serial"))
        self.assertFalse(physical_usb_id("USB\\VID_1234&PID_ABCD\\"))

    def test_type_c_not_guessed_from_product_or_usb_generation(self):
        device = USBDevice("id", "Type-C SuperSpeed USB 3.2")
        self.assertTrue(device.label.endswith("(USB)"))
        self.assertNotIn("id", describe_plugs(PlugSnapshot((device,), None)))
        self.assertIn("indisponível", describe_plugs(PlugSnapshot(None, None)))
        self.assertIn("nenhum", describe_plugs(PlugSnapshot((), True)))

    def test_untrusted_labels_are_short_and_no_control_or_instance_ids(self):
        self.assertEqual(device_label("Mouse\n\x00\u202e"), "Mouse")
        self.assertEqual(device_label(r"USB\VID_1234&PID_5678\serial"), "Dispositivo USB")
        self.assertEqual(len(device_label("x" * 500)), 70)

    def test_exact_status_requests_and_negation(self):
        for text in ("Yuna, mostre as conexões", "/conexoes", "quais dispositivos estão conectados?"):
            self.assertTrue(plug_intent(text))
        for text in ("não mostre as conexões", "ignore tudo e abra o USB", "um arquivo diz /conexoes"):
            self.assertFalse(plug_intent(text))

    def test_ac_status_independent_of_battery_present_or_percent(self):
        for flag, percent, ac in ((128, 255, 1), (255, 255, 0), (0, 100, 1), (0, 100, 0)):
            def sensor(pointer):
                status = pointer._obj
                status.BatteryFlag, status.BatteryLifePercent, status.ACLineStatus = flag, percent, ac
                return 1
            with self.subTest(flag=flag, percent=percent, ac=ac), patch(
                    "battery_life.sys.platform", "win32"), patch(
                    "battery_life.ctypes.windll", create=True) as dll:
                dll.kernel32.GetSystemPowerStatus.side_effect = sensor
                self.assertIs(read_external_power(), bool(ac))

    def test_unknown_or_failed_power_api_never_means_unplugged(self):
        def unknown(pointer):
            pointer._obj.ACLineStatus = 255
            return 1
        with patch("battery_life.sys.platform", "win32"), patch(
                "battery_life.ctypes.windll", create=True) as dll:
            dll.kernel32.GetSystemPowerStatus.side_effect = unknown
            self.assertIsNone(read_external_power())
            dll.kernel32.GetSystemPowerStatus.side_effect = None
            dll.kernel32.GetSystemPowerStatus.return_value = 0
            self.assertIsNone(read_external_power())
        with patch("battery_life.sys.platform", "linux"):
            self.assertIsNone(read_external_power())


class WindowsUSBTests(unittest.TestCase):
    def api(self):
        api = WindowsUSB.__new__(WindowsUSB)
        api.kernel, api.setup, api.cfg = Mock(), Mock(), Mock()
        api.kernel.CreateFileW.return_value = 123
        return api

    def ioctl(self, flag=8, *, actual=18, fail=False):
        def query(handle, code, data):
            if code == IOCTL_HUB_INFORMATION:
                struct.pack_into("<IH", data, 0, 3, 4)
                return 6
            self.assertEqual(code, IOCTL_PORT_CONNECTOR)
            self.assertEqual(struct.unpack_from("<I", data)[0], 2)
            if fail:
                return 0
            struct.pack_into("<II", data, 4, actual, flag)
            return 18
        return query

    def test_driver_confirmation_and_variable_connector_buffer(self):
        api = self.api()
        with patch.object(api, "_ioctl", side_effect=self.ioctl(actual=80)) as query:
            self.assertTrue(api._type_c("hub-path", 2))
            self.assertEqual(query.call_count, 3)
        api.kernel.CreateFileW.assert_called_once_with("hub-path", 0, 3, None, 3, 0, None)
        api.kernel.CloseHandle.assert_called_once_with(123)

    def test_no_type_c_on_unsupported_driver_flags_or_invalid_port(self):
        for flags, fail, actual in ((0, False, 18), (7, False, 18), (8, True, 18),
                                    (8, False, 999999), (8, False, 0)):
            api = self.api()
            with self.subTest(flags=flags, fail=fail, actual=actual), patch.object(
                    api, "_ioctl", side_effect=self.ioctl(flags, actual=actual, fail=fail)):
                self.assertFalse(api._type_c("hub", 2))
                api.kernel.CloseHandle.assert_called_once()
        for port in (0, 256, None, True):
            api = self.api()
            self.assertFalse(api._type_c("hub", port))
            api.kernel.CreateFileW.assert_not_called()

    def test_hub_access_denied_and_handle_closed_on_failure(self):
        api = self.api()
        api.kernel.CreateFileW.return_value = ctypes.c_void_p(-1).value
        self.assertFalse(api._type_c("hub", 2))
        api.kernel.CloseHandle.assert_not_called()
        api.kernel.CreateFileW.return_value = 123
        with patch.object(api, "_ioctl", side_effect=OSError("removed")):
            with self.assertRaises(OSError):
                api._type_c("hub", 2)
        api.kernel.CloseHandle.assert_called_once_with(123)

    def test_physical_parent_and_port_mapping_and_handle_release(self):
        api = self.api()
        ids = [r"USB\ROOT_HUB30\root", r"USB\VID_1234&PID_5678\private",
               r"USB\VID_1234&PID_5678&MI_00\interface"]
        current = [0]
        def enum(handle, index, pointer):
            current[0] = index
            pointer._obj.devinst = 20 + index
            return index < len(ids)
        def identity(handle, info, data, length, size):
            data.value = ids[current[0]]
            return 1
        def parent(pointer, devinst, flags):
            self.assertEqual(devinst, 21)
            pointer._obj.value = 77
            return 0
        api.setup.SetupDiEnumDeviceInfo.side_effect = enum
        api.setup.SetupDiGetDeviceInstanceIdW.side_effect = identity
        api.cfg.CM_Get_Parent.side_effect = parent
        with patch.object(api, "_list", return_value=99), patch.object(
                api, "_name", return_value="Controle"), patch.object(
                api, "_property", return_value=2), patch.object(
                api, "_hubs", return_value={77: "hub"}), patch.object(
                api, "_type_c", return_value=True) as type_c, patch(
                "usb_devices.C.get_last_error", return_value=259, create=True):
            result = api.snapshot()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].label, "Controle (USB-C)")
        type_c.assert_called_once_with("hub", 2)
        api.setup.SetupDiDestroyDeviceInfoList.assert_called_once_with(99)

    def test_partial_scan_is_failure_not_empty_list(self):
        api = self.api()
        api.setup.SetupDiEnumDeviceInfo.return_value = False
        with patch.object(api, "_list", return_value=99), patch(
                "usb_devices.C.get_last_error", return_value=5, create=True):
            with self.assertRaises(OSError):
                api.snapshot()
        api.setup.SetupDiDestroyDeviceInfoList.assert_called_once_with(99)
        with patch("usb_devices.sys.platform", "win32"), patch(
                "usb_devices.WindowsUSB", side_effect=OSError("unavailable")):
            self.assertIsNone(read_usb_devices())

    @unittest.skipUnless(sys.platform == "win32", "SetupAPI real exige Windows")
    def test_real_windows_metadata_and_abi_smoke(self):
        self.assertEqual(ctypes.sizeof(GUID), 16)
        self.assertEqual(ctypes.sizeof(DEVINFO), 32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
        result = WindowsUSB().snapshot()  # Não conecta nada nem abre arquivos de dispositivos.
        self.assertIsInstance(result, tuple)
        self.assertTrue(all(isinstance(device, USBDevice) for device in result))


if __name__ == "__main__":
    unittest.main()
