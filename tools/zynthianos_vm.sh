#!/bin/sh
usage_text='A QEMU/KVM VM with upstream'"'"'s own x86_64 zynthian ("virtual zynthian", the setup behind
virtual.zynthian.org): Debian trixie plus zynthian-sys'"'"' scripts/setup_system_lxc_64bit_trixie.sh,
run unchanged, on the tomita branches. For testing upstream behaviour and upstream fixes in
upstream'"'"'s environment, without our port changes (docs/zynthianos-vm.md). Works from any
checkout or worktree of zynthian-ui.

Usage: zynthianos_vm.sh [options] COMMAND [ARGS...]

  start              start the VM (headless) and wait for its SSH
  stop               shut it down (poweroff, then kill)
  status             PID, ports, the repositories'"'"' branches and commits, zynthian'"'"'s state;
                     the last line is "usable: yes" when the VM is built and zynthian runs
  setup              build the VM (idempotent, resumes): a disk from the Debian image, cloud-init
                     (root key, snd-dummy), upstream'"'"'s setup script (1-2 hours, log in the VM:
                     /root/zynthian-setup/setup.log), the test venv; then saves the built disk
                     as DIR/zos-built.img
  reset              throw the VM'"'"'s changes away: back to the built disk (zos-built.img)
  ssh [CMD...]       root shell (or CMD) in the VM
  sync [DIR]         copy the zynthian-ui checkout DIR (default: the current directory'"'"'s, else
                     this script'"'"'s) into the VM'"'"'s /zynthian/zynthian-ui; the first sync saves the
                     original tree as /zynthian/zynthian-ui.orig. .git, venv, build directories
                     and caches are neither sent nor deleted (the VM'"'"'s native builds stay).
                     Changed files get the sync'"'"'s time (native builds rebuild them), owner root
  restore            put the original tree back (from /zynthian/zynthian-ui.orig)
  restart            restart zynthian (virtual_zynthian.service) and wait until it is up
  run-tests [MODE] [ARGS]
                     upstream'"'"'s run_tests.sh in /zynthian/zynthian-ui (MODE: default, gui,
                     native; ARGS go to pytest), with the test venv (/zynthian/venv + pytest);
                     every mode first (re)builds tests/native/build (incremental)
  cuia NAME [ARGS]   send the CUIA /cuia/NAME over OSC (UDP 1370 in the VM)
  shot [FILE]        screenshot of the UI'"'"'s X display (:0, KasmVNC), PNG, default
                     ./zynthianos-shot.png
  log [N]            the last N (default 50) lines of the UI'"'"'s journal
  versions           branch and commit of the zynthian repositories

  -d DIR      the VM'"'"'s directory (ZOSVM_DIR, default /mnt/ssd860/qemu/zynthianos-x86)
  -p PORT     SSH port (default 2272); webconf PORT - 2272 + 8172, KasmVNC (https)
              PORT - 2272 + 8472, OSC PORT - 2272 + 1372 (udp)
  -m MEM      memory (default 6G)
  -c CPUS     virtual CPUs (default 8)
  -b BRANCH   setup: the zynthian branch (default tomita; vangelis = stable)

Example: tools/zynthianos_vm.sh start && tools/zynthianos_vm.sh status
         tools/zynthianos_vm.sh sync ~/bastel/github/zynthian-ui-noticed && tools/zynthianos_vm.sh restart'
set -eu
here=$(cd "$(dirname "$0")" && pwd)

usage() { printf '%s\n' "$usage_text"; exit "${1:-0}"; }

dir=${ZOSVM_DIR:-/mnt/ssd860/qemu/zynthianos-x86}
port=2272 mem=6G cpus=8 branch=tomita
while getopts d:p:m:c:b:h opt; do
	case $opt in
		d) dir=$OPTARG ;;
		p) port=$OPTARG ;;
		m) mem=$OPTARG ;;
		c) cpus=$OPTARG ;;
		b) branch=$OPTARG ;;
		h) usage ;;
		*) usage 1 ;;
	esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || usage 1
