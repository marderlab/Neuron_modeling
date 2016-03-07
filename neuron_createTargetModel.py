#!/usr/bin/python3



_usageStr=\
"""usage: neuron_createTargetModel.py geoFile paramFile modelName [tolerance]
         Creates a synthetic data set to use for testing of fitting.
         noise is added, as specified in simInfo.vNoiseAmp"""



import sys, os, math
if sys.version_info[0] == 3:
  import subprocess
else:
  # prepare for migration to python 3
  import commands as subprocess

import neuron_createModelHocFile, neuron_simulate, MakeZap



###############################################################################
class SimInfo:
  def __init__(self, geoFile, paramFile, modelName, tol=None, noiseAmp=None):
    self.dt               = 0.1      # ms
    self.tStart           = 0.0      # ms
    self.tSettle          = 7000.0   # ms
    self.tWaitAfterSettle = 2000.0   # ms
    self.tStopBeforeEnd   = 2000.0   # ms
    self.tDuration        = 10000.0  # ms
    self.tol              = tol

    self.populationSize   = 10000

    self.injectionType    = 'Noise'
    #self.injectionType    = 'Zap'
    # nosiePower:  0 for white, -1 for pink, -2 for red
    self.noisePower       = -2.0          
    self.maxFreq          = 40.0     # Hz
    self.amplitude        = 4.0      # rms nA
    self.noiseBias        = 0.0      # nA
    if noiseAmp == None:
      self.vNoiseAmp      = 0.05     # rms mV
    else:
      self.vNoiseAmp      = noiseAmp;
        
    self.geoFile          = geoFile
    self.paramFile        = paramFile
    self.modelName        = modelName

    self.dataFile         = modelName + '.txt'
    self.simDataFile      = 'Sim' + modelName + '.txt'
    self.hocFile          = modelName + '.hoc'
    self.simHocFile       = 'Simulate' + modelName + '.hoc'
  
    self.startupFile      = 'startup.txt'
    self.outputFile       = '/dev/null'
    self.resumeFile       = 'resume.txt'
    


###############################################################################
def calcCurrent(t, simInfo, tInject, freqStart):
  if t < tInject:
    current = 0
  else:
    # the 0.001 is to convert from Hz to 1/ms
    freq = 0.001 * freqStart * math.pow(simInfo.maxFreq/freqStart, \
                                      (t - Inject) / simInfo.tDuration)
    current = 0.3 * math.sin(2 * math.pi * freq * (t - tCutoff))
  return current



###############################################################################
def generateInjectionWaves(simInfo):
  tStop = simInfo.tSettle + simInfo.tDuration
  numT = math.ceil(1 + (tStop - simInfo.tStart) / simInfo.dt)
  dt_times_fMax = 0.001 * simInfo.dt * simInfo.maxFreq;
  time = [simInfo.tStart + simInfo.dt * n for n in range(numT)]
  tInject = simInfo.tSettle + simInfo.tWaitAfterSettle
  freqStart = 1000 / simInfo.tDuration
  current = [calcCurrent(t, simInfo, tInject, freqStart) for t in time]

  return (time, current)



###############################################################################
def generateInjectionZap(simInfo):
  tStop = simInfo.tSettle + simInfo.tDuration
  numT = math.ceil(1 + (tStop - simInfo.tStart) / simInfo.dt)
  time = [simInfo.tStart + simInfo.dt * n for n in range(numT)]

  dt = 1.0e-3 * simInfo.dt
  duration = numT * dt
  fMax = simInfo.maxFreq
  amplitude = simInfo.amplitude
  frontBuffer = 1.0e-3 * (simInfo.tWaitAfterSettle + simInfo.tSettle)
  backBuffer = 2 # s
  current = \
    MakeZap.makeZap(duration, dt, fMax, amplitude, frontBuffer, backBuffer)
  return (time, current)



