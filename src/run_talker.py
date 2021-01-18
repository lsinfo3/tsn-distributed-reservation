import argparse
import time
from reservation_interfaces.talker import Talker


def main(iface=None, ip=None, broadcast_ip=None, mac=None, timeout=None,
         stream_file=None, resends=None, load_test=None):
    talker = Talker(iface, ip, broadcast_ip, mac, timeout, resends)
    if load_test:
        talker.load_test(stream_file, load_test)
        time.sleep(1000)
    else:
        talker.advertise_streams_from_yaml(stream_file)
        time.sleep(5)
        print(f"Advertised: {len(talker.advertised_streams)}\nSubscribed:{len(talker.stream_subscriptions)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="An experimental implementation of a Time-Sensitive-Networking Talker.")

    parser.add_argument(
        '--iface',
        help="The interface from which to send the requests from")

    parser.add_argument(
        '--ip',
        help="Source IP address to put into advertisements")

    parser.add_argument(
        '--broadcast-ip',
        help="The Broadcast IPv4 address of the used subnet.")  

    parser.add_argument(
       '--mac',
        help="Source MAC address to put into advertisements")

    parser.add_argument(
        '--stream-file',
        help="Path to .yaml with stream specifications")

    parser.add_argument(
        '--timeout',
        type=int,
        help="The time in seconds until an advertisement is resent")

    parser.add_argument(
        '--resends',
        type=int,
        help="The number of times an advertisement would be resent",
        default=None)
    
    parser.add_argument(
        '--load-test',
        type=int,
        help="Use this to send n advertisements for random "
             "port-combinations of the given streams",
        required=False
    )

    kwargs = vars(parser.parse_args())
    main(**kwargs)
