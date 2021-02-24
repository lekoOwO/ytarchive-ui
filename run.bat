@echo off

echo Starting service...
waitress-serve --port=30004 api:api