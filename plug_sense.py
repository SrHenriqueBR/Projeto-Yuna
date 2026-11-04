"""Transições de USB/energia; sem modelo, rede, arquivos ou execução de comandos."""
from dataclasses import dataclass

from battery_life import read_external_power
from usb_devices import USBDevice, read_usb_devices


@dataclass(frozen=True)
class PlugSnapshot:
    usb: tuple[USBDevice, ...] | None
    power: bool | None


def read_plugs():
    return PlugSnapshot(read_usb_devices(), read_external_power())


def _labels(devices):
    ordered = sorted(devices, key=lambda device: device.label.casefold())
    label = ", ".join(device.label for device in ordered[:3])
    if len(ordered) > 3:
        label += f" e mais {len(ordered) - 3}"
    return label


class PlugTracker:
    """Primeiro snapshot, retomada e recuperação de erro criam uma base silenciosa."""

    def __init__(self):
        self.usb = None
        self.power = None

    def observe(self, snapshot):
        messages = []
        current = None if snapshot.usb is None else {d.key: d for d in snapshot.usb}
        if current is not None and self.usb is not None:
            added = current.keys() - self.usb.keys()
            removed = self.usb.keys() - current.keys()
            if added:
                messages.append("Percebi uma conexão: " + _labels(current[k] for k in added) + ".")
            if removed:
                messages.append("Percebi uma desconexão: " + _labels(self.usb[k] for k in removed) + ".")
        power_changed = (snapshot.power is not None and self.power is not None
                         and snapshot.power != self.power)
        if power_changed:
            messages.append("Energia externa conectada! Estou na tomada. ⚡" if snapshot.power
                            else "A alimentação externa foi desconectada.")
        self.usb, self.power = current, snapshot.power
        return "\n".join(messages), power_changed


def describe_plugs(snapshot):
    """Consulta determinística; nomes de hardware nunca entram no prompt do modelo."""
    if snapshot is None:
        return "Ainda estou consultando as conexões do computador."
    usb = ("USB: leitura indisponível." if snapshot.usb is None else
           "USB: nenhum dispositivo identificado." if not snapshot.usb else
           "USB presentes: " + _labels(snapshot.usb) + ".")
    power = ("Energia: estado indisponível." if snapshot.power is None else
             "Energia externa conectada." if snapshot.power else "Sem alimentação externa.")
    return usb + "\n" + power + "\nUSB-C só é indicado quando confirmado pelo Windows."


def plug_intent(text):
    from companion_commands import command
    value = command(text)
    return value in ("/conexoes", "mostre as conexoes", "verifique as conexoes",
                     "quais dispositivos estao conectados", "o que esta conectado")
