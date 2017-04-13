#!/bin/bash

DEV="usb0"
IFB="ifb0"

# clean existing down- and uplink qdiscs, hide errors
echo "Clearing $DEV"
tc qdisc del dev $DEV root
tc qdisc del dev $DEV ingress
echo "Clearing $IFB"
tc qdisc del dev $IFB root
