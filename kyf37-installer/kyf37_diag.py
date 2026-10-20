"""Kyocera factory diagnostic channel (USB 05c6:9091, interface 0, bulk OUT 0x01 / IN 0x81).

Protocol as documented in the project (docs/history/STATUS.md, device-inspection/probe_diag.py): HDLC-style framing
with CRC-16, command 0x4b 0xfc 0x81 0x20 = run a shell command as the diagnostic root user, 0xc0 = write the
factory flags word (only 0 or 4 allowed here), 0xc1 = read it back. Linux: libusb (needs a udev rule or sudo).
Windows: the WinUSB driver must be installed for interface 0 only (Zadig); interface 3 (ADB) stays as it is."""
import struct, time

VID, PID = 0x05c6, 0x9091


def crc(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x8408 if value & 1 else 0)
    return value ^ 0xffff


def encode(data):
    data += struct.pack('<H', crc(data))
    out = bytearray()
    for byte in data:
        out.extend((0x7d, byte ^ 0x20) if byte in (0x7d, 0x7e) else (byte,))
    return bytes(out) + b'\x7e'


def decode(data):
    out, esc = bytearray(), False
    for byte in data:
        if esc:
            out.append(byte ^ 0x20); esc = False
        elif byte == 0x7d:
            esc = True
        else:
            out.append(byte)
    if len(out) < 2 or crc(out[:-2]) != struct.unpack('<H', out[-2:])[0]:
        return None
    return bytes(out[:-2])


class Diag:
    def __init__(self):
        import usb.core, usb.util
        try:
            import libusb_package
            backend = libusb_package.get_libusb1_backend()
        except ImportError:
            backend = None
        self.usb = usb
        self.dev = usb.core.find(idVendor=VID, idProduct=PID, backend=backend)
        if self.dev is None:
            raise RuntimeError('diagnostic USB device 05c6:9091 not found (is the phone in diag mode and connected?)')
        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
        except (NotImplementedError, usb.core.USBError):
            pass
        usb.util.claim_interface(self.dev, 0)

    def close(self):
        self.usb.util.release_interface(self.dev, 0)
        self.usb.util.dispose_resources(self.dev)

    def _txn(self, header, payload, want_text):
        self.dev.write(0x01, encode(header + payload), timeout=2000)
        pending, chunks, deadline = bytearray(), [], time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                pending.extend(self.dev.read(0x81, 16384, timeout=500))
            except self.usb.core.USBTimeoutError:
                continue
            while 0x7e in pending:
                end = pending.index(0x7e)
                packet = decode(pending[:end]); del pending[:end + 1]
                if packet is None or not packet.startswith(header):
                    continue
                if not want_text:
                    return packet.hex()
                if len(packet) >= 9:
                    chunks.append(packet[9:].rstrip(b'\0').decode('utf-8', 'replace'))
                    if packet[8]:
                        return ''.join(chunks)
        raise RuntimeError('diagnostic command timed out')

    def shell(self, command):
        raw = command.encode()
        if len(raw) > 1023:
            raise ValueError('diagnostic command exceeds the 1023-byte protocol limit')
        return self._txn(b'\x4b\xfc\x81\x20', raw + b'\0', True)

    def factory_status(self):
        return self._txn(b'\x4b\xfc\xc1\x20', b'', False)

    def set_factory_flags(self, value):
        if value not in (0, 4):
            raise ValueError('only the recorded original value 0 and the verified permissive value 4 are allowed')
        return self._txn(b'\x4b\xfc\xc0\x20', struct.pack('<I', value), False)
