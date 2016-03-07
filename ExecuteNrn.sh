#!/bin/bash
unset LD_LIBRARY_PATH
source $HOME/neuron/nrnenv
nice -15 nrniv -dll "/home/ted/neuron/Code/channels/x86_64/.libs/libnrnmech.so" -isatty -nobanner $1
