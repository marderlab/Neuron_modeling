#!/usr/bin/python

from scipy import logspace
from math import log, log10, sqrt
import itertools
import sys
import json
if sys.version_info[0] == 3:
  import subprocess
  from io import StringIO
else:
  import commands as subprocess
  from cStringIO import StringIO
from joblib import Parallel, delayed
import tempfile
import os
import io  # to make logOut atomic
from robust_map import robust_map
import peelLength


###############################################################################
def system(commandStr):
  """
  Execute command string, returning output on success, or throwing error
  if the return value was not null
  """
  retVal, output = subprocess.getstatusoutput(commandStr)
  if retVal != 0:
    raise IOError('Error executing:' + commandStr + '\n' + output)
  return output


###############################################################################
def valsFromRange(propRange):
  if propRange[-1] == propRange[0]:
    return [propRange[0]]
  else:
    minVal, numSteps, maxVal = propRange
    return logspace(log10(minVal), log10(maxVal), numSteps)


###############################################################################
def makeParamsList(numSections, range_Ra, range_cm, range_g):
  vals_Ra = valsFromRange(range_Ra)
  vals_cm = valsFromRange(range_cm)
  vals_g = valsFromRange(range_g)
  membraneParams = list(itertools.product(vals_cm, vals_Ra, vals_Ra))
  gParams = list(itertools.product(vals_g, repeat=numSections))
  paramsList = [m + g for m in membraneParams for g in gParams]
  return paramsList


###############################################################################
def makePassiveProperties(parameters=None):
  if parameters is None:
    parameters = (1.0, 240.0, 240.0,
                  5e-5, 5e-7, 5e-5);

#      'matchTag' : 'Soma',  # Tagged by soma
  
  properties = [
    {
      'matchProp' : 'branchOrder', # this is ignored, leaving it for now
      'matchVal' : [0, 1],
      'name' : 'Soma',
      'values' : {
        'cm' : parameters[0],
        'Ra' : parameters[1],
      },
      'channels' : {
        'pas' : {
          'g' : parameters[3],
          'e' : 0.0
        }
      }
    },
    {
      'matchProp' : 'centripetalOrder', # less than two branches from edge
      'matchVal' : [0, 1],
      'name' : 'Tip',
      'values' : {
        'cm' : parameters[0],
        'Ra' : parameters[1],
      },
      'channels' : {
        'pas' : {
          'g' : parameters[4],
          'e' : 0.0
        }
      }
    },
    {
      'matchProp' : None,  # match the remainder
      'matchVal' : None,
      'name' : 'Middle',
      'values' : {
        'cm' : parameters[0],
        'Ra' : parameters[1],
      },
      'channels' : {
        'pas' : {
          'g' : parameters[5],
          'e' : 0.0
        }
      }
    }
  ]
  return properties


###############################################################################
def getExps(expOutput):
  taus, dVs = [], []
  expOutput = expOutput.split('\n')
  if len(expOutput) < 3:
    return taus, dVs, float('inf'), float('inf')
  for line in expOutput[:-2]:
    indTau1 = line.index('tau =') + len('tau =')
    indTau2 = line.index(' ms')
    indDv1 = line.index('dV =') + len('dV =')
    indDv2 = line.index(' mV')
    taus.append(float(line[indTau1:indTau2]))
    dVs.append(float(line[indDv1:indDv2]))
  line = expOutput[-2]
  i1 = line.index('delta v =') + len('delta v = ')
  i2 = line.index(' mV')
  unexplainedDV = float(line[i1:i2])
  line = expOutput[-1]
  i1 = line.index('voltage error =') + len('voltage error =')
  i2 = line.index(' mV')
  residual = float(line[i1:i2])
  return taus, dVs, unexplainedDV, residual


###############################################################################
def analyzeExpOutput(expModel, vUnexplained, vResid,
                     tauM=158.7, deltaTauM=96.4,
                     tau1=33.9, deltaTau1=17.0,
                     R0=2.3, deltaR0=1.7,
                     RIn=11.4, deltaRIn=6.0):
  #taus, dVs, unexplainedDV, residual = getExps(expOutput)
  try:
    fitTauM, fitR0 = expModel[0]
    fitTau1 = expModel[1][0]
    fitRIn = sum(modelExp[1] for modelExp in expModel) + vUnexplained
    
    """
    fitTauM = taus[0]
    fitR0 = dVs[0]
    fitTau1 = taus[1]
    fitRIn = sum(dVs) + unexplainedDV
    #fitErr = sqrt(  ((fitTauM - tauM) / deltaTauM)**2
    #              + ((fitTau1 - tau1) / deltaTau1)**2
    #              + ((fitR0 - R0) / deltaR0)**2
    #              + ((fitRIn - RIn) / deltaRIn)**2 )
    """
    fitErr = sqrt(  log(fitTauM / tauM)**2
                  + log(fitTau1 / tau1)**2
                  + log(fitR0 / R0)**2
                  + log(fitRIn / RIn)**2 )
  except IndexError:
    fitErr = float('inf')
  except ValueError:
    fitErr = float('inf')
  return fitErr