cmd=$1
shift
web=$((port - 2272 + 8172))
kasm=$((port - 2272 + 8472))
osc=$((port - 2272 + 1372))
disk=$dir/zos.img
built=$dir/zos-built.img
base_url=https://cloud.debian.org/images/cloud/trixie/latest
base=$dir/debian-13-generic-amd64.raw
ovmf_code=${ZOSVM_OVMF_CODE:-/usr/share/edk2/x64/OVMF_CODE.4m.fd}   # Arch: edk2-ovmf; Debian: ovmf
ovmf_vars=${ZOSVM_OVMF_VARS:-/usr/share/edk2/x64/OVMF_VARS.4m.fd}
password=opensynth            # zynthian's root password (zynthian-sys setup scripts)
# upstream's setup runs in the VM (its shell's PID in /root/zynthian-setup/pid)
setup_running='[ -f /root/zynthian-setup/pid ] && kill -0 $(cat /root/zynthian-setup/pid) 2>/dev/null'

ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10 -o ServerAliveInterval=30"
# shellcheck disable=SC2086 # $ssh_opts: several options
vm_ssh() { ssh $ssh_opts -o BatchMode=yes -p "$port" root@127.0.0.1 "$@"; }
vm_pid() { [ -f "$dir/qemu.pid" ] && kill -0 "$(cat "$dir/qemu.pid")" 2>/dev/null && cat "$dir/qemu.pid"; }

# Quote arguments for the remote shell
q() { for a do printf "'%s' " "$(printf '%s' "$a" | sed "s/'/'\\\\''/g")"; done; }

# The zynthian-ui checkout: DIR, the current directory's, or this script's
checkout() {
	if [ -n "${1:-}" ]; then
		(cd "$1" && pwd)
	elif top=$(git rev-parse --show-toplevel 2>/dev/null) && [ -f "$top/zynthian_main.py" ]; then
		echo "$top"
	else
		(cd "$here/.." && pwd)
	fi
}

pubkey() {
	for k in "$HOME/.ssh/id_ed25519.pub" "$HOME/.ssh/id_rsa.pub"; do [ -f "$k" ] && { cat "$k"; return; }; done
	echo "no SSH public key in ~/.ssh" >&2
	exit 1
}

# A new disk: Debian's generic cloud image (its kernel has snd-dummy, the cloud one has no sound),
# grown to 64 GB, and a cloud-init seed (NoCloud, a FAT image labelled CIDATA): root's key and
# password, hostname zynthian, snd-dummy loaded at boot. snd-dummy is what upstream's LXC host
# provides to its containers: JACKD_OPTIONS of zynthian_envars_LXC_x86_64.sh use hw:Dummy.
new_disk() {
	mkdir -p "$dir"
	if [ ! -f "$base" ]; then
		echo "downloading $base_url/${base##*/}"
		curl -fL# -o "$base.part" "$base_url/${base##*/}"
		(cd "$dir" && curl -fsSL "$base_url/SHA512SUMS" | grep " ${base##*/}\$" | sed "s|${base##*/}\$|${base##*/}.part|" | sha512sum -c -) ||
			{ echo "checksum mismatch" >&2; exit 1; }
		mv "$base.part" "$base"
	fi
	cp --sparse=always "$base" "$disk"
	truncate -s 64G "$disk"
	rm -f "$dir/OVMF_VARS.fd"
	key=$(pubkey)
	t=$(mktemp -d)
	cat > "$t/meta-data" <<EOF
instance-id: zynthianos-vm
local-hostname: zynthian
EOF
	cat > "$t/user-data" <<EOF
#cloud-config
hostname: zynthian
disable_root: false
ssh_pwauth: true
users:
  - name: root
    lock_passwd: false
    ssh_authorized_keys:
      - $key
chpasswd:
  expire: false
  users:
    - {name: root, password: $password, type: text}
write_files:
  - path: /etc/modules-load.d/zynthianos-vm.conf
    content: |
      # zynthianos_vm.sh: the "Dummy device" sound card of zynthian_envars_LXC_x86_64.sh
      snd-dummy
runcmd:
  - [modprobe, snd-dummy]
EOF
	rm -f "$dir/seed.img"
	mkfs.fat -C -n CIDATA "$dir/seed.img" 2048 > /dev/null
	mcopy -i "$dir/seed.img" "$t/meta-data" "$t/user-data" ::
	rm -rf "$t"
	echo "new disk $disk (Debian trixie generic cloud image, 64 GB)"
}

