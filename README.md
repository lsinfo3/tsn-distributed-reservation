# TSN Reservation Protocol

This repository contains the implementation of a minimalistic reservation protocol for real-time network streams in non-TSN networks.
Included are APIs for the talker- and listeners in such an environment, as well as a controller script that implements the protocol on an OpenFlow-supporting network switch (NEC PF5420).
Whereas the APIs are of a generic nature, the controller script is, in large parts, adapted to that particular switch's telnet control interface.

An evaluation of this protocol in a hardware testbed has been made with the talker-, listener- and controller software each running on a seperate Raspberry Pi 3B device.
The scripts used for generating measurements, their preprocessing and visualization are also included in this repository in the evaluation directory.

## Requirements

+ `PyYAML` for parsing the talker configuration file
+ `ryu` framework used to interface with the OpenFlow switch
+ `scapy` used for implementing the custom data plane protocol

## Usage

__Talker__

```
python src/run_talker.py [-h] [--iface IFACE] [--ip IP]
                         [--broadcast-ip BROADCAST_IP] [--mac MAC]
                         [--stream-file STREAM_FILE] [--timeout TIMEOUT]
                         [--resends RESENDS] [--load-test LOAD_TEST]

optional arguments:
  --iface IFACE         The interface from which to send the requests from
  --ip IP               Source IP address to put into advertisements
  --broadcast-ip BROADCAST_IP
                        The Broadcast IPv4 address of the used subnet.
  --mac MAC             Source MAC address to put into advertisements
  --stream-file STREAM_FILE
                        Path to .yaml with stream specifications
  --timeout TIMEOUT     The time in seconds until an advertisement is resent
  --resends RESENDS     The number of times an advertisement would be resent
  --load-test LOAD_TEST
                        Use this to send n advertisements for random port-
                        combinations of the given streams
```

__Listener__

```
python src/run_listener.py [--iface IFACE] [--ip IP] [--mac MAC]

optional arguments:
  --iface IFACE  The interfaceo on which to listen for Advertisements
  --ip IP        The IP address to set as the destination address in
                 subscriptions
  --mac MAC      The MAC address used as the MAC source address in answers
```

__SDN-Controller__


```
ryu-manager src/controller.py
```

# Authors

* Alexej Grigorjew - alexej.grigorjew@uni-wuerzburg.de
* Christian Baier - christian.baier@stud-mail.uni-wuerzburg.de
* Florian Metzger - florian.metzger@uni-wuerzburg.de
* Tobias Hoßfeld - tobias.hossfeld@uni-wuerzburg.de

This work is based on the distributed latency model from _Bounded Latency with Bridge-Local Stream Reservation and Strict Priority Queuing_ by Grigorjew et al., published on the _11th International Conference on Network of the Future (NoF) (2020)_.

It has been implemented and applied later in the paper:

*_Distributed Implementation of Deterministic Networking in Existing Non-TSN Ethernet Switches_, Workshop on Time-sensitive and Deterministic Networking of the ICC 2021*.

When referring to this work, please cite this paper.
