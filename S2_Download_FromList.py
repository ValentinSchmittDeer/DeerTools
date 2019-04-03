#!/usr/local/bin/python3
import sys, os
from time import strftime,strptime,localtime
import xml.etree.ElementTree as ET
import argparse
from pprint import pprint

#----------------------------------------------------------------------------------------------------
# Usage
#----------------------------------------------------------------------------------------------------
__version__=2.3
parser = argparse.ArgumentParser(description='''                Download Sentinel 2 Products on ESA Scihub
    I use to download Sentinel 2 data by script to get whole products or 
just few bands. OlivierHagolle's script is an alternative for search query
and download its.
    This script allow to download pre-choosen Sentinel-2 products.
He requests the Copernicus Hub (https://scihub.copernicus.eu) which is 
the official products deposit serveur. From a simple list where tiles 
are referenced by their name (from the military grid) and their 
sensing date, it finds the right products on ESA SciHub and 
downloads it. it can work on Windows and Unix system. It is also able to read 
a '.meta4' file and download content.
    Thank the ESA API documentation which is well documented and OlivierHagolle
example which show me an example. 
    An alternative of this script could be creating a cart on Copernicus Hub 
to send 'aria2 -M cart.meta4' command.

**************************************************************************
                             Tasks:
Python 3 - Version %.1f
- Search on computer a known Download Package through this list:
       • Wget : https://www.gnu.org/software/wget/
       • cURL : https://curl.haxx.se/
       • Aria2 : https://aria2.github.io/manual/en/html/index.html
- Get Id and password account for the Copernicus Hub 
  from a txt file 'S2_DownloadProducts_IdScihub.txt' next to the script
        example: JojoId JojoPass 
- Read a list of tiles in a ASCII file which is a kind of unheader CSV
        TileCode ; SensingDate       ; LevelOfProduct ; Bands                         ; OutputFolder
        T31TFL   ; 20181007          ; L1C            ; prod (Whole products)         ; /Users/administrateur/Downloads
        "        ; 20180925          ; L2A            ; B02B03B04 (seclected bands)   ; "
        "        ; 20180925          ; L2A            ; B05-B07 (band 5 to band 7)    ; "
            (" can be used to repeat the same information, # for comments)
    OR
  Read a '.meta4' file (then OpenSearchquery avoided, download in the current directory)

- Get tile centroides from ESA kml (hard link)
For each tiles
- Get the product ID by OpenSearch query (On Scihub, tiles are referenced by Id name)
- Download the full product to a zip file
    OR
  Download the product Xml file, then bands

**************************************************************************

'''% __version__,
formatter_class=argparse.RawDescriptionHelpFormatter)
#----------------------------------------------------------
# List of Download Package
#----------------------------------------------------------
dicoDP={'wget': 'wget --no-check-certificate --user={USERNAME} --password={PASSWORD} --output-document={OUTFOLDER}%s{FILENAME} "{URI_QUERY}"'% os.sep,
    'curl': 'curl -u {USERNAME}:{PASSWORD} -g "{URI_QUERY}" > {OUTFOLDER}%s{FILENAME}'% os.sep,
    'aria2c': 'aria2c --http-user={USERNAME} --http-passwd={PASSWORD} -d {OUTFOLDER} -o {FILENAME} "{URI_QUERY}"'
    }
#----------------------------------------------------------
#Hard arguments
#----------------------------------------------------------
# URL Kml military grid to find centroide
urlGrid=["https://sentinel.esa.int/documents/247904/1955685/S2A_OPER_GIP_TILPAR_MPC__20151209T095117_V20150622T000000_21000101T000000_B00.kml"]
urlGrid+=['https://hls.gsfc.nasa.gov/wp-content/uploads/2016/03/S2A_OPER_GIP_TILPAR_MPC__20151209T095117_V20150622T000000_21000101T000000_B00.kml']
# Login Scihub ID
nameIdFile="S2_Download_IdScihub.txt"
# URL OpenSearch Scihub API
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
    
    if not len(lstIn)==1 : raise RuntimeError("Login ID reading error:\n%s"% ''.join(lstIn))
    words=lstIn[0].split()
    lstId=(words[0].strip(),words[1].strip())
    
    return lstId

def BandParse(text):
    strBands=text.strip(' B').split('B')
    lst=[]
    for i in range(len(strBands)):
        elem=strBands[i]
        try:
            lst.append(int(elem))
        except ValueError:
            if not elem[-1]=='-' : raise RuntimeError("Bands error: %s"% text)
            lst+=[j for j in range(int(elem[:-1]),int(strBands[i+1]))]
    if max(lst)>12 : raise RuntimeError("Bands list out of S2 range : %s"% '-'.join([str(elem) for elem in lst]))
    
    return lst