start_vm() {
	fresh=0
	if [ -n "$(vm_pid)" ]; then
		echo "running (PID $(vm_pid), SSH $port)"
	else
		fresh=1
		[ -f "$disk" ] || new_disk
		# UEFI (OVMF): the image's BIOS grub loops on this host (the kernel resets right away)
		[ -f "$dir/OVMF_VARS.fd" ] || cp "$ovmf_vars" "$dir/OVMF_VARS.fd"
		set -- -nodefaults -machine q35,accel=kvm -cpu host -smp "$cpus" -m "$mem" \
			-drive "if=pflash,format=raw,readonly=on,file=$ovmf_code" -drive "if=pflash,format=raw,file=$dir/OVMF_VARS.fd" \
			-drive "file=$disk,format=raw,if=none,id=disk,discard=unmap" -device virtio-blk-pci,drive=disk,bootindex=0 \
			-netdev "user,id=net,hostname=zynthian,hostfwd=tcp:127.0.0.1:$port-:22,hostfwd=tcp:127.0.0.1:$web-:80,hostfwd=tcp:127.0.0.1:$kasm-:8443,hostfwd=udp:127.0.0.1:$osc-:1370" \
			-device virtio-net-pci,netdev=net,romfile= -device virtio-rng-pci \
			-display none -vga none -serial "file:$dir/serial.log" \
			-name zynthianos-vm -pidfile "$dir/qemu.pid" -daemonize
		[ ! -f "$dir/seed.img" ] || set -- "$@" -drive "file=$dir/seed.img,format=raw,if=virtio,readonly=on"
		echo "starting (SSH $port, webconf http://127.0.0.1:$web, KasmVNC https://127.0.0.1:$kasm, OSC udp $osc, serial log $dir/serial.log)"
		qemu-system-x86_64 "$@"
		date +%s > "$dir/started"
	fi
	i=0
	until vm_ssh true 2>/dev/null; do
		i=$((i + 1))
		[ $i -lt 120 ] || { echo "no SSH on port $port after 10 minutes (see $dir/serial.log)" >&2; exit 1; }
		[ -n "$(vm_pid)" ] || { echo "QEMU exited (see $dir/serial.log)" >&2; exit 1; }
		sleep 5
	done
	[ $fresh = 0 ] || echo "SSH up after $(( $(date +%s) - $(cat "$dir/started") )) s"
}

stop_vm() {
	pid=$(vm_pid) || { echo "not running"; return 0; }
	vm_ssh 'poweroff' 2>/dev/null || true
	i=0
	while kill -0 "$pid" 2>/dev/null; do
		i=$((i + 1))
		[ $i -lt 90 ] || { kill "$pid"; break; }
		sleep 1
	done
	echo "stopped"
}

# zynthian is up: the UI service runs and its OSC server (UDP 1370) is bound
wait_up() {
	t0=$(date +%s)
	timeout=${1:-300}
	while :; do
		if vm_ssh 'systemctl is-active -q virtual_zynthian && ss -lun | grep -q ":1370 "' 2>/dev/null; then
			echo "zynthian is up ($(( $(date +%s) - t0 )) s)"
			return 0
		fi
		if [ $(( $(date +%s) - t0 )) -ge "$timeout" ]; then
			echo "zynthian didn't come up in $timeout s:" >&2
			vm_ssh 'journalctl -u virtual_zynthian -n 30 --no-pager' >&2 || true
			return 1
		fi
		sleep 2
	done
}

