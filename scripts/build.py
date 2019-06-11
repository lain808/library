import os
import sys


RACK_SDK = os.path.abspath("Rack-SDK")
STAGE_DIR = "stage"
PACKAGE_DIR = "../packages"


def system(cmd):
	err = os.system(cmd)
	if err:
		raise Exception(f"Command failed with error {err}: {cmd}")


def stage_package(plugin_dir):
	system(f'mkdir -p {STAGE_DIR}')
	system(f'mv {plugin_dir}/dist/*.zip {STAGE_DIR}/')


def move_stage():
	system(f'mv -vi {STAGE_DIR}/* {PACKAGE_DIR}/')


def delete_stage():
	system(f'rm -rf {STAGE_DIR}')


def build_mac(plugin_dir):
	env = f'CC=x86_64-apple-darwin15-clang CXX=x86_64-apple-darwin15-clang++-libc++ STRIP=x86_64-apple-darwin15-strip RACK_DIR={RACK_SDK}'
	make = f'{env} make -j$(nproc) -C {plugin_dir}'
	system(f'{make} clean')
	system(f'{make} dist')
	stage_package(plugin_dir)
	system(f'{make} clean')


def build_win(plugin_dir):
	env = f'CC=x86_64-w64-mingw32-gcc CXX=x86_64-w64-mingw32-g++ STRIP=x86_64-w64-mingw32-strip RACK_DIR={RACK_SDK}'
	make = f'{env} make -j$(nproc) -C {plugin_dir}'
	system(f'{make} clean')
	system(f'{make} dist')
	stage_package(plugin_dir)
	system(f'{make} clean')


def build_lin(plugin_dir):
	make = f'make -j$(nproc)'
	plugin_abs = os.path.abspath(plugin_dir)
	# TODO Make this Docker image publicly available
	# It's essentially just Ubuntu 16.04 with plugin build dependencies installed, the workdir, and a user account set up so it matches my own machine's UID to solve file permissions issues.
	docker = f'docker run --rm -v {RACK_SDK}:/Rack-SDK -v {plugin_abs}:/workdir -w /workdir -u vortico -e RACK_DIR=/Rack-SDK rackplugin:1'
	system(f'{docker} {make} clean')
	system(f'{docker} {make} dist')
	stage_package(plugin_dir)
	system(f'{docker} {make} clean')


def build(plugin_dir):
	try:
		build_lin(plugin_dir)
		build_win(plugin_dir)
		build_mac(plugin_dir)
		move_stage()
	finally:
		delete_stage()


if __name__ == "__main__":
	plugin_dir = sys.argv[1]
	if not plugin_dir:
		raise "No plugin_dir given"
	build(plugin_dir)
