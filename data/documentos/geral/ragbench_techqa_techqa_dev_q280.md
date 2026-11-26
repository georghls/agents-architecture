# RAGBench Base Técnica Corporativa (TechQA) — Caso techqa_DEV_Q280

## Context Document 1
DTXINST; Integration Server; WESB; Install; prerequiste TECHNOTE (TROUBLESHOOTING) PROBLEM(ABSTRACT)

When attempting to install WebSphere® Transformation Extender for Integration Server version 8.2.0.x, to a server on which WebSphere Enterprise Service Bus has already been successfully installed, the Integration Server install fails with a "Setup has detected that you are trying to install a product that requires an IBM WebSphere Integration Server as a prerequisite." error message CAUSE

The WebSphere Transformation Extender for Integration Servers install process cannot locate a keyword in the .nifregistry file ENVIRONMENT During the installation of WebSphere Transformation Extender for Integration Servers v8.2.0.x DIAGNOSING THE PROBLEM An error message, "Setup has detected that you are trying to install a product that requires an IBM WebSphere Integration Server as a prerequisite." will be displayed. RESOLVING THE PROBLEM

The following steps can be taken to edit the .nifregistry file to resolve this installation issue: Operating System root installed .nifregistry location Windows %SystemRoot% AIX /usr/.ibm/.nif Solaris, Linux, HP-UX /opt/.ibm/.nif Operating System non-root installed .nifregistry location AIX, Solaris, Linux, HP-UX ~/.nif 1) Open the .nifregistry file with a file editor of your choice. The .nifregistry file is located in the directory depicted in the table listed above.

2) Look for a line similar to the following that contains "WebSphere/ESB/": <product installrooturi=" file:///C:/Program%20Files/IBM/WebSphere/ESB/ [file:///C:/Program%20Files/IBM/WebSphere/ESB/]" lastvisited="2008-07-16 14:17:00-0400" productid="ND" version="6.1.0.17"/> 3) Change the productid to be WBI. 4) After editing the .nifregistry file, the line should now look like:

<product installrooturi=" file:///C:/Program%20Files/IBM/WebSphere/ESB/ [file:///C:/Program%20Files/IBM/WebSphere/ESB/]" lastvisited="2008-07-16 14:17:00-0400" productid="WBI" version="6.1.0.17"/> Your version of WBI may be different, but as long as it is a 6.1.0.x release, it is relative to this Technote. 5) Install the WebSphere Transformation Extender for Integration Server software. 6) After the install is complete, restore the productid to "ND" in the .nifregistry file.

The .nifregistry file may have slightly different values in it, the key is to modify just the productid. PRODUCT ALIAS/SYNONYM WTX Integration Server Ascential DataStage TX

## Context Document 2
WTX; TX TECHNOTE (FAQ) QUESTION What directories does the WTX Map Primitive use in IBM® WebSphere® Transformation Extender for WebSphere Enterprise Service Bus? ANSWER For maps that are * Specified by Use map from project setting * Set in the service message object (SMO) mapServerLocation property * Set in the SMO and overridden at runtime The home directory is: < WESBserver >/temp/WTX/< flowName >/< mediationName >

where < WESBserver> is the server name under the profiles directory in the WebSphere Enterprise Service Bus or WebSphere Process Server installation location. The directory of the WebSphere Transformation Extender map's default audit log, trace log, and workspace is < WESBserver >/logs/WTX/< flowName >/< mediationName >

## Context Document 3
WebSphere Transformation Extender; WebSphere TX; WTX; ITX; application programming DOWNLOADABLE FILES ABSTRACT This document describes how to download IBM® WebSphere® Transformation Extender for Application Programming V8.4.1.4. DOWNLOAD DESCRIPTION WebSphere Transformation Extender for Application Programming provides the core transformation engine, callable by its programming interface.

