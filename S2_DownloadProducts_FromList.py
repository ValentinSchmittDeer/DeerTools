#!/usr/local/bin/python3

import sys, os, time
from datetime import datetime,timedelta
import xml.etree.ElementTree as ET

#----------------------------------------------------------------------------------------------------
# Usage
#----------------------------------------------------------------------------------------------------
def Usage():
    print("""
                Download Sentinel 2 Products on ESA Scihub
This script is an alternative to download pre-choosen Sentinel-2 products.
He requests the Copernicus Hub (https://scihub.copernicus.eu) which is 
the official products deposit serveur. From a simple list where tiles 
are referenced by their name (from the military grid) and their 
acquisition date, it finds the right products on ESA SciHub and 
downloads it. This script can work on Windows and Unix system. 
    Thank the ESA API documentation which is well documented and OlivierHagolle
example which show me an example. By the way, his script is good way to run
seaching requests.
    An alternative of this script could be creating a cart on Copernicus Hub 
to send 'aria2 -M cart.meta4' command. In fact, I wrote this way to download 
sevral tiles from the same segment before merge them.

**************************************************************************
                             Tasks:
Python 3
- Find a known Download Package
       • Wget : https://www.gnu.org/software/wget/
       • cURL : https://curl.haxx.se/
       • Aria2 : https://aria2.github.io/manual/en/html/index.html

- Get Id and password account for the Copernicus Hub 
  from a txt file 'S2_DownloadProducts_IdScihub.txt' next to the script
        example: Jojo JojoPass 

- Read a list of tiles in a ASCII file, this is a kind of unheader CSV
        TileCode ; LevelOfProduct ; DateOfAcquisition ; OutputFolder
        T31TFL   ; L1C            ; 20181007          ; /Users/administrateur/Downloads
        "        ; L2A            ; 20180925          ; " 
        (" can be used to repeat the same information)

- Get tile centroides from ESA kml (hard link)

For each tiles
- Send an OpenSearch query to get the product ID
- Parse this query to find the right product
- Download the product to a zip file in the output folder

**************************************************************************
S2_DownloadProducts_FromList.py
Arg1: List of tiles

(The script less argument returns this help)
""")

#----------------------------------------------------------
# Check Download Package
#----------------------------------------------------------

dicoDP={'wget': 'wget --no-check-certificate --user={USERNAME} --password={PASSWORD} --output-document={OUTFOLDER}%s{FILENAME} "{URI_QUERY}"'% os.sep,
    'curloo': 'curl -u {USERNAME}:{PASSWORD} -g "{URI_QUERY}" > {OUTFOLDER}%s{FILENAME}'% os.sep,
    'aria2c': 'aria2c --http-user={USERNAME} --http-passwd={PASSWORD} -d {OUTFOLDER} -o {FILENAME} "{URI_QUERY}"'
    }

#----------------------------------------------------------
#Hard arguments
#----------------------------------------------------------
# URL of ESA military grid to find centroide
urlGrid="https://sentinel.esa.int/documents/247904/1955685/S2A_OPER_GIP_TILPAR_MPC__20151209T095117_V20150622T000000_21000101T000000_B00.kml"
# Login Scihub ID
nameIdFile="S2_DownloadProducts_IdScihub.txt"
#URL OpenSearch Scihub API
urlOS='https://scihub.copernicus.eu/apihub/search?q='

#----------------------------------------------------------------------------------------------------
# Hard commands
#----------------------------------------------------------------------------------------------------
def GetDP(dicDP):
    if not 'subprocess' in locals(): import subprocess
    i,maxI=0,len(dicDP)
    nameDP=list(dicDP.keys())[0]
    strDP=None
    while not strDP:
        nameDP=list(dicDP.keys())[i]
        try:
            code=subprocess.check_output([nameDP,'-h'])
            strDP=dicDP[nameDP]
        except OSError:
            i+=1
            if i>len(dicDP)-1:
                print('Known download package did not find')
                sys.exit()
    
    del code, dicDP,
    return strDP

def GetLoginId(pathFile):
    ficIn=open(pathFile)
    lstIn=ficIn.readlines()
    ficIn.close()
    
    if not len(lstIn)==1 : raise RuntimeError("Reading error of login ID :\n%s"% ''.join(lstIn))
    words=lstIn[0].split()
    lstId=(words[0].strip(),words[1].strip())
    
    return lstId

