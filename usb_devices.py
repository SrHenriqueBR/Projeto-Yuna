"""Metadados USB presentes, via APIs nativas do Windows, sem abrir volumes.

Identificadores ficam apenas na RAM para comparar snapshots. O tipo de conector
vem do hub (usbioctl.h), nunca do nome comercial ou da velocidade do dispositivo.
"""
import ctypes as C
from dataclasses import dataclass, field
import re
import struct
import sys
import unicodedata
import uuid


def device_label(value):
    text = "".join(c for c in str(value or "")
                   if not unicodedata.category(c).startswith("C"))
    text = " ".join(text.split())
    if not text or re.search(r"(?:USB|HID|USBSTOR)\\|VID_[0-9A-F]{4}", text, re.I):
        return "Dispositivo USB"
    return text[:70]


@dataclass(frozen=True)
class USBDevice:
    key: str = field(repr=False)
    name: str = "Dispositivo USB"
    type_c: bool = False  # True só com confirmação positiva do driver do hub.

    @property
    def label(self):
        return device_label(self.name) + (" (USB-C)" if self.type_c else " (USB)")


def physical_usb_id(value):
    parts = value.upper().split("\\")
    return (len(parts) == 3 and parts[0] == "USB" and bool(parts[2])
            and re.fullmatch(r"VID_[0-9A-F]{4}&PID_[0-9A-F]{4}(?:&REV_[0-9A-F]{4})?",
                             parts[1]) is not None)


# Tipos de largura fixa: também permitem testar layouts fora do Windows.
DWORD = C.c_uint32
BOOL = C.c_int32
HANDLE = C.c_void_p
PTR = C.c_void_p
PDWORD = C.POINTER(DWORD)


class GUID(C.Structure):
    _fields_ = [("a", DWORD), ("b", C.c_uint16), ("c", C.c_uint16),
               ("d", C.c_ubyte * 8)]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


class DEVINFO(C.Structure):
    _fields_ = [("size", DWORD), ("guid", GUID), ("devinst", DWORD),
               ("reserved", C.c_size_t)]


class INTERFACE(C.Structure):
    _fields_ = [("size", DWORD), ("guid", GUID), ("flags", DWORD),
               ("reserved", C.c_size_t)]


class DEVPROPKEY(C.Structure):
    _fields_ = [("guid", GUID), ("pid", DWORD)]


HUB_GUID = GUID.parse("f18a0e88-c30c-11d0-8815-00a0c906bed8")
BUS_DESCRIPTION = DEVPROPKEY(GUID.parse("540b947e-8b40-45bc-a8a2-6a0b894cbda2"), 4)
IOCTL_HUB_INFORMATION = (0x22 << 16) | (277 << 2)
IOCTL_PORT_CONNECTOR = (0x22 << 16) | (278 << 2)
INVALID_HANDLE = C.c_void_p(-1).value
MAX_DEVICES = 512


