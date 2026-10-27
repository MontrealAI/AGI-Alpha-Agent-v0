# Digital Thread Box Data
Design, Manufacturing, and Quality data for the box assembly for collaborating around Mfg.io

## Directory Structure
+ CAD 
  - Digital Product Definition, in accordance to ASME Y14.41-2012, created using SolidWorks 2016
+ Clean 
  - Raw output from machine tool adapters with white-space and recording errors cleaned
  - Pipe delimited in accordance with the MTConnect standard v1.3
+ FAIR 
  - First article inspection reporting data in QIF 2.1 format
  - Data conforms to QIF XSD (http://qifstandards.org/latest-qif-version/)
  - Each file contains data for 20 instances of the same part
  - NIST / Mitutoyo completed inspection
+ MTConnect 
  - XML-formatted data of the machine tool output data in accordance with the MTConnect standard v1.3
  - Data conforms to MTConnect v1.3 schemas (https://github.com/mtconnect/schema)
+ NC Code 
  - Machining programs for operations steps for each part in accordance with ISO 6983 (G-code)
+ PartData 
  - Combined "Split" data organized into data blocks by part instance
+ QIF-IncomingInspection 
  - Receiving / incoming inspection reporting data in QIF 2.1 format
  - Data conforms to QIF XSD (http://qifstandards.org/latest-qif-version/)
  - Each file contains data for 20 instances of the same part
  - The MTC in the UK completed inspection
+ Raw 
  - Raw output from machine tool adapters as recorded on the given date and machine
+ Split 
  - Parsed "Clean" data split into data blocks by operation for each part instance

## Contacts

[Thomas Hedberg](https://www.nist.gov/people/thomas-hedberg). 

## Disclaimers

The use of any software or hardware by the project does not imply a recommendation or endorsement by NIST.

The use of the project results in other software or hardware products does not imply a recommendation or endorsement by NIST of those products.

We would appreciate acknowledgment if any of the project results are used, however, the use of the NIST logo is not allowed.

NIST-developed software is provided by NIST as a public service. You may use, copy and distribute copies of the software in any medium, provided that you keep intact this entire notice. You may improve, modify and create derivative works of the software or any portion of the software, and you may copy and distribute such modifications or works. Modified works should carry a notice stating that you changed the software and should note the date and nature of any such change. Please explicitly acknowledge the National Institute of Standards and Technology as the source of the software.

NIST-developed software is expressly provided “AS IS.” NIST MAKES NO WARRANTY OF ANY KIND, EXPRESS, IMPLIED, IN FACT OR ARISING BY OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT AND DATA ACCURACY. NIST NEITHER REPRESENTS NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE, OR THAT ANY DEFECTS WILL BE CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF, INCLUDING BUT NOT LIMITED TO THE CORRECTNESS, ACCURACY, RELIABILITY, OR USEFULNESS OF THE SOFTWARE.

You are solely responsible for determining the appropriateness of using and distributing the software and you assume all risks associated with its use, including but not limited to the risks and costs of program errors, compliance with applicable laws, damage to or loss of data, programs or equipment, and the unavailability or interruption of operation. This software is not intended to be used in any situation where a failure could cause risk of injury or damage to property. The software developed by NIST employees is not subject to copyright protection within the United States.