# Upstream's setup, as upstream runs it in its trixie container: the three scripts it needs next to
# each other (setup_system_lxc_64bit_trixie.sh sources ./zynthian_envars_extended.sh, which sources
# ./zynthian_envars.sh), the branches from the environment, run as root. It runs detached in the
# VM (nohup) and this waits for it; running setup again resumes waiting.
#
# Run unchanged on a fresh Debian trixie (2026-11-19, tomita 3df97e00), the script breaks early and
# everything after cascades (docs/zynthianos-vm.md, "Changes to upstream's setup"): it was evidently
# developed in a container that already had the zynthian environment. The fixes, as small as
# possible, each logged as an upstream issue:
#  1. ./zynthian_envars.sh is config/zynthian_envars_LXC_x86_64.sh, the configuration the script
#     itself installs later (line 266): with scripts/zynthian_envars.sh, zyncoder is built for a
#     wiring layout with GPIO (wiringPi.h missing) before that.
#  2. PATH has zynthian-sys' scripts and sbin from the start (etc/profile.zynthian, which the
#     script only sources at line 250; create_my_data_dirtree.sh is called bare at line 208).
#  3. python3-lgpio is dropped from the script's apt line: it exists only in Raspberry Pi OS'
#     archive, and the failed apt-get leaves out every Python package of that line (python3.13-venv
#     too: no /zynthian/venv, no pip modules).
#  4. ZYNTHIAN_MY_DATA=/zynthian/zynthian-my-data in the environment: sbin/create_my_data_dirtree.sh
#     tests and creates "$ZYNTHIAN_MY_DATA", which nothing defines (the rest of it uses
#     $ZYNTHIAN_MY_DATA_DIR), so zynthian-my-data's tree isn't created.
#  5. python-is-python3 and the en_US.UTF-8 locale beforehand (Raspberry Pi OS has both; recipes
#     with "#!/usr/bin/env python" waf scripts fail, and the script's update-locale names
#     en_US.UTF-8 without generating it).
upstream_setup() {
	if vm_ssh '[ -f /root/zynthian-setup/done ]'; then
		echo "upstream setup: done ($(vm_ssh 'cat /root/zynthian-setup/done'))"
		return 0
	fi
	if ! vm_ssh "$setup_running"; then
		vm_ssh '[ ! -d /zynthian ]' || { echo "/zynthian exists but the setup didn't finish: see /root/zynthian-setup/setup.log in the VM; start over with: rm $disk; setup" >&2; exit 1; }
		echo "upstream setup on branch $branch (zynthian-sys $branch: scripts/setup_system_lxc_64bit_trixie.sh)"
		vm_ssh "set -e
			cloud-init status --wait >/dev/null 2>&1 || true
			mkdir -p /root/zynthian-setup && cd /root/zynthian-setup
			raw=https://raw.githubusercontent.com/zynthian/zynthian-sys/$branch
			for f in setup_system_lxc_64bit_trixie.sh zynthian_envars_extended.sh; do
				curl -fsSL -o \$f.orig \$raw/scripts/\$f
				cp \$f.orig \$f
			done
			curl -fsSL -o zynthian_envars.sh \$raw/config/zynthian_envars_LXC_x86_64.sh
			sed -i 's/ python3-lgpio / /' setup_system_lxc_64bit_trixie.sh
			chmod +x setup_system_lxc_64bit_trixie.sh
			diff -u setup_system_lxc_64bit_trixie.sh.orig setup_system_lxc_64bit_trixie.sh > setup.patch || true
			export DEBIAN_FRONTEND=noninteractive
			apt-get update -q > /dev/null
			apt-get install -y -q python-is-python3 locales > /dev/null
			sed -i 's/^# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
			locale-gen > /dev/null
			date +%s > started
			PATH=\$PATH:/zynthian/zynthian-sys/scripts:/zynthian/zynthian-sys/sbin ZYNTHIAN_MY_DATA=/zynthian/zynthian-my-data ZYNTHIAN_BRANCH=$branch ZYNTHIAN_SYS_BRANCH=$branch \\
				nohup setsid bash -c 'echo \$\$ > pid; ./setup_system_lxc_64bit_trixie.sh; echo \$? > exit; date -u +%FT%TZ > done.time' > setup.log 2>&1 < /dev/null &
			sleep 1"
	fi
	echo "waiting for upstream's setup (log: $0 ssh tail -f /root/zynthian-setup/setup.log)"
	while vm_ssh "$setup_running" 2>/dev/null; do sleep 30; done
	vm_ssh 'cd /root/zynthian-setup && [ -f exit ] && echo "setup finished: exit $(cat exit), $(( $(stat -c %Y exit) - $(cat started) )) s" && echo "$(cat done.time), exit $(cat exit), branch '"$branch"'" > done'
}

