mkdir -p ~/.ssh
curl 10.0.2.2:8000/key > ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
echo "Done setting up SSH keys"
