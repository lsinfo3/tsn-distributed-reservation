# TSN Reservation Protocol

This repository contains the implementation of a minimalistic reservation protocol for real-time network streams in non-TSN networks.
Included are APIs for the talker- and listeners in such an environment, as well as a controller script that implements the protocol on an OpenFlow-supporting network switch (NEC PF5420).
Whereas the APIs are of a generic nature, the controller script is, in large parts, adapted to that particular switch's telnet control interface.

The foundation upon which this protocol has been created is the paper _Technical report on bridge-local guaranteed latency with strict priority scheduling_ by Grigorjew et al., which presents the theoretical model that allows for the deployment of real-time network streams without global knowledge of the network.

An evaluation of this protocol in a hardware testbed has been made with the talker-, listener- and controller software each running on a seperate Raspberry Pi 3B device.
The scripts used for generating measurements, their preprocessing and visualization are also included in this repository in the evaluation directory.
