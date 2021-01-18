import argparse as ap
import time
from reservation_interfaces.listener import Listener


def main(iface=None, ip=None, mac=None):
    Listener(iface, ip, mac)
    time.sleep(1000)

if __name__ == '__main__':
    parser = ap.ArgumentParser(
        description="Run a real-time stream listener implementing the model "\
                    "from `Deployment of Real-Time Network Streams with "\
                    "Standard Ethernet Switches`")

    parser.add_argument(
        '--iface',
        help="The interfaceo on which to listen for Advertisements")

    parser.add_argument(
        '--ip',
        help="The IP address to set as the destination address in "\
             "subscriptions")

    parser.add_argument(
       '--mac',
        help="The MAC address used as the MAC source address in answers")

    kwargs = vars(parser.parse_args())
    main(**kwargs)