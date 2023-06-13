source ~/anaconda3/etc/profile.d/conda.sh
conda activate polymetis-local
sudo ip link set enp89s0 down
sudo ip link set enp89s0 up
sudo service network-manager restart

#cd $( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
#python run_server.py
