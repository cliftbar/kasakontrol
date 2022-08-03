#!/bin/sh

trap '' HUP

if [ "$2" = "on" ]; then
  echo "$2"
  nohup python -u $1.py > $1.log &
  echo $! > $1.pid
elif [ "$2" = "off" ]; then
  echo off
  kill -9 "$(cat $1.pid)"
  rm $1.pid
fi
