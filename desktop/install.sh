#!/bin/bash
#******************************************************************************
# ZYNTHIAN PROJECT: install zynthian for desktop Linux / Nura packages
#
#   desktop/install.sh <component> <destdir> [<source dir>]
#
# Components (each one becomes a package):
#   ui        zynthian-ui code and assets, zynlibs, launcher. Build the zynlibs first
#             (zynlibs/build.sh).
#   zyncoder  libzyncore.so and its Python module. <source dir>: the built zyncoder
#             checkout (default: ../zyncoder).
#   sys       configuration templates from zynthian-sys (default: ../zynthian-sys)
#   data      zynthian-data (default: ../zynthian-data)
#   help      zynthian-help (default: ../zynthian-help)
#
# Layout (PREFIX defaults to /usr):
#   $PREFIX/share/zynthian/{zynthian-ui,zynthian-sys,zynthian-data,zynthian-help}
#   $PREFIX/lib/zynthian/*.so
#   $PREFIX/bin/zynthian
#******************************************************************************

set -e

component="$1"
destdir="$2"
if [ -z "$component" ] || [ -z "$destdir" ]; then
	sed -n '4,20p' "$0" | sed 's/^# \{0,1\}//'
	exit 1
fi

ui_src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/usr}"
share_dir="$destdir$PREFIX/share/zynthian"
lib_dir="$destdir$PREFIX/lib/zynthian"
ui_dst="$share_dir/zynthian-ui"

# Copy a directory tree, leaving out git, build and cache files
copy_tree() {
	local src="$1" dst="$2"
	mkdir -p "$dst"
	(cd "$src" && find . \( -name .git -o -name build -o -name __pycache__ \) -prune -o \
		\( -type f -o -type l \) -print0 | tar --null -T - -cf -) | tar -C "$dst" -xf -
}

install_ui() {
	mkdir -p "$ui_dst" "$lib_dir" "$destdir$PREFIX/bin"
	for d in zyngui zyngine zynconf zynautoconnect fonts icons img; do
		copy_tree "$ui_src/$d" "$ui_dst/$d"
	done
	# Python modules of the zynlibs, without tests
	(cd "$ui_src" && find zynlibs -name '*.py' ! -name 'unit_tests.py' ! -name 'test.py' ! -name 'format_docs.py' -print0 |
		tar --null -T - -cf -) | tar -C "$ui_dst" -xf -
	install -m 755 "$ui_src/zynthian_main.py" "$ui_dst/"
	# Qt Quick UI (ZYNTHIAN_UI=qt), without the M0 spike; not in upstream trees (nura-builds'
	# builds of upstream zynthian-ui with the port patches: Tk only)
	if [ -d "$ui_src/zynqt" ]; then
		copy_tree "$ui_src/zynqt" "$ui_dst/zynqt"
		rm -rf "$ui_dst/zynqt/spike"
		install -m 755 "$ui_src/zynthian_qt_main.py" "$ui_dst/"
	fi
	install -m 644 "$ui_src/LICENSE.txt" "$ui_dst/"
	mkdir -p "$ui_dst/desktop"
	install -m 755 "$ui_src/desktop/zynthian_desktop.sh" "$ui_src/desktop/setup_desktop.sh" "$ui_dst/desktop/"
	install -m 644 "$ui_src/desktop/zynthian_desktop_env.sh" "$ui_src/desktop/zynthian_envars_desktop.sh" "$ui_dst/desktop/"
	# Help is a separate package, linked like in the git checkout
	ln -sfn ../zynthian-help "$ui_dst/help"

	for lib in zynsmf/build/libzynsmf.so zynseq/build/libzynseq.so zynaudioplayer/build/libzynaudioplayer.so \
		zynmixer/build/libzynmixer.so zynmixer/build/libzynmixer_mixbus.so zynclippy/build/libzynclippy.so; do
		install -m 755 "$ui_src/zynlibs/$lib" "$lib_dir/"
	done

	cat > "$destdir$PREFIX/bin/zynthian" <<-EOF
	#!/bin/sh
	export ZYNTHIAN_DIR="\${ZYNTHIAN_DIR:-$PREFIX/share/zynthian}"
	export ZYNTHIAN_LIB_DIR="\${ZYNTHIAN_LIB_DIR:-$PREFIX/lib/zynthian}"
	# Python packages bundled with the package (not packaged by the distribution)
	if [ -d "\$ZYNTHIAN_DIR/python" ]; then
		export PYTHONPATH="\$ZYNTHIAN_DIR/python\${PYTHONPATH:+:\$PYTHONPATH}"
	fi
	exec "\$ZYNTHIAN_DIR/zynthian-ui/desktop/zynthian_desktop.sh" "\$@"
	EOF

	# The UI's fonts (Audiowide, ...), found by Tk through fontconfig
	mkdir -p "$destdir$PREFIX/share/fonts"
	ln -sfn ../zynthian/zynthian-ui/fonts "$destdir$PREFIX/share/fonts/zynthian"
	chmod 755 "$destdir$PREFIX/bin/zynthian"

	# Byte-compile: the installed tree is read-only at run time
	python3 -m compileall -q -d "$PREFIX/share/zynthian/zynthian-ui" "$ui_dst" >/dev/null || true
}

install_zyncoder() {
	local src="${1:-$ui_src/../zyncoder}"
	mkdir -p "$lib_dir" "$ui_dst/zyncoder"
	install -m 755 "$src/build/libzyncore.so" "$lib_dir/"
	install -m 644 "$src/__init__.py" "$src/zyncore.py" "$ui_dst/zyncoder/"
	python3 -m compileall -q -d "$PREFIX/share/zynthian/zynthian-ui/zyncoder" "$ui_dst/zyncoder" >/dev/null || true
}

install_sys() {
	local src="${1:-$ui_src/../zynthian-sys}"
	copy_tree "$src/config" "$share_dir/zynthian-sys/config"
}

install_data() {
	copy_tree "${1:-$ui_src/../zynthian-data}" "$share_dir/zynthian-data"
}

install_help() {
	copy_tree "${1:-$ui_src/../zynthian-help}" "$share_dir/zynthian-help"
}

case "$component" in
	ui) install_ui ;;
	zyncoder) install_zyncoder "$3" ;;
	sys) install_sys "$3" ;;
	data) install_data "$3" ;;
	help) install_help "$3" ;;
	*) echo "Unknown component: $component"; exit 1 ;;
esac