###############################################################################
def runParams(params, geoFile, logFile):
  from neuron_readExportedGeometry import HocGeometry
  from neuron_simulateGeometry import makeModel, simulateModel
  import peelLength
  print('Params: %s\n' % ', '.join('%.3g' % p for p in params))
  
  # make a geometry object
  geometry = HocGeometry(geoFile)
  
  # make properties list from parameters
  properties = makePassiveProperties(params)
  
  # make a passive model
  model = makeModel(geometry, properties)
  
  # simulate the model
  timeTrace, vTraces, textOutput = simulateModel(geometry, model)
  print(textOutput)
  
  # analyze output of model simulation
  expModel, vUnexplained, vResid = \
    peelLength.modelResponse(timeTrace, vTraces[geometry.soma.name],
                             verbose=False, findStepWindow=True,
                             plotFit=False, debugPlots=False,
                             displayModel=True)
  
  fitErr = analyzeExpOutput(expModel, vUnexplained, vResid)
  
  # print and return error/output
  print('Fit error = %.3g' % fitErr)
  return (fitErr, expModel, vUnexplained, vResid)


###############################################################################
def printBatchSimResult(label, params, result):
  print('%s: %s\n' % (label, ', '.join('%.3g' % p for p in params)))
  peelLength.printModel(result[1], vErr=result[2], vResid=result[3])
  
  
###############################################################################
def runBatchSimulate(geoFile, numSections=3, range_Ra=(60, 5, 480),
                     range_cm=(1.0,), range_g=(1e-7, 8, 1e-3),
                     logFile='batch_simulations.log',
                     numProcesses=0, useRobustMap=True):
  # get a list of the parameters for each passive model
  paramsList = makeParamsList(numSections, range_Ra, range_cm, range_g)
  if logFile is not None:
    if os.access(logFile, os.F_OK):
      print('Backing up previous log file')
      os.rename(logFile, logFile + '.bak')
    with io.open(logFile, 'wb') as fOut:
      fOut.write('Starting batch simulations.\n')
  
  if useRobustMap:
    resultsList = robust_map(runParams, paramsList, numProcesses=numProcesses,
                           args=(geoFile, logFile))
  else:
    if numProcesses <= 0:
      numProcesses -= 1
    # evaluate all the parameter sets in parallel
    resultsList = Parallel(n_jobs=numProcesses, verbose=10)(
      delayed(runParams)(params, geoFile, logFile) for params in paramsList
    )
  
  # get the index to the best parameter set
  bestInd = min(enumerate(resultsList), key=lambda x:x[1][0])[0]
  
  # print out the best result again
  if logFile is not None:
    with io.open(logFile, 'ab') as fOut:
      sys.stdout.flush
      stdout = sys.stdout ; sys.stdout = fOut
      for ind, (params, result) in enumerate(zip(paramsList, resultsList)):
        printBatchSimResult('Parameter set #%d' % ind, params, result)
      
      ind = bestInd ; params = paramsList[ind] ; result = resultsList[ind]
      printBatchSimResult('Best Parameter set (#%d)' % ind, params, result)
      sys.stdout.flush()
      sys.stdout = stdout

      ind = bestInd ; params = paramsList[ind] ; result = resultsList[ind]
      printBatchSimResult('Best Parameter set (#%d)' % ind, params, result)

  else:
    for ind, (params, result) in enumerate(zip(paramsList, resultsList)):
      printBatchSimResult('Parameter set #%d' % ind, params, result)
    
    ind = bestInd ; params = paramsList[ind] ; result = resultsList[ind]
    printBatchSimResult('Best Parameter set (#%d)' % ind, params, result)


###############################################################################
def _parseArguments():
  import argparse
  parser = argparse.ArgumentParser(description=
    "Run a batch of neuron simulations with different parameters,"
    + " and find the parameters that best match desired output.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("geoFile", help="file specifying neuron geometry")
  parser.add_argument("-np", "--numProcesses", default=-1, type=int,
       help="specify number of proceses to use. <= 0 indicates fewer than max")
  return parser.parse_args()


if __name__ == "__main__":
  options = _parseArguments()
  runBatchSimulate(options.geoFile, numProcesses=options.numProcesses)
