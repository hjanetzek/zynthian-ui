#!/bin/sh
usage_text='A QEMU VM for zynthian-ui'"'"'s test suite (docs/test-vm.md): the tests run there, not on this
machine. Works from any checkout or worktree of zynthian-ui.

Usage: test_vm.sh [options] COMMAND [ARGS...]

  start              start the VM (headless) and wait for its SSH
  stop               shut it down (sudo poweroff, then kill)
  status             PID, ports, disk, the synced trees
  setup              start it if needed and install everything the suite needs (idempotent: run it
                     on a fresh disk, -r setup builds one from the image)
  sync [DIR]         copy the checkout DIR (default: the one of the current directory, else this
                     script'"'"'s) into the VM as ~/zynthian-ui-test/NAME (NAME: DIR'"'"'s directory name),
                     with zyncoder and zynthian-data/snapshots next to it; .git, venvs, build
                     directories and caches are left out (the VM'"'"'s own native build is kept); the
                     VM'"'"'s tree gets a git index with the checkout'"'"'s file modes (no history)
  run [MODE] [ARGS]  run_tests.sh in the VM on the synced tree of the current checkout; MODE:
                     default (the hermetic run, same as ./run_tests.sh), gui (under xvfb), native
                     (tests/native only), all (default, gui and native one after the other, with a
                     summary). ARGS go to pytest. The native libraries are built (incrementally)
                     before each run. Exit code: pytest'"'"'s (all: the first non-zero one)
  shell [CMD...]     a login shell (or CMD) in the VM, in the synced tree if there is one

  -t NAME     the tree'"'"'s name in the VM (default: the checkout'"'"'s directory name)
  -r          start from a fresh disk (discards the VM'"'"'s changes; then run setup)
  -B          run: don'"'"'t build the native libraries first
  -i IMAGE    the image for new disks (default: the user'"'"'s download,
              ~/.cache/nura-builds/zynthian-qemu-amd64.img.zst)
  -d DIR      the VM'"'"'s directory (disk, logs, PID; NURA_TEST_VM_DIR). Default: nura-builds-test on
              the VM drive, /mnt/ssd860/qemu (NURA_QEMU_DRIVE: its qemu directory), when it is
              mounted, else ~/.cache/nura-builds-test. When the drive isn'"'"'t mounted and ~/.cache
              has no disk either, the script stops instead of creating a
              new disk there (mount the drive, or pass -d)
  -p PORT     its SSH port (default 2262; NURA_TEST_VM_PORT), webconf: PORT - 2262 + 8162
  -m MEM      memory (default 4G)
  -c CPUS     virtual CPUs (default 8)

Example (from a worktree): tools/test_vm.sh sync && tools/test_vm.sh run all'
set -eu
here=$(cd "$(dirname "$0")" && pwd)

usage() { printf '%s\n' "$usage_text"; exit "${1:-0}"; }

dir=${NURA_TEST_VM_DIR:-}
drive=${NURA_QEMU_DRIVE:-/mnt/ssd860/qemu}
port=${NURA_TEST_VM_PORT:-2262} mem=4G cpus=8 reset=0 build=1 name=
image=${XDG_CACHE_HOME:-$HOME/.cache}/nura-builds/zynthian-qemu-amd64.img.zst
while getopts t:rBi:d:p:m:c:h opt; do
	case $opt in
		t) name=$OPTARG ;;
		r) reset=1 ;;
		B) build=0 ;;
		i) image=$OPTARG ;;
		d) dir=$OPTARG ;;
		p) port=$OPTARG ;;
		m) mem=$OPTARG ;;
		c) cpus=$OPTARG ;;
		h) usage ;;
		*) usage 1 ;;
	esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || usage 1
cmd=$1
shift
web=$((port - 2262 + 8162))

# The VM's directory: given (-d, NURA_TEST_VM_DIR), on the VM drive, or in ~/.cache, but not a new
# disk in ~/.cache only because the drive isn't there right now
if [ -z "$dir" ]; then
	if [ -d "$drive" ] && mountpoint -q "$(df --output=target "$drive" | tail -n 1)" 2>/dev/null &&
		[ "$(df --output=target "$drive" | tail -n 1)" != / ]; then
		dir=$drive/nura-builds-test
	else
		dir=${XDG_CACHE_HOME:-$HOME/.cache}/nura-builds-test
		if [ ! -f "$dir/zynthian-qemu-amd64.img" ]; then
			echo "the VM drive ($drive) isn't mounted, and $dir has no disk:" >&2
			echo "mount the drive (sudo mount /mnt/ssd860: it is in /etc/fstab), or pass -d DIR" >&2
			[ "$cmd" = status ] || exit 1
		else
			echo "note: the VM drive ($drive) isn't mounted: using $dir" >&2
		fi
	fi
