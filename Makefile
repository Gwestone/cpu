SIM           		?= verilator
TOPLEVEL_LANG  		= verilog
VERILOG_SOURCES 	+= $(PWD)/rtl/main.v
COCOTB_TOPLEVEL 	= main
COCOTB_TEST_MODULES = tests.main_tb

EXTRA_ARGS += --coverage
EXTRA_ARGS += --trace --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim
