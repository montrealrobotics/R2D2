ssh 172.16.0.3 "pkill -f run_server.py"
ssh 172.16.0.3 "source ~/anaconda3/etc/profile.d/conda.sh; conda activate polymetis-local; cd /home/r2d2/r2d2_code_ws/src/R2D2/scripts/server; python run_server.py"
ssh 172.16.0.3 "pkill -f run_server.py"
read -p "NUC server stopped. Press enter to continue"
