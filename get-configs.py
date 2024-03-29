from time import sleep

from websockets.exceptions import ConnectionClosedError

import solmate_sdk
from solmate_sdk.utils import retry
from websockets.exceptions import ConnectionClosedError

client = solmate_sdk.SolMateAPIClient('S1K0506A0000xxxx')

# Local
#client = solmate_sdk.LocalSolMateAPIClient('S1K0506A0000xxxx')
#client.uri = "ws://192.168.x.x:9124/"

# client = solmate_sdk.SolMateAPIClient(sn)
client.quickstart()
def run_continuously():
    client.quickstart()
    while True:
        print(f"Solmate {client.serialnum}: {client.get_live_values()}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.get_recent_logs()}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.get_software_version()}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.get_grid_mode()}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.get_user_settings()}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.set_min_injection(50)}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.set_max_injection(200)}")
        sleep(0.1)
        print(f"Solmate {client.serialnum}: {client.get_injection_settings()}")
        sleep(10)


if __name__ == "__main__":
    run_continuously()
