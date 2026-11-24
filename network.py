"""Turtle GUI ağ yardımcıları.

Yalnızca kullanıcının bağlı olduğu özel LAN üzerinde keşif yapar. Paket
izleme, Scapy ile yalnızca başlık metaverisini döndürür; payload okunmaz.
"""
from __future__ import annotations

import ipaddress
import os
import platform
import re
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable, Iterable

import psutil

APP_VERSION = "1.1.0"

VENDORS = {
    "001A11": "Google", "3C5AB4": "Google", "F4F5D8": "Google",
    "001CB3": "Apple", "A4D1D2": "Apple", "F0DCE2": "Apple",
    "000C29": "VMware", "080027": "VirtualBox", "B827EB": "Raspberry Pi",
    "DCA632": "Raspberry Pi", "001018": "Broadcom", "0050F2": "Microsoft",
    "001E58": "D-Link", "C83A35": "Tenda", "50C7BF": "TP-Link",
    "F4F26D": "TP-Link", "0026B6": "Askey", "A0F3C1": "TP-Link",
}


def get_interfaces() -> list[dict]:
    """List network interfaces using the operating system's interface table."""
    addresses = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    rows: list[dict] = []
    for name, addrs in addresses.items():
        ipv4 = "-"
        mac = "-"
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ipv4 = addr.address
            elif getattr(psutil, "AF_LINK", object()) == addr.family:
                mac = addr.address or "-"
        state = "AÇIK" if stats.get(name) and stats[name].isup else "KAPALI"
        rows.append({"name": name, "state": state, "ipv4": ipv4, "mac": mac})
    return sorted(rows, key=lambda r: (r["state"] != "AÇIK", r["name"].lower()))


def _run(args: list[str], timeout: float = 12.0) -> str:
    completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                               errors="replace", check=False)
    if completed.returncode != 0 and not completed.stdout.strip():
        detail = completed.stderr.strip() or f"Komut başarısız oldu: {args[0]}"
        raise RuntimeError(detail)
    return completed.stdout


def _split_nmcli_row(row: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for char in row:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def scan_wifi() -> list[dict]:
    """Use native OS Wi-Fi listing commands (no injection/deauth)."""
    system = platform.system()
    rows: list[dict] = []
    if system == "Linux":
        try:
            output = _run(["nmcli", "-t", "-f", "SSID,BSSID,CHAN,SIGNAL,SECURITY",
                           "dev", "wifi", "list", "--rescan", "yes"])
        except (FileNotFoundError, RuntimeError) as exc:
            raise RuntimeError("nmcli bulunamadı veya çalışmadı. NetworkManager kurulu ve etkin mi?") from exc
        for line in output.splitlines():
            p = _split_nmcli_row(line)
            if len(p) >= 5:
                rows.append({"ssid": p[0] or "<gizli ağ>", "bssid": p[1] or "-",
                             "channel": p[2] or "-", "signal": (p[3] + "%") if p[3] else "-",
                             "security": p[4] or "AÇIK"})
    elif system == "Windows":
        output = _run(["netsh", "wlan", "show", "networks", "mode=bssid"])
        current: dict | None = None
        for line in output.splitlines():
            m = re.match(r"\s*SSID\s+\d+\s*:\s*(.*)", line, re.I)
            if m:
                if current:
                    rows.append(current)
                current = {"ssid": m.group(1).strip() or "<gizli ağ>", "bssid": "-",
                           "channel": "-", "signal": "-", "security": "-"}
                continue
            if current is None:
                continue
            for key, pattern in (("bssid", r"BSSID\s+\d+\s*:\s*(.*)"),
                                 ("signal", r"Signal\s*:\s*(.*)"),
                                 ("channel", r"Channel\s*:\s*(.*)"),
                                 ("security", r"Authentication\s*:\s*(.*)")):
                m = re.match(r"\s*" + pattern, line, re.I)
                if m:
                    current[key] = m.group(1).strip()
        if current:
            rows.append(current)
    elif system == "Darwin":
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        try:
            if os.path.exists(airport):
                output = _run([airport, "-s"])
                for line in output.splitlines()[1:]:
                    m = re.match(r"\s*(.*?)\s+([0-9a-f:]{17})\s+(-?\d+)\s+(\S+)(?:\s+.*)?$", line, re.I)
                    if m:
                        rows.append({"ssid": m.group(1).strip() or "<gizli ağ>",
                                     "bssid": m.group(2), "channel": m.group(4),
                                     "signal": f"{m.group(3)} dBm", "security": "-"})
            else:
                output = _run(["system_profiler", "SPAirPortDataType"], timeout=25)
                # system_profiler output is intentionally treated as a fallback text source.
                for block in re.split(r"\n\s{8,}(?=[^\s])", output):
                    ssid_match = re.search(r"\n\s{12,}([^\n:]+):\n", block)
                    bssid_match = re.search(r"BSSID:\s*([0-9a-f:]{17})", block, re.I)
                    if ssid_match:
                        rows.append({"ssid": ssid_match.group(1).strip(),
                                     "bssid": bssid_match.group(1) if bssid_match else "-",
                                     "channel": "-", "signal": "-", "security": "-"})
        except (FileNotFoundError, RuntimeError) as exc:
            raise RuntimeError("macOS Wi-Fi listesi alınamadı. macOS konum/Wi-Fi izinlerini kontrol et.") from exc
    else:
        raise RuntimeError(f"Desteklenmeyen işletim sistemi: {system}")
    return rows


def _interface_network(interface_name: str | None = None) -> tuple[str, ipaddress.IPv4Network]:
    addrs = psutil.net_if_addrs()
    candidates = [interface_name] if interface_name else list(addrs.keys())
    for name in candidates:
        if not name or name not in addrs:
            continue
        for addr in addrs[name]:
            if addr.family != socket.AF_INET or not addr.netmask:
                continue
            try:
                ip = ipaddress.ip_address(addr.address)
                network = ipaddress.ip_network(f"{addr.address}/{addr.netmask}", strict=False)
            except ValueError:
                continue
            if ip.is_private and not ip.is_loopback and not ip.is_link_local:
                # Bound discovery to at most a /22 to avoid broad network sweeps.
                if network.prefixlen < 22:
                    network = ipaddress.ip_network(f"{ip}/22", strict=False)
                return name, network
    raise RuntimeError("Özel IPv4 LAN arayüzü bulunamadı. Önce Wi-Fi/Ethernet ağına bağlan.")


def _ping(ip: str) -> bool:
    system = platform.system()
    if system == "Windows":
        args = ["ping", "-n", "1", "-w", "900", ip]
    elif system == "Darwin":
        args = ["ping", "-c", "1", "-W", "1000", ip]
    else:
        args = ["ping", "-c", "1", "-W", "1", ip]
    try:
        result = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=2.0, check=False)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _arp_table() -> dict[str, str]:
    try:
        output = _run(["arp", "-a"], timeout=5)
    except Exception:
        return {}
    found: dict[str, str] = {}
    ip_pattern = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
    mac_pattern = re.compile(r"(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}", re.I)
    for line in output.splitlines():
        ip_match, mac_match = ip_pattern.search(line), mac_pattern.search(line)
        if ip_match and mac_match:
            found[ip_match.group(0)] = mac_match.group(0).replace("-", ":").upper()
    return found


