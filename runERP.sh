#!/usr/bin/bash
source /usr/local/anaconda3/bin/activate dbI

#echo 'virtual env is now active'


read -p 'Enter your name: ' username

python3 /vol01/active_projects/anthony/pyqt_logs/erpPyQt.py --$username
