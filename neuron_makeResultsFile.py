#!/usr/bin/python


import os
import sys


names = []
values = []
with open('results.txt', 'r') as fIn:
  for line in fIn:
    splitLine = line.split()
    names.append(splitLine[0])
    values.append(splitLine[1])


fixName = sys.argv[1]
with open(fixName, 'r') as fIn:
  line = next(fIn)
  newValues = line.split()
newValues.insert(0, 'nan')


with open(fixName, 'w') as fOut:
  for (name, val) in zip(names, newValues):
    fOut.write('%s                  %s\n' % (name, val))
