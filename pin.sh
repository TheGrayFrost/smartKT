#!/bin/bash
set -x # echo on

# even though the exe and the input file pollute the PIN workspace
# they have to be copied as is as many times the executables does checks
# like it may check the extension of the file as being .png etc

keep="true"

P=$(pwd)								# save current location
exe=${1##*/}							# extract executable and input filename

typeset -i runid nruns
nruns=$4
runid=$3

cp $1 PIN/Work/$exe.out					# copy executable to pin folder
rm -rf PIN/Work/statinfo/
mkdir PIN/Work/statinfo/
# copy the static linakge files into pin folder
find $2 -maxdepth 1 -type f -regex ".*\.\(calls.tokens\|funcargs\|offset\|address\)" -exec cp -t PIN/Work/statinfo/ {} +

if [ $# -eq 5 ]
then
	inp=$5
else
	inp=""
fi

cd PIN/Work										# move to pin folder
chmod +x $exe.out								# make .out runnable

makerun()
{
	local i=$1
	make inp="$inp" run=$i exe=$exe $exe.dump		# create the dump
	python pass2.py ${exe}_$i.dump	dynamic_$i.xml	# add dump info to xml
	cp ${exe}_$i.dump $2							# copy back the output folder
}

typeset -i i
for ((i=1;i<=nruns;++i)); do
	makerun ${runid}_${i} $2 &
done
wait

> dynamic.xml
for ((i=1;i<=nruns;++i)); do
	cat dynamic_${runid}_$i.xml >> dynamic.xml
done

if [ "$keep" = "true" ]
then
	cp dynamic.xml $2/final_dynamic.xml
else
	mv $exe.dump $2
	mv dynamic.xml $2/final_dynamic.xml
	rm $exe.out
	rm -rf statinfo/
	rm op.txt
fi

# # make ./obj-intel64/memtracker.so		# build the pin so
# # readelf -sW $exe.out | grep "OBJECT" > $exe.symtab	# collect its symtab
# # awk -f merge $exe.symtab FS="\t" final_global.offset > $exe_global.offset	# link with final_global.offset
# # ../PIN/pin -t obj-intel64/memtracker.so -- ./$exe.out $inp > op.txt
