@echo off

cd /d C:\BentaPOS\config\config
call env\Scripts\activate.bat 

waitress-serve --listen=0.0.0.0:8000 config.wsgi.application