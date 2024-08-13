from ipaddress import IPv4Address
from typing import Any

from pydantic import BaseModel


class Neighbor(BaseModel):
    hostname: str
    ip: IPv4Address | None

    def __hash__(self):
        return hash((self.hostname, self.ip))


class CiscoCDP(BaseModel):
    device_id: str
    entry_ip: IPv4Address | None
    platform: str
    interface: str
    outgoing_port: str
    duplex: str
    management_ip: IPv4Address | None

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        elif isinstance(other, CiscoLLDP):
            return (self.device_id == other.system_name) and (
                self.management_ip == other.management_ip
            )
        else:
            return False


class CiscoLLDP(BaseModel):
    chassis_id: str  # A MAC address that is discovered by LLDP
    port_id: str  # An Interface number of opposite side device
    interface: str
    system_name: str
    management_ip: IPv4Address | None

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        elif isinstance(other, CiscoCDP):
            return (self.system_name == other.device_id) and (
                self.management_ip == other.management_ip
            )
        else:
            return False
