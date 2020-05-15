#!/usr/bin/env python3

import pathlib, sys
import upco_filesequence

if __name__ == "__main__":

	usage = f"Usage: {__file__} /path/to/cc/folder/ /path/to/shots/folder/ [...]"

	glob_cc  = []
	path_inputs = []

	path_template = pathlib.Path(__file__).parent / "template.txt"
	
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
		shot_name = f"{file_cc.stem}_EXR"
		glob_exr = []
		{glob_exr.extend(path.rglob(f"{shot_name}/")) for path in path_inputs}
		
		# Fail if no shots found, or more than one
		if len(glob_exr) != 1:
			failed.update({file_cc: "Multiple EXR sequences found." if len(glob_exr) else "No matching EXR sequences found."})
			continue
		
		seq_exr = upco_filesequence.Sequencer(glob_exr[0].glob(f"{shot_name}*.[eE][xX][rR]"))

		# If the sequencer detects more than one EXR sequence, or none
		if len(seq_exr.sequences) != 1:
			failed.update({file_cc: "EXRs break in sequence." if len(seq_exr.sequences) else "No EXR sequence found in folder."})
			continue

		seq_exr = seq_exr.sequences[0]
		
		sys.stdout.write(f"{file_cc.name}\t-> {pathlib.PurePath(seq_exr.grouped())}\n")
		success.update({file_cc: {
			"frame_first": seq_exr.min,
			"frame_last": seq_exr.max,
			"source_seq": str(pathlib.Path(seq_exr.parent, f"{seq_exr.basename}%{str(seq_exr.padding).zfill(2)}d{seq_exr.ext}").resolve(strict=False)).replace('\\', '/'),
			"source_cc": str(file_cc.resolve(strict=False)).replace('\\','/'),
			"shot_name": file_cc.stem,
			"prores_file": str(pathlib.Path("D:","Output","prepped_for_studio", seq_exr.parent.parent, f"{shot_name}_prores444.mov").resolve(strict=False)).replace('\\','/')
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
		path_nuke = pathlib.Path(fields.get("source_seq")).parent.parent / f"{fields.get('shot_name')}_EXR.txt"
		#print(path_nuke)
		
		try:
			with path_nuke.open('w') as file_nuke:
				print(txt_template.format(**fields), file=file_nuke)
		
			sys.stdout.write(f"{fields.get('shot_name')}\t-> {path_nuke}\n")
		except Exception as e:
			sys.stderr.write(f"\nError writing {path_nuke.name}: {e}\n")
