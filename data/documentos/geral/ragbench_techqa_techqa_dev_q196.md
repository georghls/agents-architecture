# RAGBench Base Técnica Corporativa (TechQA) — Caso techqa_DEV_Q196

## Context Document 1
TECHNOTE (TROUBLESHOOTING) PROBLEM(ABSTRACT) After installing Modeler 14.1 64-bit client and Statistics 32-bit client on a 64-bit operating system, Modeler cannot find the Statistics install. Nor will any of the Statistics function within Modeler. The user will receive the error "Please run the Statistics License Utility" RESOLVING THE PROBLEM Having a 64-bit install of Modeler and a 32-bit installation of Statistics is not a supported configuration by IBM SPSS.

In order to use the SPSS Statistics nodes from within Modeler, you will need to install the 64-bit version of Statistics. This is because the 32-bit API's of SPSS Statistics cannot be loaded by the 64-bit installation of SPSS Modeler. This limitation is expected to be documented in future releases of IBM SPSS Modeler. RELATED INFORMATION Need more help?

Our Modeler forum is Live! [https://developer.ibm.com/answers/topics/modeler/?smartspace=predictive-analytics] HISTORICAL NUMBER 93142

## Context Document 2
spss statistics 21.0.0 21.0 sms install push silent SCCM extract MSI TECHNOTE (FAQ) QUESTION After extracting the MSI from the product installer (.EXE file) there is no SMS file found as was indicated by the product documentation. This file is needed for some types of silent/push installation methods. ANSWER The contents of the SMS file are between the asterix lines below: ******** [PDF] Version = 2.0 [Package Definition] Name = IBM SPSS Statistics 21 Version = 21.0.0.0

Publisher = IBM Corp. Language = English, French, German, Spanish, Italian, Polish, Korean, Japanese, Russian, Chinese (Simplified), Chinese (Traditional), Portuguese (Brazil) Programs = Setup MifFileName = IBM SPSS Statistics 21.mif MifName = IBM SPSS Statistics 21 MifVersion = 21.0.0.0 MifPublisher = IBM Corp. [Setup] Name = Automated Minimum Installation CommandLine English (United States) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1033.mst

CommandLine French (France) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1036.mst CommandLine German (Germany) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1031.mst CommandLine Spanish (Traditional-Spain) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1034.mst CommandLine Italian (Italy) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1040.mst

CommandLine Japanese (Japan) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1041.mst CommandLine Polish (Poland) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1045.mst CommandLine Russian (Russia) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1049.mst CommandLine Korean (Korea) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1042.mst CommandLine Chinese (Simplified) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=2052.mst

CommandLine Chinese (Traditional) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1028.mst CommandLine Portuguese (Brazil) = msiexec /qn /I "IBM SPSS Statistics 21.msi" TRANSFORMS=1046.mst SupportedClients = Win 9x, Win NT (i386) UserInputRequired = False RemoveProgram = True UnInstallKey = {1E26B9C2-ED08-4EEA-83C8-A786502B41E5} ***** Simply copy the above lines into a normal text file with the SMS extension and use it normally. RELATED INFORMATION Need more help?

Our Statistics forum is Live! [https://developer.ibm.com/answers/topics/statistics.html?smartspace=predictive-analytics]

## Context Document 3
TECHNOTE (FAQ) QUESTION What causes an 1152 error during extraction of Modeler self extracting executable? CAUSE When an IBM SPSS compressed image is launched, files compressed within it are extracted to the temporary location assigned to the signed in user i.e. /Documents and settings/... or /users. The possibility of these files downloaded improperly exists. You can use a tool such as MD5 to verify the file content or simply attempt downloading a second time and test.

Other possible causes of this error: - Available space within the temporary location noted by the installer. - Ability to write in the temporary location noted by the installer. ANSWER Transfer the files again, resolved the issue. RELATED INFORMATION Need more help? Our Modeler forum is Live! [https://developer.ibm.com/answers/topics/modeler/?smartspace=predictive-analytics]

## Context Document 4
TECHNOTE (FAQ) QUESTION Where is the Microsoft Installer (*.msi) file required for unattended/silent/push installations the IBM SPSS Statistics application? ANSWER The Microsoft Installer (*.msi) file for IBM SPSS Statistics applications is not available as a separate download. Accessing the.msi file for IBM SPSS Statistics is dependent upon the installation media you have received. Using the Software Download: 1. Download and save the installer executable (e.g.

'SPSS_Statistics_24_win64.exe') to a known, accessible location on the computer hard drive. 2. Next, you will need to use the /b switch from your command prompt to extract the .msi file. In the example below the SPSS_Statistics_24_win64.exe was downloaded to the C: drive. Provide the file location for the extraction. This example uses the directory "MSItest" on the C: drive: C:\>SPSS_Statistics_24_win64.exe /b"C:\MSItest" 3.

Notice that running this command will launch the InstallShield Wizard. Let this run until the .msi has been extracted. You will see "Extracting: IBM SPSS Statistics 24.msi" message from the installer. You do not need to proceed with the full installation. Using Installation Media (CD/DVD) 1. Insert the disk. 2. IF prompted to install the software, select 'Cancel'. 3. Browse to the media location. 4. Open the 'SPSSStatistics' folder.

The 32-bit MSI file will be located in the 'win32'. folder. The 64-bit MSI file will be located in the 'win64' folder. Using a compressed (.zip) file 1. Extract (decompress) the contents of the ZIP file into a designated folder. 2. The MSI folder will located in the designated folder. For documentation on IBM SPSS-specific commands for use with MSI files, see 'Administrator's Guide' appropriate to your license type (e.g. 'Site', 'Concurrent' Users Guide'). RELATED INFORMATION

Need more help? Our Statistics forum is Live! [https://developer.ibm.com/answers/topics/statistics.html?smartspace=predictive-analytics] Cross reference information Segment Product Component Platform Version Edition Business Analytics SPSS Statistics

## Context Document 5
push silent install client patch msi TECHNOTE (FAQ) QUESTION How can I push out an install or patch for the IBM SPSS Modeler Client application? ANSWER A Modeler install or patch can be pushed out to the clients with the following steps. Step 1: Harvest the .msi and accompanying files required for silent install. To do this: * Go to: Start > Run and type '%temp%' to navigate to the temporary path for Windows Installer programs. Delete all contents within this folder.

* Run the installer executable (SPSS_Modeler_141_win64.exe) as normal. When it finishes extracting and decompressing the .msi file and the end-user is required to click 'Continue', minimise this window. * Switch to the %temp% folder and locate the folder with the 'ModelerClient64.msi' file. Copy ALL contents within this folder and paste it to a local folder (e.g. C:\Temp\Modeler\ClientInstall). * Once copied, switch back to the installation wizard and hit 'Cancel'.

Step 2: Use the command prompt to execute the 'MsiExec' command: * Open a command prompt window as an Administrator and run the following command: (substitute <path> with the location of your .msi file) MsiExec.exe /i "<path>\ModelerClient.msi" /qn /L*v logfile.txt INSTALLDIR="C:\Program Files\IBM\SPSS\Modeler\14" LICENSETYPE="Network" LSHOST="mylicserver"

* For a full list of Silent Install options, please refer to the 'NetworkLicenseAdministratorsGuide.pdf' > 'Installaing the Product on the Local Desktop Computers > Pushing an Installation to Windows Computers. Once that you have confirmed that Modeler Client is operational, repeat the steps to extract the .msi file for Modeler Client Fix Pack 1.

Please note that it is highly recommended to delete the contents of the temporary folder as the Fix Pack and Client installations use the same file names. This is to prevent the accidental copying of the Client installation instead of the Fix Pack install. RELATED INFORMATION Need more help? Our Modeler forum is Live! [https://developer.ibm.com/answers/topics/modeler/?smartspace=predictive-analytics]