C, Java, Enterprise JavaBeans (EJB), Cobol, and .Net application programming interfaces (APIs) are available to engage the transformation engine to process a prebuilt transformation. PREREQUISITES See the system requirements for the supported hardware and software: URL LANGUAGE SIZE(Bytes) IBM Transformation Extender system requirements [http://www.ibm.com/support/docview.wss?uid=swg27045341] English 10 INSTALLATION INSTRUCTIONS

After you download the code package, follow the instructions in the release notes to install the product: URL LANGUAGE SIZE(Bytes) IBM Transformation Extender release notes [http://www.ibm.com/support/docview.wss?&uid=swg27008337#841] English 10 DOWNLOAD PACKAGE Entitled customers can download the code package from Fix Central:

Download RELEASE DATE LANGUAGE SIZE(Bytes) Download Options Fix Central 11 Mar 2016 English 172000 HTTP [http://www.ibm.com/support/fixcentral/swg/selectFixes?parent=ibm~Other%2Bsoftware&product=ibm/WebSphere/WebSphere+Transformation+Extender&release=8.4.1.4&platform=All&function=all&useReleaseAsTarget=true] TECHNICAL SUPPORT Get online support through the following links:

Fix Central support: http://www.ibm.com/systems/support/fixes/en/fixcentral/help/index.html [http://www.ibm.com/systems/support/fixes/en/fixcentral/help/index.html] Transformation Extender support: http://www.ibm.com/software/integration/wdatastagetx/support [http://www.ibm.com/software/integration/wdatastagetx/support]

## Context Document 4
8.4.0.2; WTX 8.4.0.2; 8.3.2; HIPAA 4.3.2.2; 8.2.1.6 NEWS ABSTRACT April 27, 2012 IBM WebSphere® Transformation Extender V8.4.0.2 and Q2 Industry Packs are now available through Passport Advantage. Build ID: 8.4.0.2(12) Industry Pack releases: Pack for HIPAA EDI 4.3.2.2 Trading Manager 8.2.1.6 Pack for SAP R/3 8.3.2 CONTENT Fix List WebSphere Transformation Extender V8.4.0.2 Fix List [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27024860]

WTX 8.4.0.2 Core Release Notes Release Notes for IBM WebSphere Transformation Extender V8.4.0.2 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27019258] Release Notes for IBM WebSphere Transformation Extender with Launcher Hypervisor Edition [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27022312]

WTX 8.4.0.2 Core Download Documents WebSphere Transformation Extender with Command Server [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032141] WebSphere Transformation Extender Design Studio [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032142] WebSphere Transformation Extender Online Library [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24027668] WebSphere Transformation Extender with Launcher Hypervisor Edition

[http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032144] WebSphere Transformation Extender with Launcher [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032143] WebSphere Transformation Extender Launcher Agent [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032145] WebSphere Transformation Extender for Application Programming [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032140] WebSphere Transformation Extender Secure Adapter Collection

[http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032147] WebSphere Transformation Extender for Integration Servers [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032146]

WTX Pack Release Notes Release Notes for WebSphere Transformation Extender Pack for HIPAA EDI 4.3.2.2 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27024259] Release Notes for WebSphere Transformation Extender Trading Manager 8.2.1.6 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27023979] Release Notes for WebSphere Transformation Extender Pack for SAP R/3 8.3.2 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27024492]

WTX Pack Download Documents WebSphere Transformation Extender Pack for HIPAA EDI 4.3.2.2 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032514] WebSphere Transformation Extender Trading Manager 8.2.1.6 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032513] WebSphere Transformation Extender Pack for SAP R/3 8.3.2 [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg24032512]

WTX Pack Fix Lists WebSphere Transformation Extender Pack for HIPAA EDI 4.3.2.2 Fix List [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27024912] WebSphere Transformation Extender Trading Manager 8.2.1.6 Fix List [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27024913] WebSphere Transformation Extender Pack for SAP R/3 8.3.2 Fix List [http://www.ibm.com/support/docview.wss?rs=2320&uid=swg27024914]

IBM PassPort Advantage Online [http://www-01.ibm.com/software/howtobuy/passportadvantage/pao_customers.htm] PRODUCT ALIAS/SYNONYM Ascential DataStage TX Mercator

## Context Document 5
WTX TX IIB DTXplugin cannot be located TECHNOTE (TROUBLESHOOTING) PROBLEM(ABSTRACT) Error 'DTXPlugin cannot be located' is encountered. SYMPTOM Error 'DTXPlugin cannot be located' is shown if you "move over" the ITX Plugin-Node after installing IBM Transformation Extender (ITX) with IBM Integration Bus (IIB) Toolkit. CAUSE Two installations of IBM Transformation Extender (ITX) installed on the same system with IBM Integration Bus (IIB) Toolkit. ENVIRONMENT

Using ITX V9.0.0.x with IIB10.0.0.x and two versions of ITX are installed on the same system. DIAGNOSING THE PROBLEM The TX Map node plugin displays an error in a new installation when you "move over" the ITX Plugin-Node. RESOLVING THE PROBLEM Use a new Work Space.
