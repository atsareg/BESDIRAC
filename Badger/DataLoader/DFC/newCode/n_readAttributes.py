#!/usr/bin/env python
# -*- coding:utf-8 -*-
#data 13/07/26
#for data/all  name of file like run_0023454_All_file014_SFO-2.dst
#for data/skim & mc, we use new file naming rule,
#file name like resonance_eventType_streamId_runL_runH_*.dst

import os
import os.path
import ROOT
from ROOT import gROOT
import string
import re

from DIRAC.Core.Base import Script
Script.parseCommandLine( ignoreErrors = True )
from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient

#get number behiend string "exp"
def getNum(expNum):
    format = re.compile(r"\d+")
    res = format.search(expNum)

    if res is not None:
        return res.group()      
    
#Get expNum and resonance from ExpSearch according runids
def getExpRes(runids):
    entries = []
    expRes = {}
    expNumList = []
    resList = []
    
    #print"runids",runids
    #from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient
    client = FileCatalogClient()
    #get all entries under catalog "/BES3/ExpSearch"
    dir = '/zhanggang_test/ExpSearch'
    result = client.listDirectory(dir)
    #print "result",result
    #print result
    if result['OK']:
        for i,v in enumerate(result['Value']['Successful'][dir]['SubDirs']):
            result = client.getDirectoryMetadata(v)['Value']
            runfrm = string.atoi(result['runFrom'])
            runto = string.atoi(result['runTo'])
    
            for runid in runids:
                #check all runid whether between runfrm and runto of each entry 
                #under catalog "/BES3/ExpSearch"
                if runfrm<=runid<=runto:
                    #print "true"
                    #if this runid between runfrm and runto,and round isn't in expNumList
                    #add this expNum to expNumList
                    if result['round'] not in expNumList:
                        expNumList.append(result['round'])

                    #resonance of this id isn't in resonance List,add it to resList
                    if result['resonance'] not in resList:
                        resList.append(result['resonance'])
                    
        #only including one resonance
        if len(resList) == 1:
            expRes["resonance"] = resList[0]
        else:
            #has several resonances,may be has something wrong to this file
            print "several resonances found:",resList
            return False

        #only including one expNum
        if len(expNumList) == 1:
            expRes["round"] = expNumList[0]
        else:
            #if including several expNums,combine these expNum into mexpN1pN2p...
            sorted(expNumList)
            str = "m" + expNumList[0]
            for expNum in expNumList[1:]:
                str = str + "p+" + getNum(expNum)
           
            expRes["round"] = str

    else:
        print "ExpSearch directory is empty, please run createBesDirDFC first"
        return False
  
    return expRes


#check whether eventType is stored in eventTypeList directory
def eventTypeCheck(eventType):
    entries = []
    
    client = FileCatalogClient()
    dir = '/BES3/EventTypeList'
    result = client.listDirectory(dir)
    if result['OK']:
        for i,v in enumerate(result['Value']['Successful'][dir]['SubDirs']):
            if eventType == v.split('/')[2]:   
                return True

    return False 
    
    
#judge format of file
class JudgeFormat(Exception):
    def __init__(self, format):
        self.format = format
    def __str__(self):
        return repr("the File's format is not ",self.format)

#type of srcformat is list,it includes many formats
def checkFormat(srcformat,file):
    flag = 0
    for format in srcformat:
        #if format of file is in srcformat
        if  file.endswith(format):
            flag = 1
    return flag
                
        
#Before reading information from .root file,we need to use changeFormat
#function to create a .root link for .dst file
def changeFormat(dstfile,rootfile,srcformat=[".dst",".tag"],destformat=[".root"]):
    flag = checkFormat(srcformat,dstfile)
    if flag==0:
        raise JudgeFormat(srcformat)
        return
    flag = checkFormat(destformat,rootfile)
    if flag==0:
        raise JudgeFormat(destformat)
        return

    #if this rootfile has exists,then delete it
    if os.path.exists(rootfile):
        os.unlink(rootfile)
         
    #create a new rootfile for dstfile
    os.symlink(dstfile,rootfile)
    return rootfile


#dstfile like /bes3fs/offline/data/655-1/4040/dst/110504/run_0023474_All_file007_SFO-2.dst
def getLFN(dstfile,format=[".dst",".tag"]):
    flag = checkFormat(format,dstfile)

    if flag==0:
        raise JudgeFormat(format)
        return
    #split dstfile by "/",then get "lfn.dst"    
    items=dstfile.split("/")
    length=len(items)

    filename=items[length-1]
    
    #split "*.dst" by "."
    #get lfn
    lfn = filename.split('.')[0]

    return lfn

#get size of dst file
def getFileSize(dstfile,format = [".dst",".tag"]):
    flag = checkFormat(format,dstfile)
    
    if flag==0:
        raise JudgeFormat(format)
        return
    
    if os.path.exists(dstfile):
        #get file's size
        return os.path.getsize(dstfile)