class WindowsUSB:
    """Une devnode físico ao hub pai/porta; não pede privilégios de administrador."""

    def __init__(self):
        self.setup = C.WinDLL("setupapi", use_last_error=True)
        self.cfg = C.WinDLL("cfgmgr32", use_last_error=True)
        self.kernel = C.WinDLL("kernel32", use_last_error=True)
        signatures = [
            (self.setup, "SetupDiGetClassDevsW", HANDLE, [PTR, C.c_wchar_p, HANDLE, DWORD]),
            (self.setup, "SetupDiEnumDeviceInfo", BOOL, [HANDLE, DWORD, PTR]),
            (self.setup, "SetupDiGetDeviceInstanceIdW", BOOL,
             [HANDLE, PTR, PTR, DWORD, PDWORD]),
            (self.setup, "SetupDiGetDeviceRegistryPropertyW", BOOL,
             [HANDLE, PTR, DWORD, PDWORD, PTR, DWORD, PDWORD]),
            (self.setup, "SetupDiGetDevicePropertyW", BOOL,
             [HANDLE, PTR, PTR, PDWORD, PTR, DWORD, PDWORD, DWORD]),
            (self.setup, "SetupDiEnumDeviceInterfaces", BOOL,
             [HANDLE, PTR, PTR, DWORD, PTR]),
            (self.setup, "SetupDiGetDeviceInterfaceDetailW", BOOL,
             [HANDLE, PTR, PTR, DWORD, PDWORD, PTR]),
            (self.setup, "SetupDiDestroyDeviceInfoList", BOOL, [HANDLE]),
            (self.cfg, "CM_Get_Parent", DWORD, [PDWORD, DWORD, DWORD]),
            (self.kernel, "CreateFileW", HANDLE,
             [C.c_wchar_p, DWORD, DWORD, PTR, DWORD, DWORD, HANDLE]),
            (self.kernel, "DeviceIoControl", BOOL,
             [HANDLE, DWORD, PTR, DWORD, PTR, DWORD, PDWORD, PTR]),
            (self.kernel, "CloseHandle", BOOL, [HANDLE]),
        ]
        for library, name, restype, argtypes in signatures:
            func = getattr(library, name)
            func.restype, func.argtypes = restype, argtypes

    def _list(self, guid, enumerator, flags):
        handle = self.setup.SetupDiGetClassDevsW(guid, enumerator, None, flags)
        if handle in (None, INVALID_HANDLE):
            raise OSError("Não foi possível consultar os dispositivos USB.")
        return handle

    def _property(self, handle, info, prop):
        data, kind, size = C.create_string_buffer(8192), DWORD(), DWORD()
        if not self.setup.SetupDiGetDeviceRegistryPropertyW(
                handle, C.byref(info), prop, C.byref(kind), data,
                C.sizeof(data), C.byref(size)):
            return None
        if kind.value == 1 and 0 < size.value <= C.sizeof(data):  # REG_SZ
            return data.raw[:size.value].decode("utf-16-le", "replace").split("\0")[0]
        if kind.value == 4 and size.value == 4:  # REG_DWORD
            return struct.unpack_from("<I", data.raw)[0]
        return None

    def _name(self, handle, info):
        # O descritor do barramento identifica melhor periféricos compostos.
        data, kind, size = C.create_string_buffer(8192), DWORD(), DWORD()
        if self.setup.SetupDiGetDevicePropertyW(
                handle, C.byref(info), C.byref(BUS_DESCRIPTION), C.byref(kind),
                data, C.sizeof(data), C.byref(size), 0):
            if kind.value == 0x12 and 0 < size.value <= C.sizeof(data):  # DEVPROP_TYPE_STRING
                name = data.raw[:size.value].decode("utf-16-le", "replace").split("\0")[0]
                if name.strip():
                    return device_label(name)
        return device_label(self._property(handle, info, 12)
                            or self._property(handle, info, 0))

    def _hubs(self):
        handle = self._list(C.byref(HUB_GUID), None, 0x12)  # PRESENT | DEVICEINTERFACE
        hubs = {}
        try:
            for index in range(MAX_DEVICES):
                interface = INTERFACE()
                interface.size = C.sizeof(interface)
                if not self.setup.SetupDiEnumDeviceInterfaces(
                        handle, None, C.byref(HUB_GUID), index, C.byref(interface)):
                    if C.get_last_error() == 259:  # ERROR_NO_MORE_ITEMS
                        return hubs
                    raise OSError("Lista de hubs indisponível.")
                size = DWORD()
                self.setup.SetupDiGetDeviceInterfaceDetailW(
                    handle, C.byref(interface), None, 0, C.byref(size), None)
                if not 6 <= size.value <= 65536:
                    continue
                data = C.create_string_buffer(size.value)
                # sizeof(DETAIL_W) é 8 em x64 e 6 em x86; DevicePath começa no byte 4.
                struct.pack_into("<I", data, 0, 8 if C.sizeof(HANDLE) == 8 else 6)
                info = DEVINFO()
                info.size = C.sizeof(info)
                if self.setup.SetupDiGetDeviceInterfaceDetailW(
                        handle, C.byref(interface), data, size.value, None, C.byref(info)):
                    hubs[info.devinst] = data.raw[4:].decode("utf-16-le", "replace").split("\0")[0]
            raise OSError("Lista de hubs excedeu o limite.")
        finally:
            self.setup.SetupDiDestroyDeviceInfoList(handle)

    def _ioctl(self, handle, code, data):
        size = DWORD()
        ok = self.kernel.DeviceIoControl(handle, code, data, C.sizeof(data),
                                         data, C.sizeof(data), C.byref(size), None)
        return size.value if ok else 0

    def _type_c(self, path, port):
        if not path or type(port) is not int or not 1 <= port <= 255:
            return False
        # DesiredAccess=0: somente consultas FILE_ANY_ACCESS, sem escrita/leitura de mídia.
        handle = self.kernel.CreateFileW(path, 0, 3, None, 3, 0, None)
        if handle in (None, INVALID_HANDLE):
            return False
        try:
            hub = C.create_string_buffer(256)
            if self._ioctl(handle, IOCTL_HUB_INFORMATION, hub) < 6:
                return False
            highest = struct.unpack_from("<H", hub.raw, 4)[0]
            if not port <= highest <= 255:
                return False
            # usbioctl.h usa pack(1); a estrutura fixa ocupa 18 bytes.
            data = C.create_string_buffer(18)
            struct.pack_into("<I", data, 0, port)
            if self._ioctl(handle, IOCTL_PORT_CONNECTOR, data) < 18:
                return False
            actual = struct.unpack_from("<I", data.raw, 4)[0]
            if not 18 <= actual <= 65536:
                return False
            if actual > 18:
                data = C.create_string_buffer(actual)
                struct.pack_into("<I", data, 0, port)
                if self._ioctl(handle, IOCTL_PORT_CONNECTOR, data) < 18:
                    return False
            flags = struct.unpack_from("<I", data.raw, 8)[0]
            return bool(flags & (1 << 3))  # PortConnectorIsTypeC, não USB 3.x.
        finally:
            self.kernel.CloseHandle(handle)

    def snapshot(self):
        handle = self._list(None, "USB", 0x06)  # PRESENT | ALLCLASSES
        rows = []
        try:
            for index in range(MAX_DEVICES):
                info = DEVINFO()
                info.size = C.sizeof(info)
                if not self.setup.SetupDiEnumDeviceInfo(handle, index, C.byref(info)):
                    if C.get_last_error() == 259:
                        break
                    raise OSError("Consulta USB incompleta.")
                identity = C.create_unicode_buffer(1024)
                if not self.setup.SetupDiGetDeviceInstanceIdW(
                        handle, C.byref(info), identity, len(identity), None):
                    raise OSError("Dispositivo mudou durante a consulta.")
                if not physical_usb_id(identity.value):
                    continue  # Exclui controladores/root hubs e interfaces MI de compostos.
                parent = DWORD()
                parent_id = (parent.value if self.cfg.CM_Get_Parent(
                    C.byref(parent), info.devinst, 0) == 0 else None)
                rows.append((identity.value.upper(), self._name(handle, info),
                             parent_id, self._property(handle, info, 0x1C)))
            else:
                raise OSError("Lista USB excedeu o limite.")
        finally:
            self.setup.SetupDiDestroyDeviceInfoList(handle)
        if not rows:
            return ()
        try:
            hubs = self._hubs()
        except OSError:
            hubs = {}  # USB continua detectável mesmo sem informação do conector.
        return tuple(USBDevice(key, name, self._type_c(hubs.get(parent), port))
                     for key, name, parent, port in rows)


def read_usb_devices():
    """None é falha/indisponibilidade, () é uma lista válida vazia."""
    if sys.platform != "win32":
        return None
    try:
        return WindowsUSB().snapshot()
    except (OSError, AttributeError, ValueError):
        return None
