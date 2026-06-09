import cocotb
from cocotb.triggers import FallingEdge, Timer


async def generate_clock(dut):
    """Generate clock pulses."""

    for _ in range(10):
        dut.clk.value = 0
        await Timer(1, unit="ns")
        dut.clk.value = 1
        await Timer(1, unit="ns")


@cocotb.test()
async def my_first_test(dut):
    """Try accessing the design."""

    for _ in range(10):
        dut.clk.value = 0
        await Timer(1, unit="ns")
        dut.clk.value = 1
        await Timer(1, unit="ns")

    cocotb.log.info("my_signal_1 is %s", dut.my_signal_1.value)
    assert dut.my_signal_2.value == 0


@cocotb.test()
async def my_second_test(dut):
    """Try accessing the design."""

    cocotb.start_soon(generate_clock(dut))  # run the clock "in the background"

    await Timer(5, unit="ns")  # wait a bit
    await FallingEdge(dut.clk)  # wait for falling edge/"negedge"

    cocotb.log.info("my_signal_1 is %s", dut.my_signal_1.value)
    assert dut.my_signal_2.value == 0
