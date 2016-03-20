# ---------------------------------------------------------------------------
# Proximity_Suit_Tl.py
# Created on: 2015-03-09
# Last modified: 3/20/16
# Created By: David Wasserman
# Usage: Proximity_Suit_Tl <In_Reference_Suit > <In_Suit_Var> <Out_Suit_Prox> 
# Description: 
# This tool is designed to aid in the creation of data driven suitability layers. The tool takes a suitability layer and a variable layer as inputs. The suitability layer represents the features that you want to create suitabilities for ("Single Family Residential"), and the variable layer represents the variable that relates to the suitability layer (Parks for Recreation). Based on the average and standard deviation of the distance each object in the suitability layer is from the variable layer, a euclidean distance away from the variable layer is reclassified by the following remap table.
# "RemapRange([[0,Mean,9],[Mean,Mean+(Qrt_StD),8],[Mean+(Qrt_StD),Mean+(Qrt_StD*2),7],[Mean+(Qrt_StD*2),Mean+(Qrt_StD*3),6],[Mean+(Qrt_StD*3),Mean+(Qrt_StD*4),5],[Mean+(Qrt_StD*4),Mean+(Qrt_StD*5),4],[Mean+(Qrt_StD*5),Mean+(Qrt_StD*6),3],[Mean+(Qrt_StD*6),Mean+(Qrt_StD*7),2],[Mean+(Qrt_StD*7),(Max_Ra_Value+1),1]])."
# Before running this tool  it is critical you make sure your raster environments are set up correctly, specifically cell size, extent, and the mask you wish you use.
# ---------------------------------------------------------------------------
# Copyright 2015 David J. Wasserman
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# --------------------------------
# Import arcpy module
import arcpy
import os
from arcpy import env
from arcpy.sa import *

# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")

# Script Arguments and Parameters
In_Reference_Suit_Raw = arcpy.GetParameterAsText(
        0)  # is what you want a suitability of- what the variable layer refers to for its reclass statistics
In_Suit_Var_Raw = arcpy.GetParameterAsText(
        1)  # is the variable of interest to the reference layer-what the reclassified raster is based on
Out_Suit_Prox_Raw = arcpy.GetParameterAsText(2)  # destination of the output suitability raster input

Invert_Ra_Value = arcpy.GetParameter(3)  # Boolean value to invert the raster.


def arcToolReport(function=None, arcToolMessageBool=False, arcProgressorBool=False):
    """This decorator function is designed to be used as a wrapper with other GIS functions to enable basic try and except
     reporting (if function fails it will report the name of the function that failed and its arguments. If a report
      boolean is true the function will report inputs and outputs of a function.-David Wasserman"""

    def arcToolReport_Decorator(function):
        def funcWrapper(*args, **kwargs):
            try:
                funcResult = function(*args, **kwargs)
                if arcToolMessageBool:
                    arcpy.AddMessage("Function:{0}".format(str(function.__name__)))
                    arcpy.AddMessage("     Input(s):{0}".format(str(args)))
                    arcpy.AddMessage("     Ouput(s):{0}".format(str(funcResult)))
                if arcProgressorBool:
                    arcpy.SetProgressorLabel("Function:{0}".format(str(function.__name__)))
                    arcpy.SetProgressorLabel("     Input(s):{0}".format(str(args)))
                    arcpy.SetProgressorLabel("     Ouput(s):{0}".format(str(funcResult)))
                return funcResult
            except Exception as e:
                arcpy.AddMessage(
                        "{0} - function failed -|- Function arguments were:{1}.".format(str(function.__name__),
                                                                                        str(args)))
                print(
                "{0} - function failed -|- Function arguments were:{1}.".format(str(function.__name__), str(args)))
                print(e.args[0])

        return funcWrapper

    if not function:  # User passed in a bool argument
        def waiting_for_function(function):
            return arcToolReport_Decorator(function)

        return waiting_for_function
    else:
        return arcToolReport_Decorator(function)


@arcToolReport
def invertSuitValue(value, invertBool, maxValue=9):
    """Inverts suitability values passed to it if a boolean is checked. """
    try:
        if invertBool:
            return ((maxValue + 1) - value)
        else:
            return value
    except:
        return value


