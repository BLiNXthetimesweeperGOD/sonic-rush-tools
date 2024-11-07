# Sonic Rush tools
Tools for the Sonic Rush games that I wrote in Python. These are currently only going to work on Windows!

Currently, only the map ripper is done. The following are required to use it:
- pillow (for the image processing functionality)
- ndspy (for the Nintendo DS ROM and NARC package handling)

So do this:

pip install pillow

pip install ndspy


DSDecmp has been included for convenience (it's used for the decompression, as I couldn't get ndspy's decompression functions to work here). It uses the MIT license:

https://web.archive.org/web/20141223223529/https://code.google.com/p/dsdecmp/

Before you run this:

Epilepsy warning. Subprocess is used to run DSDecmp on every single file unpacked from the NARC packages.

How to use:

- Run the script
- Select your ROM (it gets the files out of it for you)
- Enter the zone/map name (z11, z12, m13, zt1, z1boss, exboss...)
- Wait for the extraction to complete (it should take about 5 seconds or so)
- Wait for the conversion to complete (when done, the map is saved in the Maps folder)
