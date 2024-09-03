import re
from ipaddress import IPv4Address
from typing import List, Literal, Protocol, Set

from netmiko import BaseConnection

from networkst.errors import (
    CDPNotEnabledError,
    ConnectionFailedError,
    NotConnectedError,
)

from .connection import ConnectHandler
from .models import CiscoCDP, CiscoLLDP, Neighbor


class RemoteConnectable(Protocol):
    def connect(self, id_: str, pw: str):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError


class NeighborDetectable(Protocol):
    @property
    def neighbors(self) -> List[Neighbor]:
        raise NotImplementedError

    def get_cdp(self):
        raise NotImplementedError

    def get_lldp(self):
        raise NotImplementedError


class CiscoSwitch(RemoteConnectable, NeighborDetectable):
    def __init__(self, ip: IPv4Address):
        self.ip = ip
        self.cdp: List[CiscoCDP] = []
        self.lldp: List[CiscoLLDP] = []
        self.conn: BaseConnection | None = None
        self._hostname: str | None = None

    @property
    def hostname(self) -> str:
        if self._hostname:
            return self._hostname
        self._check_connection()
        self._hostname = self.conn.find_prompt()[:-1]
        return self._hostname

    @property
    def neighbors(self) -> List[Neighbor]:
        self._check_connection()
        cdp_results = [
            Neighbor(hostname=data.device_id, ip=data.management_ip)
            for data in self.cdp
        ]
        lldp_results = [
            Neighbor(hostname=data.system_name, ip=data.management_ip)
            for data in self.lldp
        ]
        neighbors = list(set(cdp_results + lldp_results))
        return neighbors

    def connect(self, id_: str, pw: str, secret: str = ""):
        try:
            self.conn = ConnectHandler(
                device_type="custom_cisco_ios",
                host=str(self.ip),
                username=id_,
                password=pw,
                port=22,
                secret=secret or pw,
            )
        except Exception:
            raise ConnectionFailedError()

    def disconnect(self):
        self._check_connection()
        self.conn.disconnect()

    def go_enable_mode(self):
        self._check_connection()
        return self.conn.enable(check_state=False)

    def activate_cdp(self):
        self._check_connection()
        self.conn.enable(check_state=False)
        return self.conn.send_config_set(["cdp run"]).split("\n")

    def activate_lldp(self):
        self._check_connection()
        self.conn.enable(check_state=False)
        return self.conn.send_config_set(["lldp run"]).split("\n")

    def deactivate_cdp(self):
        self._check_connection()
        self.conn.enable(check_state=False)
        return self.conn.send_config_set(["no cdp run"]).split("\n")

    def deactivate_lldp(self):
        self._check_connection()
        self.conn.enable(check_state=False)
        return self.conn.send_config_set(["no lldp run"]).split("\n")

    def show_running_config(self):
        self._check_connection()
        self.conn.enable(check_state=False)
        return self.conn.send_multiline(["show running-config"]).split("\n")

    def get_cdp(self) -> List[CiscoCDP]:
        self._check_connection()
        rows = self.conn.send_multiline(["show cdp neighbors detail"]).split("\n")
        for row in rows:
            if "CDP is not enabled" in row:
                raise CDPNotEnabledError
        blocks = "\r\n".join(rows).strip().split("-------------------------\r\n")
        result = []
        patterns = {
            "device_id": re.compile(r"Device ID: (?P<device_id>\S+)"),
            "entry_ip": re.compile(r"IP address: (?P<entry_ip>\d+\.\d+\.\d+\.\d+)"),
            "platform": re.compile(r"Platform: (?P<platform>.*?),"),
            "interface": re.compile(r"Interface: (?P<interface>\S+),"),
            "outgoing_port": re.compile(
                r"Port ID \(outgoing port\): (?P<outgoing_port>\S+)"
            ),
            "duplex": re.compile(r"Duplex: (?P<duplex>\S+)"),
            "management_ip": re.compile(
                r"Management address\(es\): \r\n  IP address: (?P<management_ip>\d+\.\d+\.\d+\.\d+)"  # noqa
            ),
        }
        for block in blocks:
            matched = {}
            for key, pattern in patterns.items():
                match = pattern.search(block)
                if match:
                    matched[key] = match.group(key)

            if len(matched) <= 2:
                continue

            entry_ip = matched.get("entry_ip")
            management_ip = matched.get("management_ip") or entry_ip

            matched.update(
                {
                    "entry_ip": IPv4Address(entry_ip) if entry_ip else None,
                    "management_ip": IPv4Address(management_ip) if entry_ip else None,
                }
            )
            result.append(CiscoCDP(**matched))
        if not result:
            print(f"No CDP results in {self.hostname} ({self.ip}).")

        self.cdp = result
        return result

    def get_lldp(self) -> List[CiscoLLDP]:
        assert self.conn is not None
        rows = self.conn.send_multiline(["show lldp neighbors detail"]).split("\n")
        blocks = (
            "\r\n".join(rows)
            .strip()
            .split("---------------------------------------------\r\n")
        )
        detail_result = []
        patterns = {
            "chassis_id": re.compile(r"Chassis id: (?P<chassis_id>\S+)"),
            "port_id": re.compile(r"Port id: (?P<port_id>\S+)"),
            "system_name": re.compile(r"System Name: (?P<system_name>\S+)"),
            "management_ip": re.compile(r"IP: (?P<management_ip>\d+\.\d+\.\d+\.\d+)"),
        }
        for block in blocks:
            matched = {}
            for key, pattern in patterns.items():
                match = pattern.search(block)
                if match:
                    matched[key] = match.group(key)

            if len(matched) < 4:
                continue

            management_ip = matched.get("management_ip")
            matched.update(
                {
                    "management_ip": (
                        IPv4Address(management_ip) if management_ip else None
                    ),
                }
            )
            detail_result.append(matched)

        if not detail_result:
            print(f"No LLDP results in {self.hostname} ({self.ip}).")

        # local interface 정보 수집
        rows = self.conn.send_multiline(["show lldp neighbors"]).split("\n")

        local_intf_mapping = {}
        for line in rows:
            match = re.search(r"(\S+)\s+(\S+)", line)
            if match:
                device_id, local_intf = match.groups()
                local_intf_mapping[device_id] = local_intf

        for item in detail_result:
            device_id = item.get("system_name")
            if local_intf := local_intf_mapping.get(device_id):
                item["interface"] = local_intf

        result = [CiscoLLDP(**each) for each in detail_result]
        self.lldp = result
        return result

    def _check_connection(self) -> None:
        if self.conn.find_prompt() is None:
            raise NotConnectedError


class ExtremeSwitch(RemoteConnectable, NeighborDetectable):
    """Extreme Networks의 ExtremeOS를 사용하는 스위치를 위한 인터페이스를 구현합니다."""

    def __init__(self, ip: IPv4Address):
        self.ip = ip
        self.ip_arp: Set[IPv4Address] = set()
        self.cdp_ne: Set[IPv4Address] = set()
        self.conn: BaseConnection | None = None

    def neighbors(self):
        return []

    def connect(self, id_: str, pw: str):
        raise NotImplementedError

    def disconnect(self):
        assert self.conn is not None
        self.conn.disconnect()

    def get_cdp(self):
        raise NotImplementedError

    def get_lldp(self):
        raise NotImplementedError


def get_switch(
    ip: IPv4Address, vendor: Literal["cisco", "extreme"] = "cisco"
) -> CiscoSwitch | ExtremeSwitch:
    if vendor == "cisco":
        return CiscoSwitch(ip=ip)
    elif vendor == "extreme":
        return ExtremeSwitch(ip=ip)
    else:
        raise Exception
