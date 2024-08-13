# Networkst

Networkst is a Python library for network connectivity testing. It provides a simple and intuitive way to check the availability of network resources and diagnose network issues.

## Features

- Remote connection test: Check if a host is reachable by SSH connection.
- Port scan: Scan a range of ports on a host to check for open or closed ports.
- Discover neighbor devices: Use LLDP and CDP protocols to discover neighboring network devices.


## Usage

Here's a simple example of how to use NetCheckPy to perform a connection test:

```python
from ipaddress import IPv4Address
from netcheckpy import get_switch
from networkst.errors import ConnectionFailedError

switch = get_switch(
    ip=IPv4Address("10.0.0.1"), vendor="cisco"
)

try:
    switch.connect(id_="user", pw="password")
    print(f"{switch.ip}: {switch.hostname} is reachable.")
except ConnectionFailedError:
    print(f"Something wrong with VTY of {switch.ip}")
```

## License

Networkst is licensed under the MIT License. See the [LICENSE](https://github.com/junhyungcha/netcheckpy/blob/main/LICENSE) file for more details.