fi
base=zynthian-ui-test   # in the VM's home: NAME/, zyncoder/, zynthian-data/snapshots/

ssh_opts="-o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10 -o ServerAliveInterval=30"
# shellcheck disable=SC2086 # $ssh_opts: several options
vm_ssh() { ssh $ssh_opts -p "$port" user@127.0.0.1 "$@"; }
vm_pid() { [ -f "$dir/qemu.pid" ] && kill -0 "$(cat "$dir/qemu.pid")" 2>/dev/null && cat "$dir/qemu.pid"; }

# Quote arguments for the remote shell
q() { for a do printf "'%s' " "$(printf '%s' "$a" | sed "s/'/'\\\\''/g")"; done; }

# The zynthian-ui checkout: DIR, the current directory's, or this script's
checkout() {
	if [ -n "${1:-}" ]; then
		(cd "$1" && pwd)
	elif top=$(git rev-parse --show-toplevel 2>/dev/null) && [ -f "$top/run_tests.sh" ]; then
		echo "$top"
	else
		(cd "$here/.." && pwd)
	fi
}
tree_name() { if [ -n "$name" ]; then echo "$name"; else basename "$1"; fi; }

start_vm() {
	if [ -n "$(vm_pid)" ]; then
		[ $reset = 0 ] || { echo "the VM is running: stop it before -r" >&2; exit 1; }
		echo "running (PID $(vm_pid), SSH $port)"
	else
		mkdir -p "$dir"
		# run_qemu.sh unpacks the .img.zst it finds in its directory: a link to the user's download
		if [ ! -e "$dir/zynthian-qemu-amd64.img.zst" ] && [ -f "$image" ]; then
			ln -sf "$(readlink -f "$image")" "$dir/zynthian-qemu-amd64.img.zst"
		fi
		set -- -d "$dir" -D none -A none -m "$mem" -c "$cpus" -s 12G -p "$port" -w "$web"
		[ $reset = 0 ] || set -- "$@" -r
		echo "starting (SSH $port, log $dir/run.log)"
		setsid "$here/run_qemu.sh" "$@" < /dev/null > "$dir/run.log" 2>&1 &
		i=0
		while [ -z "$(vm_pid)" ]; do
			i=$((i + 1))
			if [ $i -gt 600 ] || ! kill -0 $! 2>/dev/null; then
				echo "QEMU didn't start:" >&2
				tail -n 20 "$dir/run.log" >&2
				exit 1
			fi
			sleep 1
		done
	fi
	# SSH: wait for the VM's sshd, then log in with the key, else (a new disk) qemu_setup.sh
	# installs it and passwordless sudo
	i=0
	until ssh-keyscan -T 5 -p "$port" 127.0.0.1 >/dev/null 2>&1; do
		i=$((i + 1))
		[ $i -lt 60 ] || { echo "no SSH on port $port after 5 minutes (see $dir/serial.log)" >&2; exit 1; }
		sleep 5
	done
	if ! vm_ssh true 2>/dev/null; then
		echo "setting up SSH key and sudo (a new disk)"
		"$here/qemu_setup.sh" -p "$port" > /dev/null
	fi
}

stop_vm() {
	pid=$(vm_pid) || { echo "not running"; return 0; }
	vm_ssh 'sudo poweroff' 2>/dev/null || true
	i=0
	while kill -0 "$pid" 2>/dev/null; do
		i=$((i + 1))
		[ $i -lt 60 ] || { kill "$pid"; break; }
		sleep 1
	done
	echo "stopped"
}

# Everything the suite needs. The image is zynthian's own Nura image: the Python modules zynthian
# imports (lilv, numpy, scipy, PySide6, Tk, ...) come with its zynthian-ui package. Added here:
# pytest, the native build (compilers, cmake, the JACK/ALSA/liblo/sndfile/... headers), xvfb,
# a jackd, and a venv that sees the modules zynthian-ui vendors.
apk_packages="build-base cmake pkgconf python3-dev py3-pip py3-pytest py3-pytest-timeout py3-pytest-cov ruff
	git rsync xvfb xvfb-run xauth font-dejavu mesa-dri-gallium
	pipewire-jack-dev alsa-lib-dev liblo-dev libsndfile-dev libsamplerate-dev rubberband-dev fftw-dev nlohmann-json
	py3-cffi py3-cairosvg"