def ReadListTile(pathFile):
    fileIn=open(pathFile)
    tile,level,date,repOut=None,None,None,None
    list=[]
    for line in fileIn:
        clearLine=line.strip()
        words=[word.strip() for word in clearLine.split(';')]
        if not len(words)==4 : raise RuntimeError("Reading error of tile list : %s"% words)
        
        # Tile name
        if not words[0]=='"' : 
            if not words[0][0]=='T' and len(words[0])==6: raise RuntimeError("Reading error of tile list : level 0 = %s"% words[0])
            try:
                int(words[0][1:3])
            except ValueError:
                raise RuntimeError("Reading error of tile list : level 0 = %s"% words[0])
            tile=words[0][1:]
        # Level name
        if not words[1]=='"' : 
            level='S2MSI'+words[1][-2:]
            if not level=='S2MSI1C' and not level=='S2MSI2A':
                raise RuntimeError("Reading error of tile list : level 1 = %s"% words[1])
        # Date
        if not words[2]=='"' : 
            if not words[2][0]=='2' or not len(words[2])==8: raise RuntimeError("Reading error of tile list : level 2 = %s"% words[2])
            date=words[2]
        # Output directory
        if not words[3]=='"' : 
            if not os.path.isdir(words[3]): raise RuntimeError("Reading error of tile list : level 3 = %s"% words[3])
            repOut=words[3]
        
        if tile and level and date and repOut: 
            list.append((tile,level,date,repOut))
        else : 
            raise RuntimeError("Reading error of tile list : %s"% clearLine)
    
    fileIn.close()
    return list

def FindTileParam(urlKml,listTile):
    dicCenter=dict((name,None) for name in listTile)
    
    if not 'urllib' in locals(): import urllib.request
    fileKml=urllib.request.urlopen(urlKml).read()
    root = ET.fromstring(fileKml)
    noiseXml=root[0].tag.replace('Document','')
    
    for tile in root.iter(noiseXml+'Placemark'):
        nameTile=tile[0].text
        if not nameTile in listTile or dicCenter[nameTile]: continue
        centerStr=tile[4][1][0].text.split(',')[:2]
        center=[float(elem) for elem in centerStr]
        dicCenter[nameTile]=center
        
        if not None in dicCenter.values(): break
    
    del fileKml,root,centerStr,center
    
    if None in dicCenter.values(): raise RuntimeError("Tile didn't find :\n"+dicCenter)
    return dicCenter