#lfn like resonance_eventType_streamId_runL_runH_*,get attributes:resonance,eventType,streamId,runL,runH 
#lfn like run_0009947_All_file001_SFO-1,get attribute runId
def splitLFN(lfn,type):
    result = {}
        
    items = lfn.split("_")

    if type == "all":
        if items[2] == "All":
            runId = string.atoi(items[1])
            return runId
    
    else:        
        result["resonance"] = items[0]
        result["eventType"] = items[1]
        result["streamId"] = items[2]
        result["runL"] = string.atoi(items[3])
        result["runH"] = string.atoi(items[4])
   
        return result
    


#get runIdList from JobOptions
def getRunIdList(jobOptions):
    result = {}    
    runIdList = []
    str1=jobOptions[0]
    pat = re.compile(r'RunIdList= {-\d+(,-?\d+)+}')
    res1 = pat.search(str1)
    
    if res1 is not None:
        #get a string like:RunIdList={-10513,0,-10629}
        str2 = res1.group()

        result["description"] = str2
        pat = re.compile(r'-\d+(,-?\d+)+')
        list = pat.search(str2)
        
        if list is not None:
            #get a string like:-10513,0,-10629
            runIds = list.group()

            #split runIds according ','
            items=runIds.split(',')

            #members' style in items is string,we need to change their style to integer
            for i in items:
                if i!='0':
                    runid=abs(string.atoi(i))
                    runIdList.append(runid)

            result["runIdList"] = runIdList

    return result
        
        
        
#get Boss version, runid, Entry number, JobOptions from root file
def getCommonInfo(rootfile):
    
    commoninfo = {}

    gROOT.ProcessLine('gSystem->Load("libRootEventData.so");')
    gROOT.ProcessLine('TFile file("%s");'%rootfile)
    gROOT.ProcessLine('TTree* tree =(TTree*)file.Get("JobInfoTree");')
    gROOT.ProcessLine('TTree* tree1 =(TTree*)file.Get("Event");')
    gROOT.ProcessLine('TBranch* branch =(TBranch*)tree->GetBranch("JobInfo");')
    gROOT.ProcessLine('TBranch* branch1 =(TBranch*)tree1->GetBranch("TEvtHeader");')
    gROOT.ProcessLine('TJobInfo* jobInfo = new TJobInfo();')
    gROOT.ProcessLine('TEvtHeader* evtHeader = new TEvtHeader();')
    gROOT.ProcessLine('branch->SetAddress(&jobInfo);')
    gROOT.ProcessLine('branch1->SetAddress(&evtHeader);')
    gROOT.ProcessLine('branch->GetEntry(0);')
    gROOT.ProcessLine('branch1->GetEntry(0);')
    gROOT.ProcessLine('Int_t num=tree1.GetEntries()')
    
    #get Boss Version
    commoninfo["bossVer"] = ROOT.jobInfo.getBossVer() 
    #get RunId
    commoninfo["runId"] = abs(ROOT.evtHeader.getRunId())
    #get all entries
    commoninfo["eventNum"] = ROOT.num
    #get TotEvtNo
    #commoninfo["TotEvtNo"] = list(i for i in ROOT.jobInfo.getTotEvtNo())
    #get JobOption
    commoninfo["jobOptions"] = list(i for i in ROOT.jobInfo.getJobOptions())

    #set DataType
    commoninfo["dataType"]='dst'
    
    return commoninfo


#get bossVer,eventNum,dataType,fileSize,name,eventType,expNum,
#resonance,runH,runL,status,streamId,description
#暂时先不转换.dst to .root
class DataAll(object):
    def __init__(self,dstfile):
        self.dstfile = dstfile
        #self.rootfile = rootfile

    
    def getAttributes(self):
        
        #store all attributes
        attributes = {}
        expRes = {}
        runIds = []
        
        #change the .dst file to .root file
        #rootfile = changeFormat(self.dstfile,self.rootfile)
        
        if getFileSize(self.dstfile)<5000:
            print "Content of this file is null:",self.dstfile
            return "error"
        else:
            attributes = getCommonInfo(self.dstfile)

        
            #get filesize by calling getFileSize function
            #get name by calling getLFN function
            attributes["fileSize"] = getFileSize(self.dstfile)
            attributes["LFN"] = getLFN(self.dstfile)
            
            #for .dst files of Data/All,their EventType are "all" 
            attributes["eventType"] = "all"
            attributes["PFN"] = self.dstfile

            #get runId from filename
            runId = splitLFN(attributes["LFN"],"all")

            #compare runid of rootfile with runid in filename
            if attributes["runId"] == runId:
                runIds.append(attributes["runId"])
                
                #get expNum and Resonance by calling getExpRes(runIds)
                expRes = getExpRes(runIds)

                if expRes != False:
                    attributes["round"] = expRes["round"]
                    attributes["resonance"] = expRes["resonance"]
                else:
                    print "Can't get expNum and resonance of this file"
                    return "error"
                    
            
                #set RunH=RunId and RunL=RunId
                attributes["runH"] = attributes["runId"]
                attributes["runL"] = attributes["runId"]

            else:
                print "runId of %s,in filename is %d,in rootfile is %d"%(self.dstfile,lfnInfo["runId"],attributes["runId"])
                return "error"

            #set values of attribute status,streamId,Description
            #and these values are null
            #-1 <=> value of status is null
            #-1 <=> value of streamId is null
            #null <=> value of Description is null
            attributes["status"] = -1
            attributes["streamId"] = 'stream0' 
            attributes["description"] = 'null'

            del attributes["runId"]
            del attributes["jobOptions"]
            return attributes