@arcToolReport
def do_analysis(In_Reference_Suit, In_Suit_Var, Out_Suit_Prox, Invert_Boolean):
    try:
        # Path setup-temp workspace: You can edit the script to use this if you want, but I defer to defaults.
        # tempFC=os.path.join(arcpy.env.scratchGDB,"tempFC")# for a temporary data

        # Progressor setup:
        arcpy.SetProgressor("step", "Creating Euclidean Distance raster...", 0, 7, 1)

        # Process-Euclidean Distance
        arcpy.AddMessage("Creating Euclidean Distance from Variable Layer")
        EuDist_Ra = EucDistance(In_Suit_Var)

        # Process: Add Field
        arcpy.SetProgressorLabel("Appending and calculating a common field for Zonal Statistics by table...")
        arcpy.SetProgressorPosition()
        arcpy.AddMessage("Adding and Calculating Common Field for Zonal Statistics by Table")
        Added_Field_st1 = arcpy.AddField_management(In_Reference_Suit, "All_Same", "LONG")

        # Process: Calculate Field
        Calced_Field_st2 = arcpy.CalculateField_management(Added_Field_st1, "All_Same", 1, "PYTHON")

        # Process: Make Feature Layer (2)
        arcpy.SetProgressorLabel("Making Reference Feature Layer with new Field...")
        arcpy.SetProgressorPosition()
        arcpy.AddMessage("Making Variable Feature Layer with new Field")
        Zonal_Input = arcpy.MakeFeatureLayer_management(Calced_Field_st2)

        # Process: Zonal Statistics as Table
        arcpy.SetProgressorLabel("Calculating Zonal Statistics for remap table...")
        arcpy.SetProgressorPosition()
        arcpy.AddMessage("Calculating Zonal Statistics")
        Zonal_Stat_Prox = ZonalStatisticsAsTable(Zonal_Input, "All_Same", EuDist_Ra, "outTable")

        # Process: Get Field Values (2-mean and standard deviation of distances)
        arcpy.SetProgressorLabel("Declaring Cursors to read Zonal Statistics table...")
        arcpy.SetProgressorPosition()
        arcpy.AddMessage("Declaring cursors to read Zonal Statistics table")
        Std_Dev = (arcpy.da.SearchCursor(Zonal_Stat_Prox, ["STD"]).next()[
                       0])  # Since it was all one field, the first element should be the only element
        Mean = (arcpy.da.SearchCursor(Zonal_Stat_Prox, ["MEAN"]).next()[
                    0])  # Since it was all one field, the first element should be the only element
        Qrt_StD = Std_Dev / 4  # one quarter standard deviation
        arcpy.AddMessage("Retrieved Mean of {0} and Std Dev of {1}".format(Mean, Std_Dev))

        arcpy.SetProgressorLabel("Calculating Statistics for Distance Raster...")
        arcpy.SetProgressorPosition()
        arcpy.AddMessage("Calculating Statistics of Distance Raster")
        EuDist_Ra_wStats = arcpy.CalculateStatistics_management(EuDist_Ra)

        # Process: Get Max Raster Value for remap
        arcpy.SetProgressorLabel("Retrieving maximum value from value raster...")
        arcpy.SetProgressorPosition()
        Max_Value_Result = arcpy.GetRasterProperties_management(EuDist_Ra_wStats, "MAXIMUM")
        Max_Ra_Value = float(Max_Value_Result.getOutput(0))
        arcpy.AddMessage(
                "Maximum Raster Value of {0} is used as the final value in the remap table.".format(Max_Ra_Value))

        # Remap List creation
        myremap = RemapRange([[0, Mean, invertSuitValue(9, Invert_Boolean)],
                              [Mean, Mean + (Qrt_StD), invertSuitValue(8, Invert_Boolean)],
                              [Mean + (Qrt_StD), Mean + (Qrt_StD * 2),invertSuitValue(7,Invert_Boolean)],
                              [Mean + (Qrt_StD * 2), Mean + (Qrt_StD * 3), invertSuitValue(6,Invert_Boolean)],
                              [Mean + (Qrt_StD * 3), Mean + (Qrt_StD * 4), invertSuitValue(5,Invert_Boolean)],
                              [Mean + (Qrt_StD * 4), Mean + (Qrt_StD * 5), invertSuitValue(4,Invert_Boolean)],
                              [Mean + (Qrt_StD * 5), Mean + (Qrt_StD * 6), invertSuitValue(3,Invert_Boolean)],
                              [Mean + (Qrt_StD * 6), Mean + (Qrt_StD * 7), invertSuitValue(2,Invert_Boolean)],
                              [Mean + (Qrt_StD * 7), (Max_Ra_Value + 1), invertSuitValue(1,Invert_Boolean)]])
                                # float("inf") does not work so this is the short term solution

        # Process: Reclassify
        arcpy.SetProgressorLabel("Starting Data Driven Reclassification...")
        arcpy.SetProgressorPosition()
        arcpy.AddMessage("Starting Data Driven Reclassification")
        Data_Driven_Reclass = Reclassify(EuDist_Ra_wStats, "Value", myremap)
        Data_Driven_Reclass.save(Out_Suit_Prox)

        # Finishing Messages and clean up.
        output_Name = (os.path.split(Out_Suit_Prox)[1])
        arcpy.AddMessage("Finished Data Driven Reclassification of {0}".format(output_Name))
        arcpy.AddMessage("Final Reclassification: {0}".format(myremap))
        arcpy.ResetProgressor()
        arcpy.Delete_management(Zonal_Stat_Prox)  # delete temporary table- edit script if you want to save it.
    except arcpy.ExecuteError:
        print(arcpy.GetMessages(2))
    except Exception as e:
        print(e.args[0])


if __name__ == '__main__':
    do_analysis(In_Reference_Suit_Raw, In_Suit_Var_Raw, Out_Suit_Prox_Raw, Invert_Ra_Value)
