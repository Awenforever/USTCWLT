# Installation
```commandline
git clone https://github.com/Awenforever/USTCWLT.git && cd ./USTCWLT
pip install -r requirements
```
# Configuration
Create `./.env` and fill in your username and password:
```text
APP_NAME=your_name
APP_PASSWORD=your_password
```
# Usage
```commandline
python ./wlt.py
```
# Auto run bat when system start up
```commandline
timeout /t 30 /nobreak >nul && cd /d "E:\Pycharm Project\SpectralGPT\wlt" && python ./wlt.py
```