#==========================================================
#main
#----------------------------------------------------------
if __name__ == "__main__":
    try:
    #----------------------------------------------------------------------------------------------------
    # Retrieval arguments
    #---------------------------------------------------------------------------------------------------- 
        print('')
        nbArg = len(sys.argv)
        if nbArg != 2: raise RuntimeError("incorrect number of arguments: %d instead of 1" % (nbArg-1))
        
        pathIn=sys.argv[1].strip()
        if not os.path.isfile(pathIn): raise RuntimeError("List is incorrect")
        
        #get Download Package
        formatDP=GetDP(dicoDP)
        del dicoDP
        #get login ID
        pathIdFile=os.path.join(os.path.dirname(sys.argv[0]),nameIdFile)
        if not os.path.exists(pathIdFile):
            print('--------------------\nLogin file does not find, let\'s create "IdScihub.txt" next to the script with ("ID Password") or')
            pathIdFile=input('Drop yours here (or return):')
            if not pathIdFile: raise RuntimeError("End")
        
        lstLogin=GetLoginId(pathIdFile.strip())
        print("------ Hello %s ------------"% lstLogin[0])
        
        #----------------------------------------------------------------------------------------------------
        # List reading
        #----------------------------------------------------------------------------------------------------
        lstFullTiles=ReadListTile(pathIn)
        
        print('-- %d Tiles to download -----------'% len(lstFullTiles))
        
        # more than 100 tiles
        lstLot=[]
        if len(lstFullTiles)/100:
            for i in range(int(len(lstFullTiles)/100)):
                lstLot.append(lstFullTiles[i*100:(i+1)*100])
        if len(lstFullTiles)%100:
            lstLot.append(lstFullTiles[(len(lstFullTiles)%100)*-1:])
        
        stat=0
        answQ=''
        #----------------------------------------------------------------------------------------------------
        # Get centroide
        #----------------------------------------------------------------------------------------------------
        dicCentroide=FindTileParam(urlGrid,[tile[0] for tile in lstFullTiles])
        
        #----------------------------------------------------------------------------------------------------
        # Loop
        #----------------------------------------------------------------------------------------------------
        pourcent=100.0/float(len(lstFullTiles))
        i=-1
        for lot in lstLot:
            for tilesStuff in lot:
                i+=1
                #----------------------------------------------------------------------------------------------------
                # OpenSearch query
                #----------------------------------------------------------------------------------------------------
                pathQuery=os.path.join(tilesStuff[3],'QueryResults_%s-%s.xml'% (tilesStuff[2],tilesStuff[0]))
                if os.path.exists(pathQuery): os.remove(pathQuery)
                urlCur=urlOS
                
                # BY centroide
                urlCur+='footprint:\\"Intersects(%s,%s)\\"'% (dicCentroide[tilesStuff[0]][1],dicCentroide[tilesStuff[0]][0])
                # BY inside square
                #urlCur+='footprint:\\"Intersects(POLYGON(({lonmin} {latmin},{lonmax} {latmin},{lonmax} {latmax},{lonmin} {latmax},{lonmin} {latmin})))\\" '.format(lonmin=dicCentroide[tilesStuff[0]][0]-0.3,lonmax=dicCentroide[tilesStuff[0]][0]+0.3,latmin=dicCentroide[tilesStuff[0]][1]-0.3,latmax=dicCentroide[tilesStuff[0]][1]+0.3)
                
                # DATE
                dateAcqui=datetime.strptime(tilesStuff[2], '%Y%m%d')
                dateBefore=dateAcqui-timedelta(days=1)
                dateAfter=dateAcqui+timedelta(days=1)
                urlCur+=' AND filename:S2* AND ingestiondate:[%s00:00:00.000Z TO %s00:00:00.000Z] AND producttype:%s &rows=100'% (dateBefore.strftime('%Y-%m-%dT'),dateAfter.strftime('%Y-%m-%dT'),tilesStuff[1])
                
                if formatDP.startswith('curl'): urlCur=urlCur.replace(' ','%20')
                cmd=formatDP.format(USERNAME=lstLogin[0], PASSWORD=lstLogin[1], OUTFOLDER=tilesStuff[3] ,FILENAME='QueryResults_%s-%s.xml'% (tilesStuff[2],tilesStuff[0]), URI_QUERY=urlCur)
                
                print("%s/%s-%.2f%%:  %s"% (time.strftime("%Y.%m.%d",time.localtime()),time.strftime("%H.%M.%S",time.localtime()),i*pourcent,cmd))
                returnCode=os.system(cmd)
                
                if returnCode or not os.path.exists(pathQuery) or not os.path.getsize(pathQuery):
                    print("-- Query hurdle : %s"% pathQuery)
                    continue
                
                #----------------------------------------------------------------------------------------------------
                # Query parse
                #----------------------------------------------------------------------------------------------------
                title,ident,urlOD=None,None,None
                
                tree=ET.parse(pathQuery)
                root=tree.getroot()
                noiseXml=root.tag.replace('feed','')
                
                lstAnsw=root.findall(noiseXml+'entry')
                answQ+='Tile %s-%s : %d answer(s)\n'% (tilesStuff[2],tilesStuff[0],len(lstAnsw))
                for entry in lstAnsw:
                    if not entry.find(noiseXml+'title').text.startswith('S2'): continue
                    title=entry.find(noiseXml+'title').text
                    wordsTitle=title.split('_')
                    
                    #match query answer (Tile)
                    if not wordsTitle[5][1:]==tilesStuff[0] : continue
                    #match query answer (Date)
                    if not wordsTitle[2][:8]==tilesStuff[2] : continue
                    
                    ident=entry.find(noiseXml+'id').text
                    urlOD=entry.find(noiseXml+'link').attrib['href']
                
                if title is None or ident is None or urlOD is None: 
                    print("-- Tile did not find : %s"% pathIn)
                    continue
                #Unix special character
                if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
                    urlOD=urlOD.replace("$value","\\$value")
                
                #----------------------------------------------------------------------------------------------------
                # Download
                #----------------------------------------------------------------------------------------------------
                #part 1 command writing : downloader
                pathOut=os.path.join(tilesStuff[3],'%s.zip'% title.replace('.SAFE',''))
                if os.path.exists(pathOut): raise RuntimeError("Product already exists : %s"% pathOut)
                
                cmd=formatDP.format(USERNAME=lstLogin[0], PASSWORD=lstLogin[1], OUTFOLDER=tilesStuff[3] ,FILENAME='%s.zip'% title.replace('.SAFE',''), URI_QUERY=urlOD)
                
                print("%s/%s-%.2f%%:  %s"% (time.strftime("%Y.%m.%d",time.localtime()),time.strftime("%H.%M.%S",time.localtime()),i*pourcent,cmd))
                returnCode=os.system(cmd)
                
                if returnCode : continue
                if os.path.exists(pathQuery) : os.remove(pathQuery)
                if os.path.exists(pathOut) and os.path.getsize(pathOut): stat+=1
                
        #----------------------------------------------------------------------------------------------------
        # Ending
        #----------------------------------------------------------------------------------------------------
        print('\n\n%d Tiles to download-------------'% len(lstFullTiles))
        print('%d Tiles done--------------------'% stat)
        print(answQ)
        
        
    #----------------------------------------------------------------------------------------------------
    # Exceptions
    #----------------------------------------------------------------------------------------------------
    except RuntimeError as msg:
        print("\nERROR - ", msg)
        Usage()
        
