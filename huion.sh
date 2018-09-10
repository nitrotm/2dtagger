#!/bin/sh

# extra 1 to 12
xinput set-button-map "HID 256c:006e Pad" 8 9 10 7 8 9 10 11 12 13 14 15 16 17 18 19

# extra 1 and 2
xinput set-button-map "HID 256c:006e Pen Pen (0)" 1 2 3 4 5 6 7

# set span on screen 2
xrestrict -d 21 -c 1 -X center -Y center
xrestrict -d 22 -c 1 -X center -Y center
