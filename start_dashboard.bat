@echo off
cd /d C:\SSIS\Prod\Python\slp_hub
start "" "C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe" dashboard_server.py
timeout /t 2
start "" "http://PEERNESHER-SAP2:5052"
