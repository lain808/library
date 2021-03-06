import sys
import os
import glob
import json
import time
import build
import zipfile
import re


PACKAGES_DIR = "../packages"
SCREENSHOTS_DIR = "../screenshots"
MANIFESTS_DIR = "manifests"
RACK_USER_DIR = "$HOME/.Rack"
RACK_USER_PLUGIN_DIR = os.path.join(RACK_USER_DIR, "plugins-v1")

# Update git before continuing
build.system("git pull")
# build.system("git submodule sync")
build.system("git submodule update --init --recursive")

plugin_filenames = sys.argv[1:]

# Default to all repos, so all out-of-date repos are built
if not plugin_filenames:
	plugin_filenames = glob.glob("repos/*")

updated_slugs = set()

for plugin_filename in plugin_filenames:
	(plugin_basename, plugin_ext) = os.path.splitext(os.path.basename(plugin_filename))
	# Extract manifest from plugin dir or package
	if os.path.isdir(plugin_filename):
		manifest_filename = os.path.join(plugin_filename, "plugin.json")
		try:
			# Read manifest
			with open(manifest_filename, "r") as f:
				manifest = json.load(f)
		except IOError:
			# Skip plugins without plugin.json
			continue
		slug = manifest['slug']
		version = manifest['version']
	elif plugin_ext == ".zip":
		m = re.match(r'^(.*)-(.*?)-(.*?)$', plugin_basename)
		slug = m[1]
		version = m[2]
		arch = m[3]
		# Open ZIP
		z = zipfile.ZipFile(plugin_filename)
		# Unzip manifest
		manifest_filename = f"{slug}/plugin.json"
		with z.open(manifest_filename) as f:
			manifest = json.load(f)
		if manifest['slug'] != slug:
			raise Exception(f"Manifest slug does not match filename slug {slug}")
		if manifest['version'] != version:
			raise Exception(f"Manifest slug does not match filename slug {slug}")
	else:
		raise Exception(f"Plugin {plugin_filename} is not a valid format")

	# Get library manifest
	library_manifest_filename = os.path.join(MANIFESTS_DIR, f"{slug}.json")

	if os.path.isdir(plugin_filename):
		# Check if the library manifest is up to date
		try:
			with open(library_manifest_filename, "r") as f:
				library_manifest = json.load(f)
			if library_manifest and version == library_manifest['version']:
				continue
		except IOError:
			pass

		# Build repo
		print()
		print(f"Building {slug}")
		try:
			build.delete_stage()
			build.build(plugin_filename)
			build.system(f'cp -vi stage/* "{PACKAGES_DIR}"')
			build.system(f'cp -vi stage/* "{RACK_USER_PLUGIN_DIR}"')
		except Exception as e:
			print(e)
			print(f"{slug} build failed")
			input()
			continue
		finally:
			build.delete_stage()

		# Open plugin issue thread
		os.system(f"qutebrowser 'https://github.com/VCVRack/library/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+in%3Atitle+{slug}' &")

	elif plugin_ext == ".zip":
		# Review manifest for errors
		print(json.dumps(manifest, indent="  "))
		print("Press enter to approve manifest")
		input()

		# Copy package
		package_dest = os.path.join(PACKAGES_DIR, os.path.basename(plugin_filename))
		build.system(f'cp "{plugin_filename}" "{package_dest}"')
		build.system(f'touch "{package_dest}"')
		if arch == 'lin':
			build.system(f'cp "{plugin_filename}" "{RACK_USER_PLUGIN_DIR}"')

	# Copy manifest
	with open(library_manifest_filename, "w") as f:
		json.dump(manifest, f, indent="  ")

	# Delete screenshot cache
	screenshots_dir = os.path.join(SCREENSHOTS_DIR, slug)
	build.system(f'rm -rf "{screenshots_dir}"')

	updated_slugs.add(slug)


if not updated_slugs:
	print("Nothing to build")
	exit(0)


print("Press enter to upload packages and push library repo")
input()

# Upload packages
build.system("cd ../packages && make upload")

# Commit repository
build.system("git add manifests")
built_slugs_str = ", ".join(updated_slugs)
build.system(f"git commit -m 'Update manifest for {built_slugs_str}'")
build.system("git push")

print()
print(f"Updated {built_slugs_str}")
print("Remember to generate and upload screenshots")
