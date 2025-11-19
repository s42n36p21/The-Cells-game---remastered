@echo off
echo Downloading requirements...
pip install -r game/src/requirements.txt
echo requirements downloaded
echo @echo off > run.bat
echo start game/main.py >> run.bat
echo exit >> run.bat
echo @echo off > start_server.bat
echo start game/start_server.py >> start_server.bat
echo exit >> start_server.bat
echo You can run your game from run.bat and start_server.bat
pause