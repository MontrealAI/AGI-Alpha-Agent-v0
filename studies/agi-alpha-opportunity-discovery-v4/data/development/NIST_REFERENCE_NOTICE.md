# Ontologies of Design and Inspection Datafor a Three-Component Assembly
This dataset includes ontologies translated from design and inspection data in a technical data package (TDP), which represents a three-component assembly, of the National Institute of Standards and Technology (NIST) Smart Manufacturing System (SMS) Test Bed.
The use of ontologies aims to integrate the product lifecycle data of engineering design represented in STEP AP242 and quality assurance represented in QIF in the context of standards-based digital thread.

## Directory Structure
+ [Design Data](./1_DesignData)
  - As-designed instance data conforms to STEP AP242 represented in STEP Part 21
+ [Inspection Data](./2_InspectionData)
  - As-inspected instance data conforms to QIF version 2.1 represented in XML
+ [STEP Ontology](./3_STEPOntology)
  - Ontology representing as-designed instance data written in RDF/XML
+ [QIF Ontology](./4_QIFOntology)
  - Ontology representing as-inspected instance data written in RDF/XML
+ [Integrated Ontology](./5_IntegratedOntology)
  - Integrated ontology including STEP and QIF ontology written in RDF/XML

## Contacts

[William Z. Bernstein](https://www.nist.gov/people/william-z-bernstein).

## Disclaimers

The use of any software or hardware by the project does not imply a recommendation or endorsement by NIST.

The use of the project results in other software or hardware products does not imply a recommendation or endorsement by NIST of those products.

We would appreciate acknowledgment if any of the project results are used, however, the use of the NIST logo is not allowed.

NIST-developed software is provided by NIST as a public service. You may use, copy and distribute copies of the software in any medium, provided that you keep intact this entire notice. You may improve, modify and create derivative works of the software or any portion of the software, and you may copy and distribute such modifications or works. Modified works should carry a notice stating that you changed the software and should note the date and nature of any such change. Please explicitly acknowledge the National Institute of Standards and Technology as the source of the software.

NIST-developed software is expressly provided “AS IS.” NIST MAKES NO WARRANTY OF ANY KIND, EXPRESS, IMPLIED, IN FACT OR ARISING BY OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, NON-INFRINGEMENT AND DATA ACCURACY. NIST NEITHER REPRESENTS NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE, OR THAT ANY DEFECTS WILL BE CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF, INCLUDING BUT NOT LIMITED TO THE CORRECTNESS, ACCURACY, RELIABILITY, OR USEFULNESS OF THE SOFTWARE.

You are solely responsible for determining the appropriateness of using and distributing the software and you assume all risks associated with its use, including but not limited to the risks and costs of program errors, compliance with applicable laws, damage to or loss of data, programs or equipment, and the unavailability or interruption of operation. This software is not intended to be used in any situation where a failure could cause risk of injury or damage to property. The software developed by NIST employees is not subject to copyright protection within the United States.
