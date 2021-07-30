# The class for parsing, formatting, and writing data from the ThisInThatCounter
from _typeshed import NoneType
from benbiohelpers.CountThisInThat.InputDataStructures import EncompassedData, EncompassingData
from benbiohelpers.CountThisInThat.OutputDataStratifiers import *
from typing import List, Type, Union
import subprocess


class CounterOutputDataHandler:
    """
    This class receives information on which encompassed features are within which encompassing features and determines how to
    record their data for the final output form.
    This class also handles data writing.
    *Places sticky note on back: "Inherit from me"*
    """

    def __init__(self):
        """
        Initialize the object by setting default values 
        """

        # Set tracking options to False by default.
        self.trackAllEncompassing = False
        self.trackNonCountedEncompassed = False
        self.trackSupInfoUntilExit = False

        self.outputDataStratifiers: List[OutputDataStratifier] = list() # The ODS's used to stratify the data.

        # Placeholders for the features being examined at a given time.
        self.encompassedFeature = None
        self.encompassingFeature = None

        # Set up the most basic output data structre: If the feature is encompassed, include it!
        self.outputDataStructure = 0


    def getNewStratificationLevelDictionaries(self):
        """
        Creates and returns all dictionaries at the object's stratification level in the ODS
        """

        if len(self.outputDataStratifiers) == 0: self.outputDataStructure = dict()
        dictionariesToReturn = [self.outputDataStructure,]
        for _ in range(len(self.outputDataStratifiers)):
            tempDictionariesToReturn = list()
            for dictionary in dictionariesToReturn:
                for key in dictionary:
                    dictionary[key] = dict()
                    tempDictionariesToReturn.append(dictionary[key])
            dictionariesToReturn = tempDictionariesToReturn

        return dictionariesToReturn


    def addNewStratifier(self, stratifier: OutputDataStratifier):
        """
        Adds a new stratifier, assigning it as the child stratifier to the last stratifier added, if necessary.
        """
        self.outputDataStratifiers.append(stratifier)
        if len(self.outputDataStratifiers) > 1: self.outputDataStratifiers[-2].childDataStratifier = stratifier

    
    def addStrandComparisonStratifier(self, strandAmbiguityHandling = AmbiguityHandling.record, outputName = "Strand_Comparison"):
        """
        Adds a layer onto the output data structure to stratify by whether or not the strands of the encompassed and encompassing features match.
        """
        self.addNewStratifier(StrandComparisonODS(strandAmbiguityHandling, self.getNewStratificationLevelDictionaries(), outputName))


    def addRelativePositionStratifier(self, encompassingFeature: EncompassingData, centerRelativePos = True, 
                                      extraRangeRadius = 0, outputName = "Relative_Pos", positionAmbiguityHandling = AmbiguityHandling.tolerate):
        """
        Adds a layer onto the output data structure to stratify by the position of the encompassed data with the encompassing data.
        """
        self.addNewStratifier(RelativePosODS(positionAmbiguityHandling, self.getNewStratificationLevelDictionaries(),
                                                         encompassingFeature, centerRelativePos, extraRangeRadius, outputName))


    def addEncompassingFeatureStratifier(self, ambiguityHandling = AmbiguityHandling.tolerate, 
                                         outputName = "Encompassing_Feature", trackAllEncompassing = True):
        """
        Adds a layer onto the output data structure to stratify by encompassing features.
        """
        self.trackAllEncompassing = trackAllEncompassing
        self.addNewStratifier(EncompassingFeatureODS(ambiguityHandling, self.getNewStratificationLevelDictionaries(), outputName))


    def addEncompassedFeatureStratifier(self, outputName = "Encompassed_Feature", trackNonCountedEncompassed = True):
        """
        Adds a layer onto the output data structure to stratify by encompassed features.
        """
        self.trackNonCountedEncompassed = trackNonCountedEncompassed
        self.addNewStratifier(EncompassedFeatureODS(self.getNewStratificationLevelDictionaries(), outputName))


    def addEncompassedFeatureContextStratifier(self, contextSize, includeAlteredTo, outputName = "Context"):
        """
        Adds a layer onto the output data structure to stratify by the surrounding nucleotide context of the encompassed feature.
        """
        self.addNewStratifier(EncompassedFeatureContextODS(self.getNewStratificationLevelDictionaries(), outputName, contextSize, includeAlteredTo))


    def addPlaceholderStratifier(self, ambiguityHandling = AmbiguityHandling.tolerate, outputName = None):
        """
        Adds a layer onto the output data structure to make sure that the last data column just contains raw counts.
        Only change ambiguity handling if you want to ensure that all encompassed features are only counted once.  (Change to "record")
        """
        self.addNewStratifier(PlaceholderODS(self.getNewStratificationLevelDictionaries(), ambiguityHandling, outputName))


    def addSupplementalInformationHandler(self, supplementalInfoClass: Type[SupplementalInformationHandler], 
                                          stratificationLevel, outputName = None):
        """
        Adds the specified supplemental information handler to the given stratification level.
        Keep in mind that SIH's cannot be added to the bottom level stratifier, as they store information in the specified
        level's child stratifier.
        If outputName is set to None, the default output name is used.
        """
        self.trackSupInfoUntilExit = True
        if outputName is None:
            self.outputDataStratifiers[stratificationLevel].addSuplementalInfo(supplementalInfoClass())
        else:
            self.outputDataStratifiers[stratificationLevel].addSuplementalInfo(supplementalInfoClass(outputName))


    def prepareToWriteIncrementalBed(self, outputFilepath, ODSSubs = None):
        """
        Prepare the class to output data with each finished encompassed/encompassing feature instead of
        all at once at the end.  (Should be more memory efficient)
        Also, this method preserves bed formatting for those features.

        ODSSubs is used to susbstitute information from the output data structures into the original data line.
        If ODSSubs is None, all data is simply appended to the line.  Otherwise, it should be a list with
        as many items as are outputted by the ODS (minus the first encompassed/encompassing feature ODS).  Each
        item in the list should be a number representing the column to substitute.
        """

        assert isinstance(self.outputDataStratifiers[0], (EncompassedFeatureODS, EncompassingFeatureODS)), (
            "Cannot write incremental bed file unless leading ODS is encompassed/encompassing feature ODS."
        )

        self.ODSSubs: List = ODSSubs
        self.outputFile = open(outputFilepath, 'w')


    def updateFeatureData(self):
        """
        Updates all relevant values in each ODS using the current encompassed and encompassing features.
        """
        for outputDataStratifier in self.outputDataStratifiers: 
            outputDataStratifier.updateConfirmedEncompassedFeature(self.encompassedFeature, self.encompassingFeature)


    def onNonCountedEncompassedFeature(self, encompassedFeature: EncompassedData):
        """
        If the Output Data Handler is set up to track non-counted encompassed data, do it here.
        """

        if self.trackNonCountedEncompassed:
            for outputDataStratifier in self.outputDataStratifiers: 
                outputDataStratifier.onNonCountedEncompassedFeature(encompassedFeature)


    def onNewEncompassingFeature(self, encompassingFeature: EncompassingData):
        """
        If the Output Data Handler is set up to track all encompassing data, do it here.
        """

        if self.trackAllEncompassing:
            for outputDataStratifier in self.outputDataStratifiers: 
                outputDataStratifier.onNewEncompassingFeature(encompassingFeature)


    def updateODS(self, count):
        """
        If count is true, increments the proper object in the output data structure.
        Otherwise, just updates supplemental information.
        """

        # Account for the base case where we are just counting all features.
        if len(self.outputDataStratifiers) == 0: 
            if count: self.outputDataStructure += 1
            return

        # Drill down through the ODS's using the relevant keys from this encompassed feature to determine where to count.
        currentODSDict = self.outputDataStructure
        for outputDataStratifier in self.outputDataStratifiers[:-1]:
            currentODSDict = currentODSDict[outputDataStratifier.getRelevantKey(self.encompassedFeature)]
            for i, supplementalInfoHandler in enumerate(outputDataStratifier.supplementalInfoHandlers):
                currentODSDict[SUP_INFO_KEY][i] = supplementalInfoHandler.updateSupplementalInfo(currentODSDict[SUP_INFO_KEY][i], 
                                                                                                 self.encompassedFeature, self.encompassingFeature)
        if count: currentODSDict[self.outputDataStratifiers[-1].getRelevantKey(self.encompassedFeature)] += 1


    def checkFeatureStatus(self, exitingEncompassment):
        """
        Determines whether or not the current encompassed feature should be counted based on ambiguity handling and whether or not it is exiting encompassment.
        Also determines whether or not the feature has a chance of being counted in the feature (whether or not it should still be tracked.)
        The function returns these two values as a tuple.  (countNow first, followed by continueTracking)
        """

        # Account for the base case of just counting everything.
        if len(self.outputDataStratifiers) == 0: return (not exitingEncompassment, not exitingEncompassment)

        # Traverse the list of output data stratifiers checking for states that invalidate counting of this feature.
        nontolerantAmbiguityHandling = False
        waitingOnAmbiguityChecks = False
        for oDS in self.outputDataStratifiers:
            if oDS.ambiguityHandling == AmbiguityHandling.tolerate: 
                pass
            else:
                nontolerantAmbiguityHandling = True
                if oDS.ambiguityHandling == AmbiguityHandling.record:
                    if oDS.getRelevantKey(self.encompassedFeature) is not None: waitingOnAmbiguityChecks = True
                else:
                    if oDS.getRelevantKey(self.encompassedFeature) is None: 
                        # There is an ODS that ignores ambiguity, and its key is ambiguous.  Don't count,
                        # and stop tracking unless we are still tracking supplemental information
                        return (False, (self.trackSupInfoUntilExit and not exitingEncompassment)) 
                    else: waitingOnAmbiguityChecks = True

        # Is there any nontolerant ambiguity handling in this data structure? If so, do we have enough information to count it now?
        if nontolerantAmbiguityHandling:
            if not waitingOnAmbiguityChecks and (not self.trackSupInfoUntilExit or exitingEncompassment): return (True, False)
            else: return (False, True)

        # If all ambiguity handling is tolerant and we are not exiting encompassment, count and continue tracking.
        elif not exitingEncompassment: return (True, True)

        # Otherwise, if we ARE exiting encompassment, don't count and stop tracking.
        else: return (False, False)


    def onEncompassedFeatureInEncompassingFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData, exitingEncompassment):
        """
        Handles the case where an encompassed feature is within an encompassing feature.
        Returns true or false based on whether or not the feature should be tracked in the future based on ambiguity handling and stuff.
        If exitingEncompassment is true, the object has been seen previously but is now GUARANTEED to not be encompassed in the future.
        Otherwise, the object MAY be seen again before it exits encompassment.
        """

        # Store the given features within this object.
        self.encompassedFeature = encompassedFeature
        self.encompassingFeature = encompassingFeature

        # First, update the encompassed feature based on the given encompassing feature unless it is exiting encompassment.
        if not exitingEncompassment: self.updateFeatureData()

        # Next, figure out whether or not the object should be counted, and whether or not it still needs to be tracked.
        countFeature, continueTracking = self.checkFeatureStatus(exitingEncompassment)
        if countFeature or self.trackSupInfoUntilExit: self.updateODS(countFeature)

        # If we're no longer tracking and the feature wasn't just counted, determine if the feature was EVER counted. If not, pass it to onNonCountedEncompassedFeature().
        # If this feature made it all the way to encompassment exiting, it WAS counted, either as the end condition of nontolerant ambiguity handling
        # or previously due to it being fully tolerant ambiguity handling.
        if not countFeature and not continueTracking and not exitingEncompassment: self.onNonCountedEncompassedFeature(encompassedFeature)

        return continueTracking


    class OutputDataWriter():

        def __init__(self, outputDataStructure, outputDataStratifiers, outputFilePath) -> None:

            self.outputDataStructure = outputDataStructure
            self.outputDataStratifiers: List[OutputDataStratifier] = outputDataStratifiers
            self.outputFilePath = outputFilePath
            self.outputFile = open(outputFilePath, 'w')

            self.ODSSubs: List = None
            self.customStratifyingNames = None
            self.currentDataRow = None
            self.previousKeys = None
            
            self.headers = self.getHeaders()

        def getCountDerivatives(self, previousKeys, getHeaders = False) -> List[str]:
            """
            Gets additional counts that are not explicitly defined within the output data structure.
            For example, the counts for both strands combined or both strands combined and aligned during dyad position counting.
            if getHeaders is true, the headers for the new data columns are returned instead.
            All return types should be lists of strings so they can be directly written to the output file using join.
            Also, MAKE SURE that the returned list, whether getHeaders is true or false, is always the SAME LENGTH.
            Should be overridden in children class, as the base functionality just returns empty lists.
            """
            return list()


        def getHeaders(self):

            headers = list()
            if len(self.outputDataStratifiers) > 1:
                for outputDataStratifier in self.outputDataStratifiers[:-1]:
                    headers.append(outputDataStratifier.outputName)
                    for supplementalInfoHandler in outputDataStratifier.supplementalInfoHandlers:
                        headers.append(supplementalInfoHandler.outputName)
            for key in self.outputDataStratifiers[-1].getKeysForOutput():
                headers.append(self.getOutputName(-1, key))

            headers += self.getCountDerivatives(None, getHeaders = True)


        def setDataCol(self, dataRow, dataCol, value):
            if self.ODSSubs is None:
                dataRow[dataCol] = value
            if self.ODSSubs[dataCol] is None:
                dataRow[self.ODSSubs[:dataCol].count(None)] = value
            else: dataRow[1][self.ODSSubs[dataCol]] = value


        def getOutputName(self,stratificationLevel, key):
            """
            A convenience function for getting output names from keys based on the customStratifyingNames parameter.
            """

            if (self.customStratifyingNames is None 
                or self.customStratifyingNames[stratificationLevel] is None 
                or key not in self.customStratifyingNames[stratificationLevel]):
                return self.outputDataStratifiers[stratificationLevel].formatKeyForOutput(key)
            else: return self.customStratifyingNames[stratificationLevel][key]

        def writeDataRows(self, currentDataObject, stratificationLevel, supplementalInfoCount):

            # If we're not at the final level of the data structure, iterate through it, recursively calling this function on the results.
            if stratificationLevel + 1 != len(self.outputDataStratifiers):
                for key in self.outputDataStratifiers[stratificationLevel].getKeysForOutput():

                    self.setDataCol(self.currentDataRow, stratificationLevel + supplementalInfoCount, 
                                    self.getOutputName(stratificationLevel, key))
                    self.previousKeys[stratificationLevel] = key

                    supplementalInfoHandlers = self.outputDataStratifiers[stratificationLevel].supplementalInfoHandlers
                    for i, supplementalInfoHandler in enumerate(supplementalInfoHandlers):
                        supplementalInfo = supplementalInfoHandler.getFormattedOutput(currentDataObject[key][SUP_INFO_KEY][i])
                        self.setDataCol(self.currentDataRow, stratificationLevel + supplementalInfoCount + i + 1, supplementalInfo)

                    self.writeDataRows(self.currentDataRow, currentDataObject[key], stratificationLevel + 1, 
                                          supplementalInfoCount + len(supplementalInfoHandlers))
            
            # Otherwise, add the entries in this dictionary (which should be integers representing counts) to the data row 
            # along with any count derivatives and write the row.
            else:
                for i, key in enumerate(self.outputDataStratifiers[stratificationLevel].getKeysForOutput()):
                    self.setDataCol(self.currentDataRow, stratificationLevel + supplementalInfoCount + i, str(currentDataObject[key]))
                self.currentDataRow[stratificationLevel + supplementalInfoCount + i + 1:] = self.getCountDerivatives(self.previousKeys)
                if isinstance(self.currentDataRow[0],list):
                    self.outputFile.write('\t'.join(('\t'.join(self.currentDataRow[0]), self.currentDataRow[1:])) + '\n')
                else:self.outputFile.write('\t'.join(self.currentDataRow) + '\n')


        def writeFeature(self, featureToWrite: Union[EncompassingData, EncompassedData]):
            """
            Writes individual features as they cease to be tracked.
            """

            # Prepare the data row based on the number of headers.
            self.currentDataRow = [featureToWrite.choppedUpLine.copy()]
            if self.ODSSubs is None: self.currentDataRow += [None] * (len(self.headers) - 1)
            else: self.currentDataRow += [None] * (self.ODSSubs.count(None) - 1)

            self.writeDataRows(self.outputDataStructure[featureToWrite], 1, 0)


        def finishIncrementalWriting(self, outputFilePath):
            """
            Sorts the results of individual feature writing, as features are not guaranteed to be written in the same order
            as the input files.
            """
            subprocess.run(("sort","-k1,1","-k2,2n",outputFilePath,"-o",outputFilePath), check = True)
            self.outputFile.close()


        def writeResults(self, outputFilePath, customStratifyingNames = None):
            """
            Writes the results of the output data structure to a given file.
            The customStratifyingNames variable, if supplied, should contain a list of dictionaries to convert keys to the desired string output.
            If not none, the list should have as many entries as layers in the output data structure, but any given entry can be "None" to indicate
            that naming should just use the keys using the basic formatting.
            """

            with open(outputFilePath, 'w') as outputFile:

                # Did we receive a valid customStratifyingNames parameter?
                assert customStratifyingNames is None or len(customStratifyingNames) == len(self.outputDataStratifiers), (
                    "Custom stratifying names given, but there is not exactly one entry for each ODS.")

                # Account for the base case of just counting everything.
                if len(self.outputDataStratifiers) == 0: outputFile.write(str(self.outputDataStructure) + '\n')

                else:

                    # First, write the headers based on the keys of the last data structure and the output names of any others,
                    # as well as any "count derivatives" defined in children class (See getCountDerivatives method).
                    headers = list()
                    if len(self.outputDataStratifiers) > 1:
                        for outputDataStratifier in self.outputDataStratifiers[:-1]:
                            headers.append(outputDataStratifier.outputName)
                            for supplementalInfoHandler in outputDataStratifier.supplementalInfoHandlers:
                                headers.append(supplementalInfoHandler.outputName)
                    for key in self.outputDataStratifiers[-1].getKeysForOutput():
                        headers.append(getOutputName(-1, key))

                    headers += self.getCountDerivatives(None, getHeaders = True)

                    outputFile.write('\t'.join(headers) + '\n')

                    # Next, write the rest of the data using a recursive function for writing rows of data from 
                    # an output data structure of an unknown number of stratifiacion levels.
                    currentDataRow = [None]*(len(headers))
                    previousKeys = [None]*(len(self.outputDataStratifiers) - 1)
                    def addDataRow(currentDataObject, stratificationLevel, supplementalInfoCount):

                        # If we're not at the final level of the data structure, iterate through it, recursively calling this function on the results.
                        if stratificationLevel + 1 != len(self.outputDataStratifiers):
                            for key in self.outputDataStratifiers[stratificationLevel].getKeysForOutput():

                                currentDataRow[stratificationLevel + supplementalInfoCount] = getOutputName(stratificationLevel, key)
                                previousKeys[stratificationLevel] = key

                                supplementalInfoHandlers = self.outputDataStratifiers[stratificationLevel].supplementalInfoHandlers
                                for i, supplementalInfoHandler in enumerate(supplementalInfoHandlers):
                                    supplementalInfo = supplementalInfoHandler.getFormattedOutput(currentDataObject[key][SUP_INFO_KEY][i])
                                    currentDataRow[stratificationLevel + supplementalInfoCount + i + 1] = supplementalInfo

                                addDataRow(currentDataObject[key],stratificationLevel + 1, 
                                        supplementalInfoCount + len(supplementalInfoHandlers))
                        
                        # Otherwise, add the entries in this dictionary (which should be integers representing counts) to the data row 
                        # along with any count derivatives and write the row.
                        else:
                            for i, key in enumerate(self.outputDataStratifiers[stratificationLevel].getKeysForOutput()):
                                currentDataRow[stratificationLevel + supplementalInfoCount + i] = str(currentDataObject[key])
                            currentDataRow[stratificationLevel + supplementalInfoCount + i + 1:] = self.getCountDerivatives(previousKeys)
                            outputFile.write('\t'.join(currentDataRow) + '\n')

                    addDataRow(self.outputDataStructure, 0, 0)