def ReadListTile(pathFile):
    fileIn=open(pathFile)
    tile,date,level,bands,repOut=None,None,None,None,None
    list=[]
    for line in fileIn:
        clearLine=line.strip()
        if clearLine.startswith('#'): continue
        words=[word.strip() for word in clearLine.split(';')]
        if not len(words)==5 : raise RuntimeError("Tile list reading error: %s"% words)
        
        # Tile name
        if not words[0]=='"' : 
            val=words[0]
            if not val[0]=='T' and len(val)==6: raise RuntimeError("Tile list reading error: #0 = %s"% val)
            try:
                int(val[1:3])
            except ValueError:
                raise RuntimeError("Tile list reading error: #0 = %s"% val)
            tile=val[1:]
        # Date
        if not words[1]=='"' : 
            val=words[1]
            if not val[:2]=='20' or not len(val)==8: raise RuntimeError("Tile list reading error: #1 = %s"% val)
            try:
                date=strptime(val, '%Y%m%d')
            except ValueError:
                raise RuntimeError("Tile list reading error: #1 = %s"% val)
        # Level name
        if not words[2]=='"' : 
            val=words[2]
            level='S2MSI'+val[-2:]
            if not level=='S2MSI1C' and not level=='S2MSI2A':
                raise RuntimeError("Tile list reading error: #2 = %s"% val)
        # Bands
        if not words[3]=='"' : 
            val=words[3]
            if val=='prod':
                bands="prod"
            else:
                bands=BandParse(val)
        # Output directory
        if not words[4]=='"' : 
            val=words[4]
            if not os.path.isdir(val): raise RuntimeError("Tile list reading error: #4 = %s"% val)
            repOut=val
        
        #final check
        if tile and date and level and bands and repOut: 
            list.append([tile,date,level,bands,repOut])
        else : 
            raise RuntimeError("Tile list reading error: %s"% clearLine)
    
    fileIn.close()
    return list

def ReadMeta4(pathFile,bands):
    tree=ET.parse(pathFile)
    root=tree.getroot()
    noise=root.tag.replace('}metalink','}')
    
    lst=[]
    for prod in root:
        title=prod.attrib['name'].replace('.zip','')
        ident=prod.find(noise+'hash').text
        # server change dhus TO apihub 
        urlOD=prod.find(noise+'url').text.replace('dhus','apihub')
        
        
        words=title.split('_')
        tile=words[5][1:]
        date=words[2][:8]
        level='S2MSI'+words[1][-2:]
        repOut=os.curdir
        
        lst.append([tile,date,level,bands,repOut,title,ident,urlOD])
    return lst

def ParseKml(lstUrlKml,listTile):
    dicCenter=dict((name,None) for name in listTile)
    
    if not 'urllib' in locals(): import urllib.request
    fileKml,k='',0
    while not fileKml:
        try:
            fileKml=urllib.request.urlopen(lstUrlKml[k]).read()
        except urllib.error.URLError or ValueError:
            k+=1
            if k>len(lstUrlKml)-1: raise RuntimeError("ESA military grid kml file did not find")
    
    root = ET.fromstring(fileKml)
    noise=root.tag.split('}')[0]+'}'
    
    for tile in root.iter(noise+'Placemark'):
        nameTile=tile[0].text
        if not nameTile in listTile or dicCenter[nameTile]: continue
        centerStr=tile[4][1][0].text.split(',')[:2]
        center=[float(elem) for elem in centerStr]
        dicCenter[nameTile]=center
        
        if not None in dicCenter.values(): break
    
    del fileKml,root,centerStr,center
    
    if None in dicCenter.values(): raise RuntimeError("Tile did not find :"+dicCenter)
    return dicCenter

def CreateOSQuery(url,name,date,level,dicoCenter):
    # BY centroide
    url+='footprint:\\"Intersects(%s,%s)\\"'% (dicoCenter[name][1],dicoCenter[name][0])    
    # DATE & Level
    url+=' AND filename:S2* AND beginposition:[%s00:00:00.000Z TO %s23:59:00.000Z] AND producttype:%s'% (strftime('%Y-%m-%dT',date),strftime('%Y-%m-%dT',date),level)
    
    if formatDP.startswith('curl'): url=url.replace(' ','%20')
    
    return url

