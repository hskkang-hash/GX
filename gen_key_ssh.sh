ssh-keygen -t ed25519 -C "huyngk@gaion.kr"
cat ~/.ssh/id_ed25519.pub
eval $(ssh-agent)
ssh-add ~/.ssh/id_ed25519
echo $SSH_AUTH_SOCK