def _vendor(mac: str) -> str:
    compact = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
    if len(compact) < 6:
        return "Bilinmiyor"
    first = int(compact[:2], 16)
    if first & 0x02:
        return "Rastgele/yerel MAC"
    return VENDORS.get(compact[:6], "Bilinmiyor")


def discover_lan(interface_name: str | None = None,
                  progress: Callable[[int, int], None] | None = None) -> list[dict]:
    """Ping sweep the attached private LAN (capped at /22), then read ARP cache."""
    name, network = _interface_network(interface_name)
    hosts = [str(host) for host in network.hosts()]
    total = len(hosts)
    alive: set[str] = set()
    completed = 0
    lock = threading.Lock()

    def check(host: str) -> None:
        nonlocal completed
        if _ping(host):
            with lock:
                alive.add(host)
        with lock:
            completed += 1
            if progress and (completed % 16 == 0 or completed == total):
                progress(completed, total)

    # Bound concurrency and address count; no arbitrary target range is accepted.
    with ThreadPoolExecutor(max_workers=64) as pool:
        futures = [pool.submit(check, host) for host in hosts]
        for future in as_completed(futures):
            future.result()

    arp = _arp_table()
    local_ip = None
    for addr in psutil.net_if_addrs().get(name, []):
        if addr.family == socket.AF_INET:
            local_ip = addr.address
            break
    if local_ip:
        alive.add(local_ip)
    # ARP cache entries are included only when they belong to the selected subnet.
    for ip in arp:
        try:
            if ipaddress.ip_address(ip) in network:
                alive.add(ip)
        except ValueError:
            pass

    ordered_ips = sorted(alive, key=lambda value: int(ipaddress.ip_address(value)))

    def resolve(ip: str) -> tuple[str, str]:
        try:
            return ip, socket.gethostbyaddr(ip)[0]
        except (OSError, socket.herror):
            return ip, "-"

    hostnames: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=32) as pool:
        for ip, hostname in pool.map(resolve, ordered_ips):
            hostnames[ip] = hostname

    rows = []
    for ip in ordered_ips:
        mac = arp.get(ip, "-")
        rows.append({"ip": ip, "mac": mac, "vendor": _vendor(mac) if mac != "-" else "-",
                     "hostname": hostnames.get(ip, "-")})
    return rows


def parse_ports(value: str) -> list[int]:
    """Parse comma-separated ports/ranges with a strict upper bound."""
    result: set[int] = set()
    if not value.strip():
        raise ValueError("Port aralığı boş olamaz.")
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start, end = int(left), int(right)
            if start > end:
                raise ValueError(f"Geçersiz port aralığı: {part}")
            result.update(range(start, end + 1))
        else:
            result.add(int(part))
    if not result or min(result) < 1 or max(result) > 65535:
        raise ValueError("Portlar 1–65535 aralığında olmalı.")
    if len(result) > 4096:
        raise ValueError("Tek taramada en fazla 4096 port seçilebilir.")
    return sorted(result)