def ParseOSQuery(pathFile,nameTile,date):
    title,id,url=None,None,None
    tree=ET.parse(pathFile)
    root=tree.getroot()
    noise=root.tag.split('}')[0]+'}'
    
    for entry in root.findall(noise+'entry'):
        if not entry.find(noise+'title').text.startswith('S2'): continue
        title=entry.find(noise+'title').text
        wordsTitle=title.split('_')
        
        #match query answer (Tile)
        if not wordsTitle[5][1:]==nameTile : continue
        #match query answer (Date)
        if not wordsTitle[2][:8]==strftime('%Y%m%d',date) : continue
        
        id=entry.find(noise+'id').text
        url=entry.find(noise+'link').attrib['href']
    
    return title,id,url

def ReadS2XML(path,level):
    tree=ET.parse(path)
    root=tree.getroot()
    
    if level=='S2MSI1C':
        print('1C')
        dico=dict([(elem.text.split('_')[-1],elem.text+'.jp2') for elem in root.iter('IMAGE_FILE')])
    elif level=='S2MSI2A':
        print('L2A')
        dico={}
        for elem in root.iter('IMAGE_FILE'):
            key=elem.text.split('_')[-2]
            if key in dico: continue
            dico[key]=elem.text+'.jp2'
    
    return dico

def PrintCmd(cmdCur,percent=0.0):
    print("--%s-%.2f%%: %s"% (strftime("%Y.%m.%d-%H:%M:%S",localtime()),percent,cmdCur))
 
