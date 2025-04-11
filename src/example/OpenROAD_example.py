import sys
from OpenROAD_helpers import *
import argparse

parser = argparse.ArgumentParser(description="Example script to perform timing optimization techniques using OpenROAD.")
parser.add_argument("-d", default="ac97_top", help="Give the design name")
parser.add_argument("-t", default="ASAP7", help="Give the technology node")
args = parser.parse_args() 

# Load the design using OpenROAD Python APIs
tech, design = load_design(args.d, True)
timing = Timing(design)
db = ord.get_db()
chip = db.getChip()
block = ord.get_db_block()
tech = ord.get_db_tech()


# --- Gate sizing ---

print("\n# --- Gate sizing ---")
timing.makeEquivCells()
# First pick an instance
inst = block.findInst("input1")
# Then get the library cell information
inst_master = inst.getMaster()
print("-----------Reference library cell-----------")
print(inst_master.getName())
print("-----Library cells with different sizes-----")
equiv_cells = timing.equivCells(inst_master)
for equiv_cell in equiv_cells:
  print(equiv_cell.getName())

# Perform gate sizing
target_master = "BUFx4_ASAP7_75t_R"
target_master_ptr = db.findMaster(target_master)
inst.swapMaster(target_master_ptr)
print("----Change to the following library cell----")
print(inst.getMaster().getName())

# --- Vt swap ---
target_master = "BUFx4_ASAP7_75t_SL"
target_master_ptr = db.findMaster(target_master)
inst.swapMaster(target_master_ptr)
print("----Change to the following library cell----")
print(inst.getMaster().getName())

# --- Buffer insertion ---
print("\n# --- Buffer insertion ---")
def insert_buffer(net, buf_cell):
    global block
    global db

    source_net = block.findNet(net)
    for pin in source_net.getITerms():
        if pin.isOutputSignal():
            source_pin = pin
    source_inst = source_pin.getInst()
    for pin in source_inst.getITerms():
        if pin.getSigType() == 'POWER':
            power_net = pin.getNet()
        elif pin.getSigType() == 'GROUND':
            gnd_net = pin.getNet()
    # Find the master instance named 'BUF_X2'
    mast = db.findMaster(buf_cell)
    # Create a new instance named 'new_inst_1' using the 'BUF_X2' master
    new_inst = odb.dbInst_create(block,mast,'new_buffer_1')
    # Create a new net
    new_net = odb.dbNet_create(block,'new_buffer_net_1')
    # Disconnect the source pin
    source_pin.disconnect()
    # Connect the source pin to the new net
    source_pin.connect(new_net)

    # Connect the pins of the new instance
    for pin in new_inst.getITerms():
        if pin.isInputSignal():
            pin.connect(new_net)
        elif pin.isOutputSignal():
            pin.connect(source_net)
        elif pin.getSigType() == 'POWER':
            pin.connect(power_net)
        elif pin.getSigType() == 'GROUND':
            pin.connect(gnd_net)

print("net1 connection before buffer insertion")
get_connection("net1")
insert_buffer("net1", "BUFx2_ASAP7_75t_R")
get_connection("net1")
print("net1 connection after buffer insertion")

