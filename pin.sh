#!/bin/bash
set -x # echo on

# even though the exe and the input file pollute the PIN workspace
# they have to be copied as is as many times the executables does checks
# like it may check the extension of the file as being .png etc

P=$(pwd)								# save current location
exe=${1##*/}							# extract executable and input filename
cp $1 PIN/Work/$exe.out					# copy executable to pin folder
rm -rf PIN/Work/statinfo/
mkdir PIN/Work/statinfo/
cp $2/* PIN/Work/statinfo/ || true		# copy the static results into pin

if [ $# -eq 3 ]
then
	inp=${3##*/}
	cp $3 PIN/Work/$inp					# copy input file to pin if specified
else
	inp=""
fi

cd PIN/Work								# move to pin folder
chmod +x $exe.out						# make .out runnable
make inp=$inp $exe.dump					# create the dump
python pass2.py $exe.dump				# add dump info to xml
mv $exe.dump $2
mv dynamic.xml $2/final_dynamic.xml

rm $exe.out
rm $inp || true
rm -rf statinfo/

# # make ./obj-intel64/memtracker.so		# build the pin so
# # readelf -sW $exe.out | grep "OBJECT" > $exe.symtab	# collect its symtab
# # awk -f merge $exe.symtab FS="\t" final_global.offset > $exe_global.offset	# link with final_global.offset
# # ../PIN/pin -t obj-intel64/memtracker.so -- ./$exe.out $inp > op.txt
