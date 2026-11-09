#!/bin/sh
# One-time setup of a running QEMU VM (nura/tools/run_qemu.sh) for scripted use (agents, tests): installs
# this user's SSH public key for the VM's user, and passwordless sudo for that user in the VM, using
# the image's password once. Then ssh/scp work with BatchMode (the other nura/tools with -V).
#
#   nura/tools/qemu_setup.sh [-p PORT] [-u USER] [-k PUBKEY] [-w PASSWORD]
#
#   -p PORT      the VM's SSH port on this machine (default 2222, as run-qemu.sh)
#   -u USER      the VM's user (default user)
#   -k PUBKEY    public key to install (default the first of ~/.ssh/id_ed25519.pub, id_rsa.pub)
#   -w PASSWORD  the user's password in the image (default 147147, NURA_IMAGE_PASSWORD in CI)
#
# Run it again after run-qemu.sh -r / -u (a fresh disk).
set -eu

usage() { sed -n '2,/^set -eu/{/^set -eu/d;s/^# \{0,1\}//;p}' "$0"; exit "${1:-0}"; }
port=2222 user=user key= password=147147
while getopts p:u:k:w:h opt; do
	case $opt in
		p) port=$OPTARG ;;
		u) user=$OPTARG ;;
		k) key=$OPTARG ;;
		w) password=$OPTARG ;;
		h) usage ;;
		*) usage 1 ;;
	esac
done
if [ -z "$key" ]; then
	for k in "$HOME/.ssh/id_ed25519.pub" "$HOME/.ssh/id_rsa.pub"; do
		[ -f "$k" ] && { key=$k; break; }
	done
fi
[ -f "$key" ] || { echo "no SSH public key (-k)" >&2; exit 1; }

# The VM's host key changes with every fresh disk: don't record it
opts="-p $port -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

# The password for ssh through SSH_ASKPASS (OpenSSH 8.4+), no terminal needed
askpass=$(mktemp)
trap 'rm -f "$askpass"' EXIT
printf '#!/bin/sh\necho %s\n' "'$password'" > "$askpass"
chmod 700 "$askpass"

echo "waiting for the VM's SSH on port $port"
i=0
until SSH_ASKPASS=$askpass SSH_ASKPASS_REQUIRE=force DISPLAY=${DISPLAY:-:0} \
	ssh $opts -o ConnectTimeout=5 -o NumberOfPasswordPrompts=1 "$user@127.0.0.1" true 2>/dev/null; do
	i=$((i + 1))
	[ $i -lt 60 ] || { echo "no SSH login on port $port (is the VM running? the password right?)" >&2; exit 1; }
	sleep 5
done

# shellcheck disable=SC2086 # $opts: several options
SSH_ASKPASS=$askpass SSH_ASKPASS_REQUIRE=force DISPLAY=${DISPLAY:-:0} ssh $opts "$user@127.0.0.1" \
	"set -e
	mkdir -p ~/.ssh && chmod 700 ~/.ssh
	grep -qxF '$(cat "$key")' ~/.ssh/authorized_keys 2>/dev/null || echo '$(cat "$key")' >> ~/.ssh/authorized_keys
	chmod 600 ~/.ssh/authorized_keys
	echo '$password' | sudo -S -p '' sh -c \"echo '$user ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-nura-vm && chmod 440 /etc/sudoers.d/90-nura-vm\""

# shellcheck disable=SC2086
ssh $opts -o BatchMode=yes "$user@127.0.0.1" 'sudo -n true' && echo "ready: ssh -p $port $user@127.0.0.1 (key login, passwordless sudo)"