###############################################################################
def generateInjectionNoise(simInfo):
  tStop = simInfo.tSettle + simInfo.tDuration
  numT = math.ceil(1 + (tStop - simInfo.tStart) / simInfo.dt)
  dt_times_fMax = 0.001 * simInfo.dt * simInfo.maxFreq;
  time = [simInfo.tStart + simInfo.dt * n for n in range(numT)]

  numQuietBefore = \
    math.ceil(1 + (simInfo.tSettle + simInfo.tWaitAfterSettle) / simInfo.dt);
  numQuietAfter = math.ceil(simInfo.tStopBeforeEnd / simInfo.dt);
  numNoise = numT - numQuietBefore - numQuietAfter;

  # first have interval with no current injection
  current = [0] * numQuietBefore;

  # next inject noise
  noiseCmd = '/home/ted/python/noise/Noise.py %g %d %g %g' % \
    (simInfo.amplitude, numNoise, dt_times_fMax, simInfo.noisePower)
  output = subprocess.getstatusoutput(noiseCmd)
  current = current + [x + simInfo.noiseBias for x in eval(output[1])]

  # end with brief period with no injection
  current = current + [0] * numQuietAfter

  return (time, current)



###############################################################################
def generateInjection(simInfo):
  if simInfo.injectionType == 'None':
    # WTF?
    return generateInjectionWaves(simInfo)
  elif simInfo.injectionType == 'Zap':
    return generateInjectionZap(simInfo)
  else:
    return generateInjectionNoise(simInfo)



###############################################################################
def outputInjection(fileName, time, current):
  with open(fileName, 'w') as fOut:
    numT = len(time)
    fOut.write('%d\n' % numT)
    for n in range(numT):
      fOut.write('%10.2f %8.4f %3.1f\n' % (time[n], current[n], 0))



###############################################################################
def writeFakeStartup(simInfo):
  with open(simInfo.startupFile, 'w') as fOut:
    fOut.write('DataFile    %s\n' % simInfo.dataFile)
    fOut.write('GeoFile     %s\n' % simInfo.geoFile)
    fOut.write('OutputFile  %s\n' % simInfo.outputFile)
    fOut.write('ResumeFile  %s\n' % simInfo.resumeFile)



###############################################################################
def getVNoise(numSamples, simInfo):
  if float(simInfo.vNoiseAmp) <= 0.0:
    # make noiseless "noise"
    return [0.0] * numSamples
  else:
    # make white noise
    output = subprocess.getstatusoutput( \
      '/home/ted/python/noise/Noise.py %s %d' % (simInfo.vNoiseAmp,numSamples))
    return eval(output[1])



###############################################################################
def finalize(simInfo):
  # get full data trace from simulation
  with open(simInfo.simDataFile, 'r') as fIn:
    numData = int(next(fIn))
    t = next(fIn).split(None)
    i = next(fIn).split(None)
    v = next(fIn).split(None)

  # remove the simulation data file
  #os.remove(simInfo.simDataFile)

  # calculate index of time to settle
  tFloat = [float(x) for x in t]
  ind0 = tFloat.index(simInfo.tSettle)
  # length of truncated data, remaining after settle time
  numTrunc = numData - ind0

  # get noise trace to add to voltage
  vNoise = getVNoise(numTrunc, simInfo)

  # write truncated data trace with noise added to voltage
  with open(simInfo.dataFile, 'w') as fOut:
    fOut.write(str(numTrunc) + '\n')
    for n in range(ind0, numData):
      v[n] = float(v[n]) + vNoise[n - ind0];
      fOut.write('%s  %s  %g\n' % (t[n], i[n], v[n]))