# Not in Alpine and not vendored by the zynthian-ui package: what zyngui/zynthian_widget_audio_file.py
# (the Tk UI's audio file widget) imports, from PyPI into the venv
pip_packages="moderngl-window pyopengltk"
setup_vm() {
	start_vm
	echo "installing the packages"
	# shellcheck disable=SC2086
	vm_ssh "set -e
		sudo apk update -q 2>&1 | grep -v '^WARNING: Permanently redirected' || true
		sudo apk add -q $(echo $apk_packages) 2>&1 | grep -v '^WARNING: Permanently redirected' || true
		for p in $(echo $apk_packages); do apk info -e \$p >/dev/null || { echo \"missing: \$p\" >&2; exit 1; }; done"
	# jackd: Alpine's jack package conflicts with pipewire-jack (both have /usr/lib/libjack.so.0),
	# which the image's zynthian packages depend on, and pipewire-jack's libjack talks to PipeWire,
	# not to a jackd. So jack is unpacked to /opt/jack, and its lib directory goes first in musl's
	# library path (/etc/ld-musl-x86_64.path): every process in the VM loads jack's libjack, also the
	# child processes the tests start with a clean environment (tests/native/zynmixer/test_exit.py).
	# Nothing in the VM uses PipeWire's JACK (the kiosk session is off). The libraries are built
	# against pipewire-jack-dev's headers (the same API and soname, libjack.so.0).
	echo "jackd in /opt/jack"
	vm_ssh 'set -e
		t=$(mktemp -d); cd "$t"
		apk fetch -q jack 2>&1 | grep -v "^WARNING: Permanently redirected" || true
		apk=$(ls jack-*.apk)
		if [ "$(cat /opt/jack/.apk 2>/dev/null)" != "$apk" ]; then
			sudo rm -rf /opt/jack; sudo mkdir -p /opt/jack
			sudo tar -xzf "$apk" -C /opt/jack 2>/dev/null || true
			sudo rm -f /opt/jack/.PKGINFO /opt/jack/.SIGN.* /opt/jack/.pre-* /opt/jack/.post-*
			echo "$apk" | sudo tee /opt/jack/.apk >/dev/null
		fi
		cd /; rm -rf "$t"
		test -x /opt/jack/usr/bin/jackd
		# (the libjack.so link of jack-dev: JACK-Client dlopen()s libjack.so, which musl would else
		# find as pipewire-jack-dev'"'"'s /usr/lib/libjack.so)
		sudo ln -sf libjack.so.0 /opt/jack/usr/lib/libjack.so
		printf "%s\\n" /opt/jack/usr/lib /lib /usr/local/lib /usr/lib | sudo tee /etc/ld-musl-x86_64.path >/dev/null'
	# The jackd wrapper on PATH (the tests find jackd with shutil.which). musl'"'"'s getopt misparses
	# separate driver option values (-d dummy -r 48000 -p 256 gives a period of 8192, not 256):
	# the wrapper attaches them (-r48000 -p256)
	vm_ssh 'sudo tee /usr/local/bin/jackd >/dev/null' <<'EOF'
#!/bin/sh
# jackd of the test VM (tools/test_vm.sh): Alpine's jack, unpacked to /opt/jack because it
# conflicts with pipewire-jack's libjack (its libjack is found through /etc/ld-musl-x86_64.path).
export JACK_DRIVER_DIR=/opt/jack/usr/lib/jack
# musl's getopt misparses separate driver option values (-d dummy -p 256): attach them (-p256)
driver=0 pend= first=1
for a do
	[ $first = 0 ] || { set --; first=0; }
	if [ -n "$pend" ]; then
		case $a in
			-*) set -- "$@" "$pend" ;;
			*) set -- "$@" "$pend$a"; pend=; continue ;;
		esac
		pend=
	fi
	if [ $driver = 2 ]; then
		case $a in -[a-zA-Z]) pend=$a; continue ;; esac
	fi
	set -- "$@" "$a"
	case $a in
		-d | --driver) driver=1 ;;
		-d?*) driver=2 ;;
		*) [ $driver != 1 ] || driver=2 ;;
	esac
