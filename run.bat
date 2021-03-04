@echo off

:head
echo Starting service...
waitress-serve --port=30004 api:api
goto head