###############################################################################
def writeRealStartup(simInfo, sectionNames):
  paramNames = []
  paramVals = []
  
  (paramNames, paramVals) = neuron_simulate.getParameters(simInfo.paramFile)

  fOut = open(simInfo.startupFile, 'w')
  homeDir = os.path.expanduser('~')
  basePath = os.getcwd().replace(homeDir, '~')
  fOut.write('DataFile    %s\n' % os.path.join(basePath, simInfo.dataFile))
  fOut.write('GeoFile     %s\n' % os.path.join(basePath, simInfo.geoFile))
  fOut.write('OutputFile  %s\n' % simInfo.outputFile)
  fOut.write('ResumeFile  %s\n' % os.path.join(basePath, simInfo.resumeFile))

  fOut.write('\nPopulationSize  %d\n' % simInfo.populationSize)

  fOut.write('\nParameters:\n')
  fOut.write('#Global Properties:\n')
  stageNum = 0
  numSections = len(sectionNames)
  for n in range(len(paramNames)):
    name = paramNames[n]
      
    if stageNum == numSections:
      if sectionNames[-1] not in name:
        fOut.write('\n#Channel Shifts:\n')
        stageNum = stageNum + 1
    elif stageNum < numSections:
      if sectionNames[stageNum] in name:
        fOut.write('\n#%s Properties:\n' % sectionNames[stageNum])
        stageNum = stageNum + 1

    if stageNum == 0:
      if name.startswith('C_Specific') or name.startswith('R_Intracellular'):
        valLow = str(float(paramVals[n]) * 0.1)
        valHigh = str(float(paramVals[n]) * 10.0)
      else:
        valLow = paramVals[n]
        valHigh = valLow
    elif stageNum == (numSections + 1):
      if 'Shift' in name:
        valLow = str(float(paramVals[n]) - 5.0)
        valHigh = str(float(paramVals[n]) + 5.0)
      else:
        valLow = str(float(paramVals[n]) * 0.67)
        valHigh = str(float(paramVals[n]) * 1.50)
    else:
      if 'Bar' in name:
        valLow = str(float(paramVals[n]) * 0.01)
        valHigh = str(float(paramVals[n]) * 100.0)
      elif '_Fact_' in name:
        valLow = paramVals[n]
        valHigh = paramVals[n]
      else:
        valLow = str(float(paramVals[n]) - 20.0)
        valHigh = str(float(paramVals[n]) + 20.0)

    if len(name) < 8:
      name = name + ' ' * (8 - len(name))
    fOut.write('%s\t%s\t%s\n' % (name, valLow, valHigh))

  fOut.close()



###############################################################################
def createTargetModel(geoFile, paramFile, modelName, noiseAmp=None, \
                      tol=None, integralStep=None, useCVOde=True):
  simInfo = SimInfo(geoFile, paramFile, modelName, tol, noiseAmp)

  #write currentFile
  (time, current) = generateInjection(simInfo)
  outputInjection(simInfo.dataFile, time, current)

  #write crappy "fake" startup file to get started
  writeFakeStartup(simInfo)

  #create the target model hoc file
  os.system('rm -f %s*' % simInfo.resumeFile)
  os.system('cp %s %s_param.txt' % (paramFile, simInfo.resumeFile))
  (sectionList, modelName) = \
    neuron_createModelHocFile.createModelHocFile(simInfo.startupFile)

  #simulate the target model
  neuron_simulate.simulateNeuron(simInfo.startupFile, sectionList, modelName,
                                 tol=tol, integralStep=integralStep, \
                                 useCVOde=useCVOde)

  # remove the hoc files
  os.remove(simInfo.hocFile)
  os.remove(simInfo.simHocFile)

  # truncate first tSettle ms of data, add noise, and clean-up:
  finalize(simInfo)

  #write a "real" startup file to prepare for fits
  sectionNames = [section.name for section in sectionList]
  writeRealStartup(simInfo, sectionNames)



###############################################################################
def _parseArguments():
  arguments = sys.argv
  if len(arguments) not in (4, 5):
    print(_usageStr)
    if len(arguments) > 1:
      raise TypeError('Incorrect number of arguments.')
    sys.exit(0)

  geoFile = arguments[1]
  paramFile = arguments[2]
  modelName = arguments[3]
  if len(arguments) == 4:
    tol = None
  else:
    tol = float(arguments[4])
  return (geoFile, paramFile, modelName, tol)



###############################################################################
if __name__ == "__main__":
  (geoFile, paramFile, modelName, tol) = _parseArguments()

  createTargetModel(geoFile, paramFile, modelName, tol=tol)
  
  os.system('beep -l 50 -f 200')
  sys.exit(0)