done
[ -z "$pend" ] || set -- "$@" "$pend"
exec /opt/jack/usr/bin/jackd "$@"
EOF
	vm_ssh 'sudo chmod 755 /usr/local/bin/jackd'
	# The environment of the test runs (also for login shells: test_vm.sh shell)
	vm_ssh 'sudo tee /etc/profile.d/zyntest.sh >/dev/null' <<'EOF'
# zynthian-ui test VM (tools/test_vm.sh, docs/test-vm.md)
# the venv: the system's modules and the ones zynthian-ui vendors (/usr/share/zynthian/python)
export VIRTUAL_ENV=$HOME/zyntest-venv
export PATH=$VIRTUAL_ENV/bin:$PATH
EOF
	# The Python modules the zynthian-ui package vendors (not packaged in Alpine: JACK-Client,
	# pyliblo3, oyaml, soundfile, wavio, ...; nura-builds: aports/zynthian/zynthian-ui/APKBUILD) are
	# in /usr/share/zynthian/python, which zynthian'"'"'s launcher puts on its path. The test venv
	# gets them through a .pth file
	echo "venv ~/zyntest-venv (system modules + /usr/share/zynthian/python)"
	vm_ssh "set -e
		[ -x ~/zyntest-venv/bin/python3 ] || python3 -m venv --system-site-packages ~/zyntest-venv
		echo /usr/share/zynthian/python > \$(~/zyntest-venv/bin/python3 -c 'import sysconfig; print(sysconfig.get_path(\"purelib\"))')/zynthian.pth
		~/zyntest-venv/bin/pip install -q --disable-pip-version-check $pip_packages
		~/zyntest-venv/bin/python3 -c 'import jack, pyliblo3, oyaml, lilv, numpy, PySide6, tkinter, pytest, moderngl_window'"
	# A test machine: no kiosk session (zynthian, PipeWire) running beside the tests
	vm_ssh 'if systemctl is-enabled -q tinydm 2>/dev/null; then sudo systemctl disable -q --now tinydm; fi'
	echo "checking: a private dummy jackd and a client"
	vm_ssh '. /etc/profile.d/zyntest.sh
		jackd --no-realtime -n zyntest_setup -d dummy -r 48000 -p 256 >/tmp/zyntest_setup_jackd.log 2>&1 &
		timeout 60 python3 - <<EOF
import time, jack
jack.set_error_function(lambda msg: None)
for _ in range(100):
    try:
        c = jack.Client("probe", servername="zyntest_setup", no_start_server=True)
        break
    except jack.JackError:
        time.sleep(0.05)
else:
    raise SystemExit("no jackd")
print("jackd OK: %d Hz, %d frames per period" % (c.samplerate, c.blocksize))
assert (c.samplerate, c.blocksize) == (48000, 256)
c.close()
EOF
		r=$?; kill $! 2>/dev/null; wait 2>/dev/null; exit $r'
	echo "ready"
}

sync_tree() {
	src=$(checkout "${1:-}")
	[ -f "$src/run_tests.sh" ] || { echo "$src: not a zynthian-ui checkout" >&2; exit 1; }
	n=$(tree_name "$src")
	rs="ssh $ssh_opts -p $port"
	vm_ssh "mkdir -p ~/$base/$n ~/$base/zynthian-data"
	echo "sync $src -> VM:~/$base/$n"
	# .gitignore'd files (venv, __pycache__, build directories, caches) are neither sent nor deleted
	# in the VM: its tests/native/build stays
	rsync -a --delete -e "$rs" --filter=':- .gitignore' --exclude=.git --exclude='/venv*' --exclude=/.venv \
		--exclude=build/ --exclude=__pycache__ --exclude=.pytest_cache --exclude=.ruff_cache --exclude='*.pyc' \
		"$src/" "user@127.0.0.1:$base/$n/"
	# git's index of the checkout (modes and blob ids, no objects or history): what
	# tests/architecture/test_cli_scripts.py checks (the executable bit as committed)
	if git -C "$src" rev-parse --git-dir >/dev/null 2>&1; then
		git -C "$src" ls-files -s | vm_ssh "cd ~/$base/$n && rm -rf .git && git init -q && git update-index --index-info"
	fi
	# zyncoder (libzyncore's sources; the tree's zyncoder link points to ../zyncoder) and the
	# public example snapshots (the corpus tests look for ../zynthian-data/snapshots)
	zc=$src/zyncoder
	[ -f "$zc/CMakeLists.txt" ] || zc=$src/../zyncoder
	if [ -f "$zc/CMakeLists.txt" ]; then
		zc=$(cd "$zc" && pwd -P)
		echo "sync $zc -> VM:~/$base/zyncoder"
		rsync -a --delete -e "$rs" --exclude=.git --exclude=build/ --exclude=__pycache__ "$zc/" "user@127.0.0.1:$base/zyncoder/"
	else
		echo "warning: no zyncoder next to $src: the zynmidirouter tests will skip" >&2
	fi
	if [ -d "$src/../zynthian-data/snapshots" ]; then
		echo "sync $(cd "$src/../zynthian-data/snapshots" && pwd -P) -> VM:~/$base/zynthian-data/snapshots"
		rsync -a --delete -e "$rs" "$src/../zynthian-data/snapshots/" "user@127.0.0.1:$base/zynthian-data/snapshots/"
	else
		echo "warning: no zynthian-data/snapshots next to $src: the snapshot corpus tests will skip" >&2
	fi
}

