from typing import Any

from netmiko.base_connection import BaseConnection
from netmiko.cisco.cisco_ios import CiscoIosBase
from netmiko.ssh_dispatcher import CLASS_MAPPER_BASE, FILE_TRANSFER_MAP


class CustomCiscoIosBase(CiscoIosBase):
    def set_base_prompt(
        self,
        pri_prompt_terminator: str = "#",
        alt_prompt_terminator: str = ">",
        delay_factor: float = 1.0,
        pattern: str | None = r".*[#>]$",
    ) -> str:
        """
        Cisco IOS/IOS-XE abbreviates the prompt at 20-chars in config mode.

        Consequently, abbreviate the base_prompt
        """
        base_prompt = super().set_base_prompt(
            pri_prompt_terminator=pri_prompt_terminator,
            alt_prompt_terminator=alt_prompt_terminator,
            delay_factor=delay_factor,
            pattern=pattern,
        )
        self.base_prompt = base_prompt[:16]
        return self.base_prompt

    def check_config_mode(
        self,
        check_string: str = ")#",
        pattern: str = r"[>#]$",
        force_regex: bool = False,
    ) -> bool:
        return super().check_config_mode(check_string=check_string, pattern=pattern)


CLASS_MAPPER_BASE["custom_cisco_ios"] = CustomCiscoIosBase
new_mapper = {}
for k, v in CLASS_MAPPER_BASE.items():
    new_mapper[k] = v
    alt_key = k + "_ssh"
    new_mapper[alt_key] = v
CLASS_MAPPER = new_mapper


platforms = list(CLASS_MAPPER.keys())
platforms.sort()
platforms_base = list(CLASS_MAPPER_BASE.keys())
platforms_base.sort()
platforms_str = "\n".join(platforms_base)
platforms_str = "\n" + platforms_str

scp_platforms = list(FILE_TRANSFER_MAP.keys())
scp_platforms.sort()
scp_platforms_str = "\n".join(scp_platforms)
scp_platforms_str = "\n" + scp_platforms_str

telnet_platforms = [x for x in platforms if "telnet" in x]
telnet_platforms_str = "\n".join(telnet_platforms)
telnet_platforms_str = "\n" + telnet_platforms_str


def ssh_dispatcher(device_type: str) -> BaseConnection:
    """Select the class to be instantiated based on vendor/platform."""
    return CLASS_MAPPER[device_type]


def ConnectHandler(*args: Any, **kwargs: Any) -> BaseConnection:
    """Factory function selects the proper class and creates object based on device_type."""
    device_type = kwargs["device_type"]
    if device_type not in platforms:
        if device_type is None:
            msg_str = platforms_str
        else:
            msg_str = telnet_platforms_str if "telnet" in device_type else platforms_str
        raise ValueError(
            "Unsupported 'device_type' "
            "currently supported platforms are: {}".format(msg_str)
        )
    ConnectionClass = ssh_dispatcher(device_type)
    return ConnectionClass(*args, **kwargs)
