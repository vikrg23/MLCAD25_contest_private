import os
import pdn, odb, utl
from openroad import Tech, Design, Timing
import openroad as ord
from collections import defaultdict
from pathlib import Path

def load_design(design_name, verilog = False):
  tech = Tech()
  libDir = Path("../../platform/ASAP7/lib/")
  lefDir = Path("../../platform/ASAP7/lef/")
  designDir = Path("../../designs/%s"%design_name)

  # Read technology files
  libFiles = libDir.glob('*.lib')
  lefFiles = lefDir.glob('*.lef')
  for libFile in libFiles:
    tech.readLiberty(libFile.as_posix())
  tech.readLef("%s/%s"%(lefDir.as_posix(), "asap7_tech_1x_201209_tech.lef"))
  for lefFile in lefFiles:
    tech.readLef(lefFile.as_posix())
  design = Design(tech)

  # Read design files
  if verilog:
    verilogFile = "%s/%s.v"%(designDir.as_posix(), design_name)
    design.readVerilog(verilogFile)
    design.link(design_name)
  else:
    defFile = "%s/%s_fp.def.gz"%(designDir.as_posix(), design_name)
    design.readDef(defFile)

  # Read the SDC file, SPEF file, and set the clocks
  sdcFile = "%s/%s.sdc"%(designDir.as_posix(), design_name)
  design.evalTclString("read_sdc %s"%sdcFile)
  design.evalTclString("source ../../platform/ASAP7/setRC.tcl")
  
  # Global connect
  VDDNet = design.getBlock().findNet("VDD")
  if VDDNet is None:
    VDDNet = odb.dbNet_create(design.getBlock(), "VDD")
  VDDNet.setSpecial()
  VDDNet.setSigType("POWER")
  VSSNet = design.getBlock().findNet("VSS")
  if VSSNet is None:
    VSSNet = odb.dbNet_create(design.getBlock(), "VSS")
  VSSNet.setSpecial()
  VSSNet.setSigType("GROUND")
  design.getBlock().addGlobalConnect(None, ".*", "VDD", VDDNet, True)
  design.getBlock().addGlobalConnect(None, ".*", "VSS", VSSNet, True)
  design.getBlock().globalConnect()

  return tech, design

def get_connection(net):
  block = ord.get_db_block()
  net = block.findNet(net)
  sink_pins = []
  for p in net.getITerms():
    if p.isOutputSignal():
      d_pin = p
    else:
      sink_pins.append(p)
  print("Driver: ",d_pin.getName())
  for p in sink_pins:
    print("Sink: ",p.getName())

def get_inst_connection(inst):
  block = ord.get_db_block()
  inst = block.findInst(inst)
  in_pins = []
  out_pins = []
  for pin in inst.getITerms():
    if pin.isOutputSignal():
      out_pins.append(pin)
    elif pin.isInputSignal():
      in_pins.append(pin)
  for pin in in_pins:
    driver = [x for x in pin.getNet().getITerms() if x.isOutputSignal()][0]
    print("Input pin ",pin.getName(),"is connected to ",driver.getName())
  for pin in out_pins:
    print("Connections to output pin ",pin.getName())
    for p in pin.getNet().getITerms():
      if p.isInputSignal():
        print(p.getName())


def connect_pg(inst, power_net, gnd_net):
  for pin in inst.getITerms():
    sig_type = pin.getSigType()
    if sig_type == 'POWER' and power_net:
      pin.connect(power_net)
    elif sig_type == 'GROUND' and gnd_net:
      pin.connect(gnd_net)