#==========================================================
#main
#----------------------------------------------------------
if __name__ == "__main__":
    try:
        #----------------------------------------------------------------------------------------------------
        # Retrieval arguments
        #----------------------------------------------------------------------------------------------------
        parser.add_argument('pathIn',help='Tile list OR products.meta4 (from https://scihub.copernicus.eu)')
        
        parser.add_argument('-bands',default='B02B03B04',help='Set .meta4 process downloading bands (default B02B03B04)')
        
        args = parser.parse_args()
        
        #----------------------------------------------------------------------------------------------------
        #Unix special character
        #----------------------------------------------------------------------------------------------------
        if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
            specChar="\\$value"
        else:
            specChar="$value"
        
        #----------------------------------------------------------------------------------------------------
        #get Download Package
        #----------------------------------------------------------------------------------------------------
        formatDP=GetDP(dicoDP)
        del dicoDP
        
        #----------------------------------------------------------------------------------------------------
        #get login ID
        #----------------------------------------------------------------------------------------------------
        pathIdFile=os.path.join(os.path.dirname(sys.argv[0]),nameIdFile)
        if not os.path.exists(pathIdFile):
            print('--------------------\nLogin file does not find, fill "IdScihub.txt" next to the script with ("ID Password") or')
            pathIdFile=input('Drop yours here (or return):')
            if not pathIdFile: raise RuntimeError("End")
        
        lstLogin=GetLoginId(pathIdFile.strip())
        if lstLogin[0]=='Name': raise RuntimeError('Login file does not find, fill "IdScihub.txt" next to the script with ("ID Password")')
        print("\n------ Hello %s ---------"% lstLogin[0])
        
        #----------------------------------------------------------------------------------------------------
        # List reading
        #----------------------------------------------------------------------------------------------------
        formIn=args.pathIn.split('.')[-1]
        if formIn=='txt':
            lstTiles=ReadListTile(args.pathIn)
        elif formIn=='meta4':
            lstTiles=ReadMeta4(args.pathIn,args.band)
        else:
            raise RuntimeError("Unknown list format : %s"% formIn)
        print('-- %d Tiles -----------'% len(lstTiles))
        lstTilesUrlLess=[elem for elem in lstTiles if len(elem)<8]
        
        #----------------------------------------------------------------------------------------------------
        # Get centroide
        #----------------------------------------------------------------------------------------------------
        if lstTilesUrlLess:
            dicCentroide=ParseKml(urlGrid,[tile[0] for tile in lstTiles])
        
        #----------------------------------------------------------------------------------------------------
        # Query Loop
        #----------------------------------------------------------------------------------------------------
        i=-1
        for tilesStuff in lstTilesUrlLess:
            i+=1
            [nameTile,dateTile,levelTile,bandsTile,outTile]=tilesStuff
            #----------------------------------------------------------------------------------------------------
            # OpenSearch query
            #----------------------------------------------------------------------------------------------------
            nameQuery='QueryResults_%s-%s.xml'% (strftime('%Y%m%d',dateTile),nameTile)
            pathQuery=os.path.join(outTile,nameQuery)
            if os.path.exists(pathQuery): os.remove(pathQuery)
            
            urlCur=CreateOSQuery(urlOS,nameTile,dateTile,levelTile,dicCentroide)
            
            cmd=formatDP.format(USERNAME=lstLogin[0], PASSWORD=lstLogin[1], OUTFOLDER=outTile ,FILENAME=nameQuery, URI_QUERY=urlCur)
            PrintCmd(cmd)
            returnCode=os.system(cmd)
            
            if returnCode or not os.path.exists(pathQuery) or not os.path.getsize(pathQuery):
                print("--Query empty : %s"% pathQuery)
                continue
            
            #----------------------------------------------------------------------------------------------------
            # Query parse
            #----------------------------------------------------------------------------------------------------
            title,ident,urlOD=ParseOSQuery(pathQuery,nameTile,dateTile)
            
            if title is None or ident is None or urlOD is None: 
                print("--Tile did not find : %s-%s"% (strftime('%Y%m%d',dateTile),nameTile))
                continue
            else:
                lstTiles[i]+=[title,ident,urlOD]
                if os.path.exists(pathQuery) : os.remove(pathQuery)
        
        #----------------------------------------------------------------------------------------------------
        # Download loop
        #----------------------------------------------------------------------------------------------------
        pourcent=100.0/float(len([elem for elem in lstTiles if len(elem)==8]))
        stat=0
        i=-1
        for tilesStuff in lstTiles:
            if not len(tilesStuff)==8 : continue
            [nameTile,dateTile,levelTile,bandsTile,outTile,titleTile,identTile,urlODTile]=tilesStuff
            
            #Download whole product
            if bandsTile=='prod':
                if os.path.exists(os.path.join(outTile,titleTile+'.zip')): 
                    print("Product already exists : %s"% outTile)
                    continue
                
                cmd=formatDP.format(USERNAME=lstLogin[0], PASSWORD=lstLogin[1], OUTFOLDER=outTile ,FILENAME=titleTile+'.zip', URI_QUERY=urlODTile.replace("$value",specChar))
                PrintCmd(cmd,i*pourcent)
                returnCode=os.system(cmd)
                
                if returnCode : 
                    print("--Download issue")
                    continue
                elif os.path.exists(os.path.join(outTile,titleTile+'.zip')) and os.path.getsize(os.path.join(outTile,titleTile+'.zip')): 
                    stat+=1
                    i+=1
            
            #Download bands 
            else:
                repOut=os.path.join(outTile,'%s'% titleTile)
                if os.path.exists(repOut): 
                    print("Product already exists : %s"% outTile)
                    continue
                os.mkdir(repOut)
                
                #Get Xml file of product
                xmlName='MTD_MSIL%s.xml'% levelTile[-2:]
                urlXml='/'.join( urlODTile.split('/')[:-1]+["Nodes('%s.SAFE')"% titleTile]+["Nodes('%s')"% xmlName]+[specChar] )
                
                cmd=formatDP.format(USERNAME=lstLogin[0], PASSWORD=lstLogin[1], OUTFOLDER=repOut ,FILENAME=xmlName, URI_QUERY=urlXml)
                PrintCmd(cmd,i*pourcent)
                returnCode=os.system(cmd)
                
                if returnCode : 
                    print("--Download issue : Xml file")
                    continue
                else:
                    dicoRelatPath=ReadS2XML(os.path.join(repOut,xmlName),levelTile)
                    
                
                #Get bands
                returnCode=0
                for bandNum in bandsTile:
                    relatPathBand=dicoRelatPath['B%02i'% bandNum]
                    nameBandOut=titleTile+'_B%02i.jp2'% bandNum
                    
                    urlBand='/'.join( urlODTile.split('/')[:-1]+["Nodes('%s.SAFE')"% titleTile]+["Nodes('%s')"% elem for elem in relatPathBand.split('/')]+[specChar] )
                    
                    cmd=formatDP.format(USERNAME=lstLogin[0], PASSWORD=lstLogin[1], OUTFOLDER=repOut ,FILENAME=nameBandOut, URI_QUERY=urlBand)
                    PrintCmd(cmd,i*pourcent)
                    returnCodeCur=os.system(cmd)
                    
                    if returnCodeCur: 
                        print("--Download issue : Bands %s"% nameBandOut)
                        returnCode+=1
                
                if not returnCode:
                    stat+=1
                    i+=1
            
        #----------------------------------------------------------------------------------------------------
        # End
        #----------------------------------------------------------------------------------------------------
        print('%d/%d Tiles correctly done---------------'% (stat,len(lstTiles)))
    
    
    #----------------------------------------------------------------------------------------------------
    # Exceptions
    #----------------------------------------------------------------------------------------------------
    except RuntimeError as msg:
        print("\nERROR - ", msg)
        
