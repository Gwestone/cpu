SIM           		?= verilator
TOPLEVEL_LANG  		= verilog
VERILOG_SOURCES 	+= $(PWD)/rtl/cpu_types.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/alu_types.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/load_types.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/main.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/alu.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/alu_controller.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/alu_b_decoder.sv
VERILOG_SOURCES 	+= $(PWD)/rtl/alu_mask_decoder.sv
COCOTB_TOPLEVEL 	= main
COCOTB_TEST_MODULES += tests.RV32I_ISA_tb,tests.RV64I_ISA_tb

EXTRA_ARGS += --coverage
EXTRA_ARGS += --trace --trace-structs

include $(shell cocotb-config --makefiles)/Makefile.sim
