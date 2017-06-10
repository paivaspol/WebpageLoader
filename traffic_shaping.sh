#!/bin/bash

# set -e

# The Ultimate Setup For Your Internet Connection At Home
# 
#
# Set the following values to somewhat less than your actual download
# and uplink speed. In kilobits
UPLINK=$1
DOWNLINK=$2
RTT=$3

# egress

# DEV="wlan0"
DEV="usb0"
IFB="ifb0"

# clean existing down- and uplink qdiscs, hide errors
echo "Clearing $DEV"
tc qdisc del dev $DEV root
tc qdisc del dev $DEV ingress
echo "Clearing $IFB"
tc qdisc del dev $IFB root

###### ingress
# create an interface for egress
ip link set dev ifb0 up

# install root HTB, point default traffic to 1:20:
tc qdisc add dev $DEV handle ffff: ingress
tc filter add dev $DEV parent ffff: protocol ip u32 \
  match u32 0 0 flowid 1:1 action mirred egress \
  redirect dev $IFB

echo "Setting egress for $DEV"
tc qdisc add dev $DEV root handle 1: htb default 20

# Shape uplink bandwidth.
tc class add dev $DEV parent 1: classid 1:1 htb rate ${UPLINK} ceil ${UPLINK}
tc class add dev $DEV parent 1:1 classid 1:20 htb rate ${UPLINK} ceil ${UPLINK}

echo "Setting latency egress for $DEV"
# Set the latency for the interface
tc qdisc add dev $DEV parent 1:20 handle 20: netem delay ${RTT}

########## egress #############
# Shaped the interface.
tc qdisc add dev $IFB root handle 1: htb default 15

tc class add dev $IFB parent 1: classid 1:1 htb rate ${DOWNLINK} ceil ${DOWNLINK}
tc class add dev $IFB parent 1:1 classid 1:15 \
  htb rate ${DOWNLINK} ceil ${DOWNLINK}

# Set the latency for the interface
tc qdisc add dev $IFB parent 1:15 handle 15: netem delay ${RTT}

# slow downloads down to somewhat less than the real speed  to prevent 
# queuing at our ISP. Tune to see how high you can set it.
# ISPs tend to have *huge* queues to make sure big downloads are fast
#
# attach ingress policer:

# tc qdisc add dev $DEV handle ffff: ingress
# 
# # filter *everything* to it (0.0.0.0/0), drop everything that's
# # coming in too fast:
# 
# tc filter add dev $DEV parent ffff: protocol ip u32 match ip src 0.0.0.0/0 police \
#   rate ${DOWNLINK} ceil ${DOWNLINK} drop flowid :1
