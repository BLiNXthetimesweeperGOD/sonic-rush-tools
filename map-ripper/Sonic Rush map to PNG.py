import os
from PIL import Image
import ndspy.rom
import ndspy.narc
import os
import subprocess

import tkinter as tk #Used to kill the extra tkinter window
from tkinter import filedialog
root = tk.Tk()#Create a root window
root.withdraw()#Hide the root window
file = filedialog.askopenfilename()
root.destroy()#Destroy the root window

def decompress(inputFile, outputFile=None):
    dsdecmp = 'DSDecmp.exe'
    command = [dsdecmp, inputFile]
    if outputFile:
        command.append(outputFile)

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Decompression successful: {result.stdout.decode()}")
    except subprocess.CalledProcessError as e:
        print(f"Error during decompression: {e.stderr.decode()}")
    
def extractNarc(narcData, outputDir):
    narc = ndspy.narc.NARC(narcData)
    names = narc.filenames
    for i, file in enumerate(narc.files):
        filePath = os.path.join(outputDir, f"{names[i]}")
        with open(filePath, 'w+b') as f:
            f.write(file)
        decompress(filePath)

def RGB555ToRGB(RGB555):
    red = (RGB555 & 0x1F) << 3
    green = ((RGB555 >> 5) & 0x1F) << 3
    blue = ((RGB555 >> 10) & 0x1F) << 3
    return (red, green, blue)

def readRGB555Palette(paletteData):
    colors = []
    for i in range(0, len(paletteData), 2):
        RGB555 = int.from_bytes(paletteData[i:i+2], byteorder='little')
        rgb = RGB555ToRGB(RGB555)
        colors.append(rgb)
    return colors

