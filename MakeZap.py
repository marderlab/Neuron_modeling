#!/usr/bin/python3
usageStr = \
"""usage: MakeZAP.py fileName t dt maxF [amplitude]
     fileName should end in .atf
     times in seconds, frequencies in Hz"""



import sys, math



################################################################################
def calcDeltaPhase(t, duration, dt, f0, slope):
  tLeft = duration - t
  if t < tLeft:
    freq = f0 * math.exp(slope * t)
  else:
    freq = f0 * math.exp(slope * tLeft)
    
  deltaPhase = 2 * math.pi * freq * dt

  return deltaPhase



################################################################################
def generateInjection(duration, dt, numSamples, fMax, amp):
  f0 = 0.25 #Hz
  # the factor of two is because we have an increasing ramp followed
  #  by a decreasing ramp:
  slope = 2.0 * math.log(fMax / f0) / duration

  tStart = 0.0  #s
  t = [tStart + dt * n for n in range(numSamples)]
  deltaPhase = [calcDeltaPhase(t_n, duration, dt, f0, slope) for t_n in t]
  signal = []
  phase = 0
  for n in range(len(deltaPhase)):
    signal.append(amp * math.sin(phase))
    phase += deltaPhase[n]
  
  return signal



################################################################################
def bufferSignal(signal, dt, frontBuffer, numTotal):
  frontLen = int(round(frontBuffer / dt))
  backLen = numTotal - frontLen - len(signal)
  
  buffSig = [0] * frontLen + signal + [0] * backLen
  return buffSig



################################################################################
def outputSignal(signal, dt, fileName):
  with open(fileName, 'w') as fHandle:
    fHandle.write('ATF\t1.0\r\n')
    fHandle.write('0\t2\r\n')
    fHandle.write('"Time (s)"\t"Trace #1 (nA)"\r\n')
    t = 0.0
    for n in range(len(signal)):
      lineStr = '%.6f\t%.6f\r\n' % (t, signal[n])
      fHandle.write(lineStr)
      t = t + dt



################################################################################
def makeZap(duration, dt, fMax, amplitude, frontBuffer=1.0, backBuffer=1.0):
  numTotal = int(duration / dt)
  duration = duration - (frontBuffer + backBuffer)
  numSamples = int(duration / dt)
  signal = generateInjection(duration, dt, numSamples, fMax, amplitude)
  signal = bufferSignal(signal, dt, frontBuffer, numTotal)
  return signal



################################################################################
def _parseArguments():
  arguments = sys.argv
  if len(arguments) not in (5, 6):
    print(usageStr)
    raise TypeError('Incorrect number of arguments.')
  
  fileName = arguments[1]
  duration = float(arguments[2])
  dt = float(arguments[3])
  fMax = float(arguments[4])
  
  if len(arguments) < 6:
    amplitude = 1.0
  else:
    amplitude = float(arguments[5])
  
  return (fileName, duration, dt, fMax, amplitude)


  
################################################################################
if __name__ == "__main__":
  (fileName, duration, dt, fMax, amplitude) = _parseArguments()

  # make the signal
  signal = makeZap(duration, dt, fMax, amplitude)
  
  # output the signal
  outputSignal(signal, dt, fileName)

  sys.exit(0)
