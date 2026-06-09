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

    dut.data.value = 0b0000000
    dut.reset.value = 0

    for _ in range(10):
        dut.clk.value = 0
        await Timer(1, unit="ns")
        dut.clk.value = 1
        await Timer(1, unit="ns")

    cocotb.log.info("response is %s", dut.message.value)
    assert dut.message.value == dut.data.value


@cocotb.test()
async def my_second_test(dut):
    """Try accessing the design."""

    dut.data.value = 0b0000000
    dut.reset.value = 0

    cocotb.start_soon(generate_clock(dut))  # run the clock "in the background"

    await Timer(10, unit="ns")  # wait a bit
    await FallingEdge(dut.clk)  # wait for falling edge/"negedge"

    cocotb.log.info("response is %s", dut.message.value)
    assert dut.message.value == dut.data.value
