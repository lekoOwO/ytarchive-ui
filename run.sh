#!/bin/sh

rm -f ./ytarchive.py
echo "Downloading ytarchive..."
wget -O ./ytarchive.py "https://raw.githubusercontent.com/Kethsar/ytarchive/master/ytarchive.py"
echo "Finished."
echo "Starting service..."
gunicorn -b 0.0.0.0:8080 api:api