# The last pytest summary line ("== 10 passed, 2 skipped in 3.1s ==") of a log
summary_of() { sed 's/\x1b\[[0-9;]*m//g' "$1" | grep -E '^=+ .* in [0-9.]+s' | tail -n 1 | sed 's/^=* *//; s/ *=*$//'; }

run_tests() {
	n=$(tree_name "$(checkout)")
	vm_ssh "test -f ~/$base/$n/run_tests.sh" || { echo "no tree $n in the VM: run sync first" >&2; exit 1; }
	mode=default
	case ${1:-} in default | gui | native | all) mode=$1; shift ;; esac
	modes=$mode
	[ "$mode" != all ] || modes="default gui native"
	colour=
	[ ! -t 1 ] || colour="PY_COLORS=1"
	log=$(mktemp -d)
	trap 'rm -rf "$log"' EXIT
	start=$(date +%s)
	# One run at a time per tree (flock): the native build directory is shared
	pre="cd ~/$base/$n && . /etc/profile.d/zyntest.sh && export PYTHONUNBUFFERED=1 $colour && exec 9>.zyntest.lock && flock 9"
	if [ $build = 1 ]; then
		echo "== building the native libraries (tests/native/build_native.sh)"
		vm_ssh "$pre && tests/native/build_native.sh" || echo "warning: the native build failed (tests of missing libraries skip)" >&2
	fi
	rc=0
	for m in $modes; do
		echo "== run_tests.sh $m $*"
		arg=$m
		[ "$m" != default ] || arg=
		t0=$(date +%s)
		{ r=0; vm_ssh "$pre && ./run_tests.sh $arg $(q "$@")" 2>&1 || r=$?; echo $r > "$log/$m.rc"; } | tee "$log/$m.log"
		echo "$(( $(date +%s) - t0 ))" > "$log/$m.time"
		r=$(cat "$log/$m.rc")
		[ "$r" = 0 ] || [ "$rc" != 0 ] || rc=$r
	done
	if [ "$mode" = all ]; then
		echo
		echo "== summary ($(( $(date +%s) - start )) s in all, native build included)"
		for m in $modes; do
			printf '%-8s exit %s, %4s s: %s\n' "$m" "$(cat "$log/$m.rc")" "$(cat "$log/$m.time")" "$(summary_of "$log/$m.log")"
		done
	fi
	return "$rc"
}

case $cmd in
	start) start_vm ;;
	stop) stop_vm ;;
	status)
		if pid=$(vm_pid); then
			echo "running: PID $pid, SSH $port (ssh -p $port user@127.0.0.1), directory $dir"
			vm_ssh "df -h / | tail -n 1 | awk '{print \"disk: \" \$3 \" used, \" \$4 \" free\"}'
				cat /opt/jack/.apk 2>/dev/null | sed 's/^/jack: /' || echo 'not set up (setup)'
				echo trees: \$(ls ~/$base 2>/dev/null)" || echo "no SSH (booting? setup?)"
		else
			echo "not running (directory $dir)"
		fi
		;;
	setup) setup_vm ;;
	sync) sync_tree "$@" ;;
	run) run_tests "$@" ;;
	shell)
		n=$(tree_name "$(checkout)")
		# shellcheck disable=SC2086
		if [ $# -eq 0 ]; then
			ssh $ssh_opts -t -p "$port" user@127.0.0.1 "cd ~/$base/$n 2>/dev/null; exec \$SHELL -l"
		else
			vm_ssh "cd ~/$base/$n 2>/dev/null; . /etc/profile.d/zyntest.sh; $*"
		fi
		;;
	*) usage 1 ;;
esac