def saveTiles(filePath, paletteData, outputDir='tiles', tileImageFile='all_tiles.png', tileOffsetsFile='tile_offsets.txt'):
    with open(filePath, 'rb') as f:
        tileData = f.read()

    palette = readRGB555Palette(paletteData)
    os.makedirs(outputDir, exist_ok=True)

    tileSize = 8
    imageSize = 256
    numTiles = len(tileData) // (tileSize * tileSize)
    tilesPerRow = imageSize // tileSize
    tileImage = Image.new('RGB', (imageSize, imageSize))

    with open(os.path.join(outputDir, tileOffsetsFile), 'w') as offsets_file:
        for tileIndex in range(numTiles):
            tile = Image.new('RGB', (tileSize, tileSize))
            for y in range(tileSize):
                for x in range(tileSize):
                    pixelIndex = tileIndex * tileSize * tileSize + y * tileSize + x
                    colorIndex = tileData[pixelIndex]
                    tile.putpixel((x, y), palette[colorIndex])
            tile_x = (tileIndex % tilesPerRow) * tileSize
            tile_y = (tileIndex // tilesPerRow) * tileSize
            tileImage.paste(tile, (tile_x, tile_y))
            offsets_file.write(f'Tile {tileIndex}: ({tile_x}, {tile_y})\n')

    tileImage.save(os.path.join(outputDir, tileImageFile))

def applyFlip(tile, flipType):
    if flipType == 1:  #Flip horizontally
        return tile.transpose(Image.FLIP_LEFT_RIGHT)
    elif flipType == 2:  #Flip vertically
        return tile.transpose(Image.FLIP_TOP_BOTTOM)
    elif flipType == 3:  #Flip horizontally and vertically
        return tile.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    return tile

def constructBlocks(tileFilePath, indexFilePath, paletteData, outputDir='blocks'):
    with open(tileFilePath, 'rb') as f:
        tileData = f.read()

    with open(indexFilePath, 'rb') as f:
        indexData = f.read()

    palette = readRGB555Palette(paletteData)
    os.makedirs(outputDir, exist_ok=True)

    tileSize = 8
    blockSize = 64  #Blocks are 64x64 pixels. They're made up of the 8x8 pixel tiles that were extracted earlier.
    tilesPerBlock = blockSize // tileSize
    numTiles = len(tileData) // (tileSize * tileSize)
    numBlocks = len(indexData) // (tilesPerBlock * tilesPerBlock * 2)  #Each index is a 16-bit value

    for blockIndex in range(numBlocks):
        block = Image.new('RGB', (blockSize, blockSize))
        for by in range(tilesPerBlock):  #8 tiles vertically
            for bx in range(tilesPerBlock):  #8 tiles horizontally
                tileIndexOffset = (blockIndex * tilesPerBlock * tilesPerBlock + by * tilesPerBlock + bx) * 2
                tileIndex = int.from_bytes(indexData[tileIndexOffset:tileIndexOffset+2], byteorder='little')
                flipType = tileIndex >> 10  #Extract the flip bits
                if flipType > 0: #0 means both bits aren't set, so no flip happens. In that case, just use the index with no flip.
                    tileIndex = int(f"{tileIndex:016b}"[6:16],2)
                if tileIndex < numTiles:
                    tile = Image.new('RGB', (tileSize, tileSize))
                    for ty in range(tileSize):
                        for tx in range(tileSize):
                            pixelIndex = tileIndex * tileSize * tileSize + ty * tileSize + tx
                            colorIndex = tileData[pixelIndex]
                            tile.putpixel((tx, ty), palette[colorIndex])
                    tile = applyFlip(tile, flipType)
                    block.paste(tile, (bx * tileSize, by * tileSize))
        
        block.save(os.path.join(outputDir, f'block_{blockIndex}.png'))

def constructMap(blockFilePath, blockDataPath, outputFilePath):
    with open(blockDataPath, 'rb') as f:
        blockData = f.read()

    mapWidth = int.from_bytes(blockData[0:2], byteorder='little')
    mapHeight = int.from_bytes(blockData[2:4], byteorder='little')
    blockIndices = blockData[4:]

    blockSize = 64
    mapImage = Image.new('RGB', (mapWidth * blockSize, mapHeight * blockSize))

    for y in range(mapHeight):
        for x in range(mapWidth):
            blockIndex = int.from_bytes(blockIndices[(y * mapWidth + x) * 2:(y * mapWidth + x) * 2 + 2], byteorder='little')
            blockPath = os.path.join(blockFilePath, f'block_{blockIndex}.png')
            if os.path.exists(blockPath):
                blockImage = Image.open(blockPath)
                mapImage.paste(blockImage, (x * blockSize, y * blockSize))

    mapImage.save(outputFilePath)

mapname = input("Enter the name of the map you want to see get extracted. Example: z11, z12, m13, z21...\n")

#Load the ROM
rom = ndspy.rom.NintendoDSRom.fromFile(file)

romName = rom.name #Used to get the mode. The mode determines how to grab the maps, as the filesystem layout can be a bit different from game to game.

if romName == b'SONIC RUSH':
    print("Sonic Rush detected")
    mode = "R"
if romName == b'SONICRUSHADV':
    print("Sonic Rush Adventure detected")
    mode = "A"
if romName == b'SONICCOLORS':
    print("Sonic Colors detected")
    mode = "C"

# Create output directory
outputDir = os.getcwd()+'/NARCFiles/'
os.makedirs(outputDir, exist_ok=True)

# Scan for NARC archives and extract them
for fileID, fileData in enumerate(rom.files):
    if fileData[:4] == b'NARC':
        name = str(rom.filenames[fileID]).split(".")[0]
        if mapname in name:
            narcOutputDir = os.path.join(outputDir, f"{name}")
            os.makedirs(narcOutputDir, exist_ok=True)
            extractNarc(fileData, narcOutputDir)

print("Extraction complete! Starting map conversion...")


basePath = os.getcwd()+"/NARCFiles"
mapOutputPath = os.getcwd()+"/Maps/"
if not os.path.exists(mapOutputPath):
    os.makedirs(mapOutputPath)
if mode == "R":
    tileFilePath = f'{basePath}/narc/{mapname}_map/{mapname}.ch'
    indexFilePath = f'{basePath}/narc/{mapname}_map/{mapname}.bk'
    paletteFile = f'{basePath}/narc/{mapname}_map/{mapname}.pl'
    a = f'{basePath}/narc/{mapname}_map/{mapname}_a.mp'
    b = f'{basePath}/narc/{mapname}_map/{mapname}_b.mp'
    a_out = f'{mapOutputPath}{mapname}_a.png'
    b_out = f'{mapOutputPath}{mapname}_b.png'
else:
    tileFilePath = f'{basePath}/narc/{mapname}_raw/{mapname}.ch'
    indexFilePath = f'{basePath}/narc/{mapname}_raw/{mapname}.bk'
    paletteFile = f'{basePath}/narc/{mapname}_map/{mapname}.pl'
    a = f'{basePath}/narc/{mapname}_map/{mapname}_a.mp'
    b = f'{basePath}/narc/{mapname}_map/{mapname}_b.mp'
    a_out = f'{mapOutputPath}{mapname}_a.png'
    b_out = f'{mapOutputPath}{mapname}_b.png'
with open(paletteFile, "rb") as f:
    paletteData = f.read(0x200)
saveTiles(tileFilePath, paletteData)
constructBlocks(tileFilePath, indexFilePath, paletteData)
constructMap('blocks', a, a_out)
constructMap('blocks', b, b_out)

print("The conversion is finished! Check the Maps folder for your converted map!")
