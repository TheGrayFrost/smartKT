##############################################################
#
#                   DO NOT EDIT THIS FILE!
#
##############################################################

# If the tool is built out of the kit, PIN_ROOT must be specified in the make invocation and point to the kit root.

PIN_ROOT := $(shell cd ../PIN && pwd)
CONFIG_ROOT := $(PIN_ROOT)/source/tools/Config
include $(CONFIG_ROOT)/makefile.config
include makefile.rules
include $(CONFIG_ROOT)/makefile.default.rules

ifndef run
run := 1
endif

CC := gcc
CXX := g++
CFLAGS := -gdwarf-4
CXXFLAGS := -gdwarf-4

.SECONDARY: 

.PRECIOUS: %.dump %.out %.xml #%.symtab %_static.offset


memtracker.cpp: memtracker.h
	@touch memtracker.cpp
%.out: %.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
%.out: %.c
	$(CC) $(CFLAGS) $< -o $@
%.so: %.c
	gcc -gdwarf-4 -fPIC -shared $^ -o $@
main.out: main.o lib.so
	gcc -gdwarf-4 -rdynamic $^ -o $@ -Wl,-rpath,.
%.out.address: statinfo/%.address
	cp $< statinfo/$@
%.dump: %.out %.out.address ./obj-intel64/memtracker.so
	../PIN/pin -t obj-intel64/memtracker.so inp="$(inp)" run=$(run) exe=$< -- ./$< $(inp) > op.txt


cleaner:
	make clean


# %.dd: %.out
# 	dwarfdump $< > $@
# %.dump: %.out %.dd ./obj-intel64/memtracker.so
# 	../PIN/pin -t obj-intel64/memtracker.so -- ./$< > op.txt
# %.symtab: %.out
# 	readelf -sW $< | grep "OBJECT" > $@
# %_static.offset: %.symtab final_global.offset merge
# 	awk -f merge $< FS="\t" final_global.offset > $@


##############################################################
#
#                   DO NOT EDIT THIS FILE!
#
##############################################################
