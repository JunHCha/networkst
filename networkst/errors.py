class NotConnectedError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "SSH connection is not established. Call connect() method first."
        )


class ConnectionFailedError(Exception):
    def __init__(self) -> None:
        super().__init__("SSH connection failed. Check your username and password.")


class CDPNotEnabledError(Exception):
    def __init__(self) -> None:
        super().__init__("CDP is not enabled on the switch.")


class LLDPNotEnabledError(Exception):
    def __init__(self) -> None:
        super().__init__("LLDP is not enabled on the switch.")
