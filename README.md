11## S2_Download
### Download Sentinel 2 Products on ESA Scihub.
I have developed a script called “S2_Download_fromList” to download Sentinel-2 data, allowing access to either the whole product or limited to a few bands. The “S2_Download” script extracts pre-chosen Sentinel-2 images from the [Copernicus Hub](https://scihub.copernicus.eu/dhus/#/home), the ESA official products server. Tiles are listed first by their name (from the military grid) and their sensing date, then it finds the right products on the ESA SciHub, where tiles are referenced by an ID name, and proceed with the downloading. The “S2_Download” can work indifferently on Windows and Unix systems.It is also able to read a '.meta4' file and download content.

I have written this tool thanks to CESBIO Olivier Hagolle’s script which provided me with an example. He has developed script to download elements by queries (area, date, cloudy level ...). This is convenient way, but tiles are not exactly chosen.

Due recognition is also given to the well documented ESA API documentation.

An alternative to this script could consist of creating a cart on Copernicus Hub to send the  `aria2 -M cart.meta4` command

### Tasks:
Python 3 - Script version 2.1 - Script less argument returns this help
- Search on computer a known Download Package. 
- Get Id and password account for the Copernicus Hub 
- Read a list of tiles in a ASCII file which is a kind of unheader CSV

`          TileCode ; SensingDate ; LevelOfProduct ; Bands                         ; OutputFolder`

`          T31TFL   ; 20181007          ; L1C            ; prod (Whole products)         ; /Users/administrateur/Downloads`

`          "        ; 20180925          ; L2A            ; B02B03B04 (seclected bands)   ; "`

`          "        ; 20180925          ; L2A            ; B05-B07 (band 5 to band 7)    ; "`

*(" can be used to repeat the same information, # to comment)*

  OR  read a ['.meta4'](http://www.rsgis.info/wp-content/uploads/2015/12/sentinel_03-2.jpg) file (then OpenSearch query avoided, band selection as hard arguments, download in the current directory)

- Get tile centroides from ESA kml (hard link)

For each tiles

* Send an OpenSearch query to get the product ID (On Scihub, tiles are referenced by Id name)
* Parse this query to find the right product
* Download the product to a zip file in the output folder
    
    *OR*
    
* Download the Xml file of the product, then download bands

## Author

* **Valentin Schmitt** - [ValentinSchmittDeer](https://github.com/ValentinSchmittDeer)
