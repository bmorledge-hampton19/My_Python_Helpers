# This script is testing the CountThisInThat classes by replicating my previous code that counts mutations in nucleosomes for comparison.
from typing import List

from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
from benbiohelpers.CountThisInThat.Counter import ThisInThatCounter
from benbiohelpers.CountThisInThat.InputDataStructures import EncompassingDataDefaultStrand
from benbiohelpers.CountThisInThat.CounterOutputDataHandler import AmbiguityHandling, CounterOutputDataHandler


class NucleosomeCODH(CounterOutputDataHandler):

    def getCountDerivatives(self, previousKeys, getHeaders = False) -> List[str]:
        if getHeaders: return ["Both_Strands_Counts", "Aligned_Strands_Counts"]
        else:
            thisPlusCounts = self.outputDataStructure[previousKeys[0]][True]
            thisMinusCounts = self.outputDataStructure[previousKeys[0]][False]
            oppositeMinusCounts = self.outputDataStructure[-previousKeys[0]][False]
            return [str(thisPlusCounts+thisMinusCounts),str(thisPlusCounts+oppositeMinusCounts)]


class MutationsInNucleosomesCounter(ThisInThatCounter):

    def setUpOutputDataHandler(self):
        self.outputDataHandler = NucleosomeCODH()
        self.outputDataHandler.addRelativePositionStratifier(self.currentEncompassingFeature, extraRangeRadius = self.encompassingFeatureExtraRadius,
                                                             outputName = "Dyad_Position")
        self.outputDataHandler.addStrandComparisonStratifier(strandAmbiguityHandling = AmbiguityHandling.tolerate)

    def constructEncompassingFeature(self, line) -> EncompassingDataDefaultStrand:
        return EncompassingDataDefaultStrand(line, self.acceptableChromosomes)

    def writeResults(self):
        return super().writeResults(customStratifyingNames=(None, {True:"Plus_Strand_Counts", False:"Minus_Strand_Counts"}))


def testingCountThisInThat1(mutationPosFilePath, nucleosomePosFilePath, outputFilePath):

    counter = MutationsInNucleosomesCounter(mutationPosFilePath, nucleosomePosFilePath, outputFilePath, encompassingFeatureExtraRadius=73)
    counter.count()
    counter.writeResults()


def main():

    # Create the Tkinter UI
    dialog = TkinterDialog(workingDirectory=getDataDirectory())
    dialog.createFileSelector("Bed Mutation Data:",0,("Bed Files",".bed"))    
    dialog.createFileSelector("Nucleosome Dyad Center Positions:",1,("Bed Files",".bed"))
    dialog.createFileSelector("Output File:",2,("TSV Files",".tsv"), newFile = True)

    # Run the UI
    dialog.mainloop()

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    testingCountThisInThat1(dialog.selections.getIndividualFilePaths()[0], dialog.selections.getIndividualFilePaths()[1],
                            dialog.selections.getIndividualFilePaths()[2])


if __name__ == "__main__": main()