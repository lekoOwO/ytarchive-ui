@echo off

del "%cd%\ytarchive.py" >NUL 2>NUL
echo Downloading ytarchive...
bitsadmin.exe /reset >NUL
bitsadmin.exe /create "ytarchive" >NUL
bitsadmin.exe /setpriority "ytarchive" foreground >NUL
bitsadmin.exe /transfer "ytarchive" "https://raw.githubusercontent.com/Kethsar/ytarchive/master/ytarchive.py" "%cd%\ytarchive.py" >NUL 
bitsadmin.exe /complete "ytarchive" >NUL
echo Finished.
echo Starting service...
waitress-serve --port=30004 api:api