# The test venv: /zynthian/zynthian-ui/venv (upstream's run_tests.sh prefers the checkout's venv
# over /zynthian/venv), seeing /zynthian/venv's packages through a .pth file, plus pytest & co
# from requirements-dev.txt. sync and restore leave it alone.
setup_tests() {
	echo "test venv /zynthian/zynthian-ui/venv (sees /zynthian/venv; + pytest, pytest-timeout, pytest-cov, ruff), xvfb"
	vm_ssh 'set -e
		DEBIAN_FRONTEND=noninteractive apt-get install -y -q xvfb xauth > /dev/null
		cd /zynthian/zynthian-ui
		[ -x venv/bin/python3 ] || /zynthian/venv/bin/python3 -m venv --system-site-packages venv
		zsp=$(/zynthian/venv/bin/python3 -c "import sysconfig; print(sysconfig.get_path(\"purelib\"))")
		echo "$zsp" > "$(venv/bin/python3 -c "import sysconfig; print(sysconfig.get_path(\"purelib\"))")/zynthian-venv.pth"
		venv/bin/pip install -q --disable-pip-version-check pytest pytest-timeout pytest-cov ruff
		grep -qx "/venv/" .git/info/exclude 2>/dev/null || echo "/venv/" >> .git/info/exclude
		venv/bin/python3 -c "import pytest, jack, numpy, PIL"'
}

# KasmVNC's first start asks interactively which desktop to run (select-de.sh) and fails under
# systemd (virtual_zynthian.service: "kasmvncserver :0"): no X server, the UI can't open its
# display. Upstream's setup leaves that to an interactive first run; here: an xstartup without a
# desktop (the zynthian UI is the only X client) and KasmVNC's "desktop was selected" marker.
setup_kasmvnc() {
	vm_ssh '[ -f /root/.vnc/.de-was-selected ] && [ -x /root/.vnc/xstartup ]' && return 0
	echo "KasmVNC: xstartup without a desktop"
	vm_ssh 'mkdir -p /root/.vnc && cat > /root/.vnc/xstartup <<EOF
#!/bin/sh
# zynthianos_vm.sh: KasmVNC without a desktop environment. virtual_zynthian.service starts
# "kasmvncserver :0", whose first run asks interactively for a desktop (select-de.sh) and fails
# under systemd; the zynthian UI is the only X client.
exec sleep infinity
EOF
		chmod 755 /root/.vnc/xstartup && touch /root/.vnc/.de-was-selected && systemctl restart virtual_zynthian'
}

setup_vm() {
	start_vm
	upstream_setup
	setup_kasmvnc
	setup_tests
	if [ ! -f "$built" ]; then
		echo "rebooting (first boot of the built system)"
		vm_ssh 'systemctl reboot' 2>/dev/null || true
		sleep 15
		start_vm
		wait_up 600
		echo "saving the built disk as $built (reset goes back to it)"
		vm_ssh 'sync; fstrim -a 2>/dev/null; true'
		stop_vm
		cp --sparse=always "$disk" "$built"
		start_vm
	fi
	wait_up 600
	versions
	echo "ready"
}

versions() {
	vm_ssh 'for r in zynthian-sys zynthian-ui zyncoder zynthian-webconf zynthian-data zynthian-help; do
			printf "%-17s %s\n" "$r" "$(git -C /zynthian/$r log -1 --format="%h %cd" --date=short 2>/dev/null) $(git -C /zynthian/$r rev-parse --abbrev-ref HEAD 2>/dev/null)"
		done'
}

sync_tree() {
	src=$(checkout "${1:-}")
	[ -f "$src/zynthian_main.py" ] || { echo "$src: not a zynthian-ui checkout" >&2; exit 1; }
	vm_ssh '[ -d /zynthian/zynthian-ui.orig ] || { echo "saving the original tree as /zynthian/zynthian-ui.orig"; cp -a /zynthian/zynthian-ui /zynthian/zynthian-ui.orig; }'
	echo "sync $src -> VM:/zynthian/zynthian-ui"
	# .gitignore'd files (build directories, caches, venv) are neither sent nor deleted: the VM's
	# native builds (zynlibs/*/build) and its test venv stay. The VM's .git stays too: git
	# status/diff there show the synced change against the VM's commit.
	# Not -a: no host mtimes (-t) but --checksum, so only files whose content differs are written,
	# with the time of the sync: newer than the VM's native builds, which make then rebuilds
	# (run-tests native, zynlibs/build.sh). Owner root:root as upstream's tree (rsync as root
	# would keep the host's uid 1000).
	rsync -rlpgoD --checksum --chown=root:root --delete -e "ssh $ssh_opts -p $port" --filter=':- .gitignore' --exclude=.git --exclude='/venv*' \
		--exclude=build/ --exclude=__pycache__ --exclude=.pytest_cache --exclude=.ruff_cache --exclude='*.pyc' --exclude='*.so' \
		"$src/" "root@127.0.0.1:/zynthian/zynthian-ui/"
	vm_ssh 'cd /zynthian/zynthian-ui && git status --short | head -n 20'
}

restore_tree() {
	vm_ssh '[ -d /zynthian/zynthian-ui.orig ]' || { echo "nothing to restore (no sync yet)"; return 0; }
	echo "restoring /zynthian/zynthian-ui from /zynthian/zynthian-ui.orig"
	# As sync: changed files get the current time (the native builds see them as newer)
	vm_ssh 'rsync -rlpgoD --checksum --delete --exclude=/venv /zynthian/zynthian-ui.orig/ /zynthian/zynthian-ui/ && rm -rf /zynthian/zynthian-ui.orig && cd /zynthian/zynthian-ui && git status --short | head'
}

case $cmd in
	start) start_vm ;;
	stop) stop_vm ;;
	status)
		if pid=$(vm_pid); then
			echo "running: PID $pid, SSH $port (ssh -p $port root@127.0.0.1), webconf http://127.0.0.1:$web, KasmVNC https://127.0.0.1:$kasm (root/$password), OSC udp $osc, directory $dir"
			if vm_ssh true 2>/dev/null; then
				if vm_ssh '[ -f /root/zynthian-setup/done ]'; then
					versions
					vm_ssh '[ -d /zynthian/zynthian-ui.orig ] && echo "zynthian-ui: synced tree (original in /zynthian/zynthian-ui.orig)" || echo "zynthian-ui: original tree"'
					if vm_ssh 'systemctl is-active -q virtual_zynthian && ss -lun | grep -q ":1370 "'; then
						echo "zynthian: running"
						[ -f "$built" ] && echo "usable: yes" || echo "usable: no (setup still finishing)"
					else
						echo "zynthian: not running ($(vm_ssh 'systemctl is-active virtual_zynthian'))"
						echo "usable: no"
					fi
				else
					vm_ssh "$setup_running"' && echo "upstream setup running: $(tail -n 1 /root/zynthian-setup/setup.log | cut -c1-100)" || echo "upstream setup not done (setup)"'
					echo "usable: no"
				fi
			else
				echo "no SSH (booting?)"
				echo "usable: no"
			fi
		else
			echo "not running (directory $dir)"
			echo "usable: no"
		fi
		;;
	setup) setup_vm ;;
	reset)
		[ -f "$built" ] || { echo "no built disk yet ($built): setup" >&2; exit 1; }
		[ -z "$(vm_pid)" ] || stop_vm
		cp --sparse=always "$built" "$disk"
		echo "disk reset to $built" ;;
	ssh)
		# shellcheck disable=SC2086
		if [ $# -eq 0 ]; then ssh $ssh_opts -t -p "$port" root@127.0.0.1; else vm_ssh "$*"; fi ;;
	sync) sync_tree "$@" ;;
	restore) restore_tree ;;
	restart)
		vm_ssh 'systemctl restart virtual_zynthian'
		sleep 3
		wait_up 300 ;;
	run-tests)
		mode=
		case ${1:-} in default) shift ;; gui | native) mode=$1; shift ;; esac
		# Every mode: (re)build tests/native/build first (the default and gui suites load the native
		# libraries too, e.g. the zynseq tests). run_tests.sh builds them only when libzyncore.so is
		# missing, so after a sync the old libraries ran: a segfault in the zynseq tests, then a
		# jack.Client() that hung until a reboot. build_native.sh runs cmake + make in the existing
		# build directories: sources changed by sync (newer mtimes) are rebuilt, the rest stays
		build="tests/native/build_native.sh /zynthian/zyncoder >/dev/null || { echo 'native build failed (tests/native/build/*/make.log)'; exit 1; }; "
		vm_ssh "cd /zynthian/zynthian-ui && $build./run_tests.sh $mode $(q "$@")" ;;
	cuia)
		[ $# -ge 1 ] || usage 1
		n=$1; shift
		types=
		for a do case $a in *[!0-9-]* | '') types=${types}s ;; *) types=${types}i ;; esac; done
		if [ -n "$types" ]; then oscsend "osc.udp://127.0.0.1:$osc" "/cuia/$n" "$types" "$@"; else oscsend "osc.udp://127.0.0.1:$osc" "/cuia/$n"; fi ;;
	shot)
		f=${1:-zynthianos-shot.png}
		# X's screen is KasmVNC's default size; the UI's window is DISPLAY_WIDTHxDISPLAY_HEIGHT at 0,0
		vm_ssh '. /zynthian/config/zynthian_envars.sh; DISPLAY=:0 import -window root -crop "${DISPLAY_WIDTH}x${DISPLAY_HEIGHT}+0+0" +repage png:-' > "$f"
		[ -s "$f" ] && echo "$f" ;;
	log) vm_ssh "journalctl -u virtual_zynthian -n ${1:-50} --no-pager" ;;
	versions) versions ;;
	*) usage 1 ;;
esac
