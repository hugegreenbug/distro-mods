#!/bin/sh

# Original: https://gist.github.com/mbaez/9271180
# Modded by: Hugh Greenberg <hugegreenbug@gmail.com>

# sudo ./change-brightness.sh -3000 //reduce the brightness
# sudo ./change-brightness.sh 3000 //add brightness

if [ -z $1 ]; then
   echo "Missing brightness change"
   exit 1
fi

path=/sys/class/backlight/intel_backlight

MAX=`cat $path/max_brightness`
ACTUAL=`cat $path/actual_brightness`
NEW=`echo "$1 + $ACTUAL"|bc`
if [ $NEW -lt 0 ]; then
  NEW="0"
elif [ $NEW -gt $MAX ]; then
  NEW=$MAX
fi 

echo $NEW > $path/brightness
