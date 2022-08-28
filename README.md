# duplicates
Simple python script for removing duplicated files. Program calculates md5sum for all found files and based on that finds duplicates. The script indexes files from the root directory and all subdirectories.

## Script arguments:
- -r / --root ;    root directory, starting point for the script 
- -d / --delete ;   if provided script will delete duplicated files

## Usage
<code>python3.8 duplicates.py -r /path/to/your/data</code>