# --- Gate cloning ---
print("\n# --- Gate cloning ---")
def clone_gate(inst_name, new_inst_name):
    global block
    global db

    # Find the original instance
    orig_inst = block.findInst(inst_name)
    if not orig_inst:
        print(f"Error: Instance {inst_name} not found.")
        return

    # Find the master cell of the original instance
    mast = orig_inst.getMaster()

    # Create a new instance using the same master cell
    cloned_inst = odb.dbInst_create(block, mast, new_inst_name)

    power_net = None
    gnd_net = None

    # Identify input and output nets
    output_net = None
    for pin in orig_inst.getITerms():
        sig_type = pin.getSigType()

        if pin.isInputSignal():
            # Connect the cloned gate's input to the same net
            cloned_pin = cloned_inst.findITerm(pin.getMTerm().getName())
            cloned_pin.connect(pin.getNet())

        elif pin.isOutputSignal():
            output_net = pin.getNet()  # Get the output net of the original instance
            output_pin = pin

        elif sig_type == 'POWER':
            power_net = pin.getNet()
        elif sig_type == 'GROUND':
            gnd_net = pin.getNet()

    if output_net is None:
        print(f"Error: No output net found for {inst_name}.")
        return

    # Create a new net for the cloned gate's output
    new_net = odb.dbNet_create(block, f"{new_inst_name}_out_net")
    
    # Connect the cloned gate's output to the new net
    cloned_output_pin = cloned_inst.findITerm(output_pin.getMTerm().getName())
    cloned_output_pin.connect(new_net)

    # Get all sink pins of the original instance's output net
    sink_pins = [pin for pin in output_net.getITerms() if pin.getInst() != orig_inst]

    # Move half of the sink pins to the cloned instance's output net
    num_sinks_to_move = len(sink_pins) // 2
    for i, sink_pin in enumerate(sink_pins):
        if i < num_sinks_to_move:
            sink_pin.disconnect()
            sink_pin.connect(new_net)

    # Connect power and ground to the cloned gate
    for pin in cloned_inst.getITerms():
        sig_type = pin.getSigType()
        if sig_type == 'POWER' and power_net:
            pin.connect(power_net)
        elif sig_type == 'GROUND' and gnd_net:
            pin.connect(gnd_net)

    print(f"Cloned gate {inst_name} as {new_inst_name} and moved {num_sinks_to_move} sink pins.")

# Example Usage:
get_inst_connection("_299_")
clone_gate("_299_", "_299_clone")
get_inst_connection("_299_")
get_inst_connection("_299_clone")

# --- Logic restructuring ---
# In this example a 4 input OR is split into 3 two input OR gates
target_inst = '_436_'
inst = block.findInst(target_inst)

master = 'OR2x2_ASAP7_75t_R'
master_ptr = db.findMaster(master)

# Creating new instances and nets
new_inst1 = odb.dbInst_create(block, master_ptr, "new_OR_1")
new_inst2 = odb.dbInst_create(block, master_ptr, "new_OR_2")
new_inst3 = odb.dbInst_create(block, master_ptr, "new_OR_3")
new_net1 = odb.dbNet_create(block, "new_OR_1_out_net")
new_net2 = odb.dbNet_create(block, "new_OR_2_out_net")

in_nets = []
# Getting the input, output and PG nets of original OR gate
for pin in inst.getITerms():
    sig_type = pin.getSigType()
    if pin.isOutputSignal():
        out_net = pin.getNet()
    elif pin.isInputSignal():
        in_nets.append(pin.getNet())
    elif sig_type == 'POWER':
        power_net = pin.getNet()
    elif sig_type == 'GROUND':
        gnd_net = pin.getNet()

# Connecting the PG pins of newly added OR gates
connect_pg(new_inst1,power_net,gnd_net)
connect_pg(new_inst2,power_net,gnd_net)
connect_pg(new_inst3,power_net,gnd_net)
# Connecting signal pins of OR gate 1
i = 0
for pin in new_inst1.getITerms():
    if pin.isOutputSignal():
        pin.connect(new_net1)
    elif pin.isInputSignal():
        pin.connect(in_nets[i])
        i=i+1
# Connecting signal pins of OR gate 2
for pin in new_inst2.getITerms():
    if pin.isOutputSignal():
        pin.connect(new_net2)
    elif pin.isInputSignal():
        pin.connect(in_nets[i])
        i=i+1
i = 0
# Connecting signal pins of OR gate 3
for pin in new_inst3.getITerms():
    if pin.isOutputSignal():
        pin.connect(out_net)
    elif pin.isInputSignal():
        if i:
            pin.connect(new_net2)
        else:
            pin.connect(new_net1)
            i=i+1
odb.dbInst_destroy(inst)     
