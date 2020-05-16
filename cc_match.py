#!/usr/bin/env python3
# This was written in like an hour, so please forgive me.

import pathlib, sys, re
import upco_filesequence

if __name__ == "__main__":

	# User-configurable settings ==================================================
	
	# Vendor codes and their dispaly names.
	# If not in this list, vendor code will be displayed as-is.
	# User upper-case vendor codes in this dict.
	vendor_names  = {"WTA":"Weta Digital"}

	# Regex patterns to identify VFX ID and vendor codes
	pat_vfx_id = re.compile(r"^\d{3}[a-z]?_([a-z]{3})_\d{4}", re.I)
	pat_vendor_code = re.compile(r".+_COMP_(?P<vendor_code>[a-z]{3})", re.I)

	# Location of .nk template file
	path_template = pathlib.Path(__file__).parent / "template.txt"


	# Main script below ===========================================================

	usage = f"Usage: {__file__} /path/to/cc/folder/ [/path/to/shots/folder/] [...]"
	
	glob_cc  = []
	path_inputs = []

	if len(sys.argv) < 2:
		sys.stderr.write(f"{usage}\n")
		exit(1)

	# Check that inputs are valid folders, and find .CC files
	for path in {pathlib.Path(x) for x in sys.argv[1:]}:
		if not path.is_dir(): continue
		path_inputs.append(path)
		glob_cc.extend(path.rglob("*.[cC][cC]"))
	
	if not len(path_inputs):
		sys.stderr.write(f"No folders found.\n{usage}\n")
		exit(1)
	elif not len(glob_cc):
		sys.stderr.write(f"No .CC files found.\n{usage}\n")
		exit(1)
	
	# Make sure nothing crazy happened
	while True:
		choice = input(f"Found {len(glob_cc)} .CC file(s).  Continue? [y/n]: ").strip().lower()
		if not len(choice) or choice[0] not in ['y','n']:
			continue
		elif choice[0] == 'n':
			sys.stdout.write("I see.\n")
			exit(0)
		else: break
	
	sys.stdout.write("\nSearching for shots...\n\n")

	failed  = {}
	success = {}

	# Find corresponding EXR sequences based on CC named + _EXR
	for file_cc in glob_cc:

		# Verify .cc file begins with a VFX ID
		match = pat_vfx_id.match(file_cc.stem)
		if not match:
			failed.update({file_cc: "CC filename does not start with a VFX ID."})
			continue

		vfx_id = match.group(0)

		seq_exr = []
		{seq_exr.extend(upco_filesequence.Sequencer(x.rglob(f"{vfx_id}*/{vfx_id}*.[eE][xX][rR]")).sequences) for x in path_inputs}

		# If the sequencer detects more than one EXR sequence, or none
		if len(seq_exr) != 1:
			failed.update({file_cc: "EXRs break in sequence." if len(seq_exr) else f"No EXR sequences found for VFX ID {vfx_id}."})
			continue

		seq_exr = seq_exr[0]

		match = pat_vendor_code.match(seq_exr.parent.name)
		if not match:
			failed.update({file_cc: "No vendor code found in EXR folder name."})
			continue

		# Prepare field data for .nk file
		vendor_name = vendor_names.get(match.group("vendor_code").upper(), match.group("vendor_code").upper())
		shot_name = seq_exr.parent.name[:-len("_EXR")] if seq_exr.parent.name.lower().endswith("_exr") else seq_exr.parent.name
		
		sys.stdout.write(f"{file_cc.name}\t-> {pathlib.PurePath(seq_exr.grouped())}\n")
		success.update({file_cc: {
			"frame_first": seq_exr.min,
			"frame_last": seq_exr.max,
			"source_seq": str(pathlib.Path(seq_exr.parent, f"{seq_exr.basename}%{str(seq_exr.padding).zfill(2)}d{seq_exr.ext}").resolve(strict=False)).replace('\\', '/'),
			"source_cc": str(file_cc.resolve(strict=False)).replace('\\','/'),
			"shot_name": seq_exr.parent.name,
			"vendor_name": vendor_name,
			"file_prores": str(pathlib.Path("D:","Output","prepped_for_studio", seq_exr.parent.parent, f"{seq_exr.parent.name}_prores4444.mov").resolve(strict=False)).replace('\\','/')
		}})

	# Make sure nothing crazy happened
	sys.stdout.write(f"\n{len(success.keys())} shots matched successfully; {len(failed.keys())} failed.\n")
	while True:
		choice = input("Write Nuke scripts? [Yes/No/Details]: ").strip().lower()
		if not len(choice) or choice[0] not in ['y','n','d']:
			continue

		elif choice[0] == 'd':

			# No failures
			if not len(failed):
				sys.stdout.write(f"No errors to report.\n")
				continue

			# Print failures
			sys.stdout.write(f"\nThese shots failed:\n")
			for fail in failed:
				sys.stdout.write(f"{fail}:\t{failed.get(fail)}\n")
			sys.stdout.write('\n')
		
		elif choice[0] == 'n':
			sys.stdout.write("I see.\n")
			exit(0)
		else: break

	# Read template
	txt_template = path_template.read_text()
	sys.stdout.write('\n')
	
	for shot in success:
		fields = success.get(shot)
		path_nuke = pathlib.Path(fields.get("source_seq")).parent.parent / f"{fields.get('shot_name')}.nk"
		#print(path_nuke)
		
		try:
			with path_nuke.open('w') as file_nuke:
				print(txt_template.format(**fields), file=file_nuke)
		
			sys.stdout.write(f"{fields.get('shot_name')}\t-> {path_nuke}\n")
		except Exception as e:
			sys.stderr.write(f"\nError writing {path_nuke.name}: {e}\n")

