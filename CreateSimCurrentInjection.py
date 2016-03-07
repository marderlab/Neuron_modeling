#!/usr/bin/python3
import sys, math

def CalcCurrent(T, TCutOff):
  if T < TCutOff:
    Current = 0
  else:
    Freq = ((T + 500 - TCutOff) / 2000) / 1000;  # 1/ms
    Current = 0.3 * math.sin(2 * math.pi * Freq * (T - TCutOff))
  return Current

def GenerateInjection():
  dt = 0.1        #ms
  TStart = 0.0    #ms
  TCutOff = 5250.0 #ms
  TStop = TCutOff + 5000.0  - 250.0 #ms
  
  NumT = math.ceil(1 + (TStop - TStart) / dt)
  Time = [TStart + dt * n for n in range(NumT)] 
  Current = [CalcCurrent(T, TCutOff) for T in Time]
  return (Time, Current)

def OutputInjection(Time, Current):
  NumT = len(Time)
  print('%g' % NumT)
  for n in range(NumT):
    print('%.1f\t%.4f' % (Time[n], Current[n]))

if __name__ == "__main__":
  """Arguments = sys.argv
  Arguments.remove(Arguments[0])"""
  
  (Time, Current) = GenerateInjection()
  OutputInjection(Time, Current)
  sys.exit(0)

