#DeerTools

## S2_Download
### Download Sentinel 2 Products on ESA Scihub.
I use to download Sentinel 2 data by script to get whole products or just few bands. OlivierHagolle's script is an alternative for search query and download its.
This script allow to download pre-choosen Sentinel-2 products. He requests the Copernicus Hub (https://scihub.copernicus.eu) which is the official products deposit serveur. From a simple list where tiles are referenced by their name (from the military grid) and their acquisition date, it finds the right products on ESA SciHub and downloads it. it can work on Windows and Unix system. 

Thank the ESA API documentation which is well documented and OlivierHagolle example which show me an example. 

An alternative of this script could be creating a cart on Copernicus Hub to send 'aria2 -M cart.meta4' command.
### Tasks:
Python 3
- Search on computer a known Download Package. 
- Get Id and password account for the Copernicus Hub 
- Read a list of tiles in a ASCII file which is a kind of unheader CSV

`          TileCode ; DateOfAcquisition ; LevelOfProduct ; Bands                         ; OutputFolder`

`          T31TFL   ; 20181007          ; L1C            ; prod (Whole products)         ; /Users/administrateur/Downloads`

`          "        ; 20180925          ; L2A            ; B02B03B04 (seclected bands)   ; "`

`          "        ; 20180925          ; L2A            ; B05-B07 (band 5 to band 7)    ; "`

`(" can be used to repeat the same information)

- Get tile centroides from ESA kml (hard link)
For each tiles
- Send an OpenSearch query to get the product ID (On Scihub, tiles are referenced by Id name)
- Parse this query to find the right product
- Download the product to a zip file in the output folder
    OR
- Download the Xml file of the product, then download bands