#get resonance,runL,runH,eventType,streamId,LFN from file name
#file name like resonance_eventType_streamId_runL_runH_*.dst
#get bossVer,runL,runH,eventNum by reading information from rootfile
class Others(object):
    def __init__(self,dstfile,rootfile):
        self.dstfile = dstfile
        self.rootfile = rootfile
        
    def getAttributes(self):
        #store all attributes
        attributes = {}
        expRes = {}
        lfnInfo = {}
        runIds = []

        #change the .dst file to .root file
        rootfile = changeFormat(self.dstfile,self.rootfile)
        if getFileSize(self.dstfile)<5000:
            print "Content of this file is null:",self.dstfile
            return "error"
        else:
            attributes = getCommonInfo(rootfile)
            
            #get filesize by calling getFileSize function
            #get lfn by calling getLFN function
            attributes["fileSize"] = getFileSize(self.dstfile)
            
            attributes["LFN"] = getLFN(self.dstfile)
           
            #get resonance,eventType,streamId,runL,runH in filename by calling splitLFN function
            lfnInfo = splitLFN(attributes["LFN"],"others")

            #if runL is equal to runH,this file only has one runId
            if lfnInfo["runL"] == lfnInfo["runH"]:
                #if runId in filename also is equal to runId in rootfile
                if attributes["runId"] == lfnInfo["runL"]:
                    runIds.append(attributes["runId"])
                    
                    attributes["runL"] = attributes["runId"]
                    attributes["runH"] = attributes["runId"]
                    
                    #get expNum and Resonance by calling getExpRes()
                    expRes = getExpRes(runIds)
                   
                    if expRes == False:
                        print "Can't get expNum and resonance of this file"
                        return "error"

                    attributes["round"] = expRes["round"]
                    attributes["description"] = "null"

                    #if resonance in filename is same as resonance that get from ExpSearch
                    if expRes["resonance"] == lfnInfo["resonance"]:
                        attributes["resonance"] = expRes["resonance"]
                    else:
                        print "Error %s:resonance in filename is %s,in ExpSearch is %s"%(self.dstfile,lfnInfo["resonance"],expRes["resonance"])
                        return "error"
                else:
                    print "Error %s:in the filename,runL = runH = %d,but runId in the root file is %d"%(self.dstfile,lfnInfo["runL"],attributes["runId"])
                    return "error"
            else:
                #this dst file has several runIds,get them from JobOptions by calling getRunIdList function
                result = getRunIdList(attributes["jobOptions"])
                if result is not None:
                    
                    runH = max(result["runIdList"])
                    runL = min(result["runIdList"])

                
                    if runL == lfnInfo["runL"]:
                        if runH == lfnInfo["runH"]:
                            attributes["runL"] = lfnInfo["runL"]
                            attributes["runH"] = lfnInfo["runH"]
                            
                            #get expNum and Resonance by calling getExpRes(runid)
                            expRes = getExpRes(result["runIdList"])
                            
                            if expRes== False:
                                print "Error:",this.dstfile
                                return "error"
                            
                            attributes["expNum"] = expRes["expNum"]
                            attributes["description"] = result["description"]
                            
                            if expRes["resonance"] == lfnInfo["resonance"]:
                                attributes["resonance"] = lfnInfo["resonance"]
                            else:
                                print "Error %s:resonance in filename is %s,in ExpSearch is %s"%(self.dstfile,lfnInfo["resonance"],expRes["resonance"])
                                return "error"

                        else:
                            print "Error %s:runH in filename is %d,in jobOptions is %d"%(self.dstfile,lfnInfo["runH"],runH)
                            return "error"
                    else:
                        print "Error %s:runL in filename is %d,in jobOptions is %d"%(self.dstfile,lfnInfo["runL"],runL)
                        return "error"
            
            #get streamId from filename
            attributes["streamId"] = lfnInfo["streamId"]

            #check eventType in filename
            evtType_exist = eventTypeCheck(lfnInfo["eventType"])
            
            if evtType_exist == True:
                attributes["eventType"] = lfnInfo["eventType"]
            else:
                print "Error %s:eventType %s in filename is not stored in AMGA"%(self.dstfile,lfnInfo["eventType"])
                return "error"

            #set values of attribute status
            #-1 <=> value of status is null
            attributes["status"] = -1
            
            del attributes["runId"]
            del attributes["jobOptions"]
            return attributes


if __name__=="__main__":
   client = FileCatalogClient()
   obj = DataAll("/bes3fs/offline/data/663p01/4260/dst/./121215/run_0029679_All_file002_SFO-2.dst")
   result = obj.getAttributes()
   import pprint
   pprint.pprint(result) 
   #num = getNum("exp2")
   #print "num:",num
   #runids = [8093,12000]
   #result = getExpRes(runids)
   #print str(result)