SERVICES = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
            80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
            3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 8080: "HTTP-Alt"}


def scan_ports(target: str, port_spec: str, authorized: bool = False,
               timeout: float = 0.75,
               progress: Callable[[int, int], None] | None = None) -> list[dict]:
    try:
        address = ipaddress.ip_address(target.strip())
    except ValueError as exc:
        raise ValueError("Hedef geçerli bir IPv4/IPv6 adresi olmalı.") from exc
    is_local = address.is_private or address.is_loopback or address.is_link_local
    if not is_local and not authorized:
        raise PermissionError("Hedef özel LAN adresi değil. Yalnızca yazılı izinli sistemler için yetki onayını işaretle.")
    ports = parse_ports(port_spec)
    open_rows: list[dict] = []
    completed = 0
    lock = threading.Lock()

    def probe(port: int) -> tuple[int, bool]:
        nonlocal completed
        opened = False
        try:
            with socket.socket(address.version == 6 and socket.AF_INET6 or socket.AF_INET,
                               socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                endpoint = (str(address), port, 0, 0) if address.version == 6 else (str(address), port)
                opened = sock.connect_ex(endpoint) == 0
        except OSError:
            opened = False
        with lock:
            completed += 1
            if progress and (completed % 32 == 0 or completed == len(ports)):
                progress(completed, len(ports))
        return port, opened

    with ThreadPoolExecutor(max_workers=128) as pool:
        futures = [pool.submit(probe, port) for port in ports]
        for future in as_completed(futures):
            port, opened = future.result()
            if opened:
                open_rows.append({"port": port, "service": SERVICES.get(port, "Bilinmiyor"),
                                  "state": "AÇIK"})
    return sorted(open_rows, key=lambda row: row["port"])


class PacketCapture:
    """Header-only packet capture powered by Scapy (optional dependency)."""
    def __init__(self, interface: str, packet_filter: str,
                 on_packet: Callable[[dict], None], on_error: Callable[[str], None]):
        self.interface = interface
        self.packet_filter = packet_filter
        self.on_packet = on_packet
        self.on_error = on_error
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="turtle-capture", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _run(self) -> None:
        try:
            from scapy.all import sniff, IP, IPv6, TCP, UDP, ICMP, ARP  # type: ignore
        except Exception as exc:
            self.on_error("Paket izleme için Scapy kurulmalı: python -m pip install scapy")
            return

        bpf = {"TCP": "tcp", "UDP": "udp", "ICMP": "icmp", "ARP": "arp",
               "DNS": "port 53", "Tümü": ""}.get(self.packet_filter, "")
        if self.packet_filter.startswith("Port:"):
            port_text = self.packet_filter.split(":", 1)[1].strip()
            if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
                self.on_error("Port filtresi 1–65535 arasında bir sayı olmalı.")
                return
            bpf = f"port {int(port_text)}"
        try:
            while not self.stop_event.is_set():
                packets = sniff(iface=self.interface or None, filter=bpf or None,
                                timeout=1, store=False)
                for packet in packets:
                    if self.stop_event.is_set():
                        break
                    now = datetime.now().strftime("%H:%M:%S")
                    source, dest, proto, info = "-", "-", "OTHER", "Başlık bilgisi"
                    if packet.haslayer(ARP):
                        layer = packet[ARP]
                        source, dest, proto = layer.psrc, layer.pdst, "ARP"
                        info = f"{layer.hwsrc} → {layer.hwdst}"
                    elif packet.haslayer(IP):
                        layer = packet[IP]
                        source, dest = layer.src, layer.dst
                        if packet.haslayer(TCP):
                            l4 = packet[TCP]; proto = "TCP"
                            info = f"{l4.sport} → {l4.dport} | flags={l4.flags}"
                        elif packet.haslayer(UDP):
                            l4 = packet[UDP]; proto = "DNS" if (l4.sport == 53 or l4.dport == 53) else "UDP"
                            info = f"{l4.sport} → {l4.dport}"
                        elif packet.haslayer(ICMP):
                            proto, info = "ICMP", f"type={packet[ICMP].type} code={packet[ICMP].code}"
                    elif packet.haslayer(IPv6):
                        layer = packet[IPv6]
                        source, dest, proto = layer.src, layer.dst, "IPv6"
                        if packet.haslayer(TCP):
                            proto = "TCP"; l4 = packet[TCP]; info = f"{l4.sport} → {l4.dport}"
                        elif packet.haslayer(UDP):
                            proto = "UDP"; l4 = packet[UDP]; info = f"{l4.sport} → {l4.dport}"
                    self.on_packet({"time": now, "source": source, "dest": dest,
                                    "protocol": proto, "info": info})
        except Exception as exc:
            self.on_error(f"Paket yakalama başlatılamadı: {exc}. macOS/Linux'ta yönetici izni gerekebilir.")
