from openroad import Tech, Design, Timing
from pathlib import Path

tech_node = "ASAP7"
design_name = "ac97_top"
design_top_module_name = "ac97_top"

# Initialize OpenROAD objects and read technology files
tech = Tech()
# Set paths to library and design files
libDir = Path("../../platform/ASAP7/lib/")
lefDir = Path("../../platform/ASAP7/lef/")
designDir = Path("../../designs/%s"%design_name)

# Read all liberty (.lib) and LEF files from the library directories
libFiles = libDir.glob("*.lib")
techLefFiles = lefDir.glob("*tech.lef")
lefFiles = lefDir.glob('*.lef')

# Load liberty timing libraries
for libFile in libFiles:
    tech.readLiberty(libFile.as_posix())
# Load technology and cell LEF files  
for techLefFile in techLefFiles:
    tech.readLef(techLefFile.as_posix())
for lefFile in lefFiles:
    tech.readLef(lefFile.as_posix())

# Create design and read Verilog netlist
design = Design(tech)
verilogFile = "%s/%s.v"%(designDir.as_posix(), design_name)
design.readVerilog(verilogFile.as_posix())
design.link(design_top_module_name)

# Configure clock constraints
# Create 20ns period clock on clk port
#design.evalTclString(""create_clock -period 20 [get_ports clk] -name core_clock"")
#design.evalTclString(""set_propagated_clock [get_clocks {core_clock}]"")

# Read the SDC file, SPEF file, and set the clocks
sdcFile = "%s/%s.sdc"%(designDir.as_posix(), design_name)
design.evalTclString("read_sdc %s"%sdcFile)
design.evalTclString("source ../../platform/ASAP7/setRC.tcl")

# Initialize floorplan with core and die area
#floorplan = design.getFloorplan()
# Set die area to 60um x 50um
# Initialize floorplan with FreePDK45 site
#site = floorplan.findSite(""FreePDK45_38x28_10R_NP_162NW_34O"")
#utilization = 0.5
#aspect_ratio = 1.0
#leftSpace = design.micronToDBU(10)
#rightSpace = design.micronToDBU(10)
#topSpace = design.micronToDBU(10)
#bottomSpace = design.micronToDBU(10)
#floorplan.initFloorplan(utilization, aspect_ratio, bottomSpace, topSpace, leftSpace, rightSpace, site)
#floorplan.makeTracks()

# Configure and run I/O pin placement
#params = design.getIOPlacer().getParameters()
#params.setRandSeed(42)
#params.setMinDistanceInTracks(False)
#params.setMinDistance(design.micronToDBU(0))
#params.setCornerAvoidance(design.micronToDBU(0))
## Place I/O pins on metal8 (horizontal) and metal9 (vertical) layers
#design.getIOPlacer().addHorLayer(design.getTech().getDB().getTech().findLayer(""metal8""))
#design.getIOPlacer().addVerLayer(design.getTech().getDB().getTech().findLayer(""metal9""))
#IOPlacer_random_mode = True
#design.getIOPlacer().runAnnealing(IOPlacer_random_mode)
#
## Place macro blocks if present
#macros = [inst for inst in design.getBlock().getInsts() if inst.getMaster().isBlock()]
#if len(macros) > 0:
#    mpl = design.getMacroPlacer()
#    block = design.getBlock()
#    core = block.getCoreArea()
#    mpl.place(
#        num_threads = 64, 
#        max_num_macro = len(macros)//8,
#        min_num_macro = 0,
#        max_num_inst = 0,
#        min_num_inst = 0,
#        tolerance = 0.1,
#        max_num_level = 2,
#        coarsening_ratio = 10.0,
#        large_net_threshold = 50,
#        signature_net_threshold = 50,
#        halo_width = 2.0,
#        halo_height = 2.0,
#        fence_lx = block.dbuToMicrons(core.xMin()),
#        fence_ly = block.dbuToMicrons(core.yMin()),
#        fence_ux = block.dbuToMicrons(core.xMax()),
#        fence_uy = block.dbuToMicrons(core.yMax()),
#        area_weight = 0.1,
#        outline_weight = 100.0,
#        wirelength_weight = 100.0,
#        guidance_weight = 10.0,
#        fence_weight = 10.0,
#        boundary_weight = 50.0,
#        notch_weight = 10.0,
#        macro_blockage_weight = 10.0,
#        pin_access_th = 0.0,
#        target_util = 0.25,
#        target_dead_space = 0.05,
#        min_ar = 0.33,
#        snap_layer = 4,
#        bus_planning_flag = False,
#        report_directory = """"
#    )

# Read floorplan def file
defFile = "%s/%s_fp.def.gz"%(designDir.as_posix(), design_name)
design.readDef(defFile)

# Configure and run global placement
gpl = design.getReplace()
gpl.setTimingDrivenMode(False)
gpl.setRoutabilityDrivenMode(True)
gpl.setUniformTargetDensityMode(True)
# Limit initial placement iterations and set density penalty
gpl.setInitialPlaceMaxIter(10)
gpl.setInitDensityPenalityFactor(0.05)
gpl.doInitialPlace(threads = 4)
gpl.doNesterovPlace(threads = 4)
gpl.reset()

# Run initial detailed placement
site = design.getBlock().getRows()[0].getSite()
# Allow 1um x-displacement and 3um y-displacement
max_disp_x = int(design.micronToDBU(1))
max_disp_y = int(design.micronToDBU(3))
# Remove filler cells to be able to move the cells
design.getOpendp().removeFillers()
design.getOpendp().detailedPlacement(max_disp_x, max_disp_y, "", False)

import pdn, odb
# Configure power delivery network
# Set up global power/ground connections
for net in design.getBlock().getNets():
    if net.getSigType() == "POWER" or net.getSigType() == "GROUND":
        net.setSpecial()
VDD_net = design.getBlock().findNet("VDD")
VSS_net = design.getBlock().findNet("VSS")
switched_power = None
secondary = list()
# Create VDD/VSS nets if they don't exist
if VDD_net == None:
    VDD_net = odb.dbNet_create(design.getBlock(), "VDD")
    VDD_net.setSpecial()
    VDD_net.setSigType("POWER")
if VSS_net == None:
    VSS_net = odb.dbNet_create(design.getBlock(), "VSS")
    VSS_net.setSpecial()
    VSS_net.setSigType("GROUND")

# Connect power pins to global nets
design.getBlock().addGlobalConnect(region = None,
    instPattern = ".*", 
    pinPattern = "^VDD$",
    net = VDD_net, 
    do_connect = True)
design.getBlock().addGlobalConnect(region = None,
    instPattern = ".*",
    pinPattern = "^VDDPE$",
    net = VDD_net,
    do_connect = True)
design.getBlock().addGlobalConnect(region = None,
    instPattern = ".*",
    pinPattern = "^VDDCE$",
    net = VDD_net,
    do_connect = True)
design.getBlock().addGlobalConnect(region = None,
    instPattern = ".*",
    pinPattern = "^VSS$",
    net = VSS_net, 
    do_connect = True)
design.getBlock().addGlobalConnect(region = None,
    instPattern = ".*",
    pinPattern = "^VSSE$",
    net = VSS_net,
    do_connect = True)
design.getBlock().globalConnect()

# Configure power domains
pdngen = design.getPdnGen()
pdngen.setCoreDomain(power = VDD_net,
    switched_power = switched_power, 
    ground = VSS_net,
    secondary = secondary)

# Configure power ring dimensions
core_ring_width = [design.micronToDBU(2), design.micronToDBU(2)]
core_ring_spacing = [design.micronToDBU(2), design.micronToDBU(2)]
core_ring_core_offset = [design.micronToDBU(0) for i in range(4)]
core_ring_pad_offset = [design.micronToDBU(0) for i in range(4)]
pdn_cut_pitch = [design.micronToDBU(0) for i in range(2)]

# Get routing layers for power ring connections
ring_connect_to_pad_layers = list()
for layer in design.getTech().getDB().getTech().getLayers():
    if layer.getType() == ""ROUTING"":
        ring_connect_to_pad_layers.append(layer)

# Create power grid for standard cells
domains = [pdngen.findDomain(""Core"")]
halo = [design.micronToDBU(0) for i in range(4)]
for domain in domains:
    pdngen.makeCoreGrid(domain = domain,
    name = ""top"",
    starts_with = pdn.GROUND, 
    pin_layers = [],
    generate_obstructions = [],
    powercell = None,
    powercontrol = None,
    powercontrolnetwork = ""STAR"")

# Get metal layers for power grid
m1 = design.getTech().getDB().getTech().findLayer(""metal1"")
m4 = design.getTech().getDB().getTech().findLayer(""metal4"")
m7 = design.getTech().getDB().getTech().findLayer(""metal7"")
m8 = design.getTech().getDB().getTech().findLayer(""metal8"")

grid = pdngen.findGrid(""top"")
for g in grid:
    # Create power rings around core area
    pdngen.makeRing(grid = g,
        layer0 = m7,
        width0 = core_ring_width[0],
        spacing0 = core_ring_spacing[0],
        layer1 = m8,
        width1 = core_ring_width[0],
        spacing1 = core_ring_spacing[0],
        starts_with = pdn.GRID,
        offset = core_ring_core_offset,
        pad_offset = core_ring_pad_offset,
        extend = False,
        pad_pin_layers = ring_connect_to_pad_layers,
        nets = [],
        allow_out_of_die = True)
  
    # Create horizontal power straps on metal1 for standard cell connections
    pdngen.makeFollowpin(grid = g,
        layer = m1, 
        width = design.micronToDBU(0.07),
        extend = pdn.CORE)
  
    # Create vertical power straps on metal4 and metal7
    pdngen.makeStrap(grid = g,
        layer = m4,
        width = design.micronToDBU(1.2), 
        spacing = design.micronToDBU(1.2),
        pitch = design.micronToDBU(6),
        offset = design.micronToDBU(0), 
        number_of_straps = 0,
        snap = False,
        starts_with = pdn.GRID,
        extend = pdn.CORE,
        nets = [])
    pdngen.makeStrap(grid = g,
        layer = m7,
        width = design.micronToDBU(1.4),
        spacing = design.micronToDBU(1.4),
        pitch = design.micronToDBU(10.8),
        offset = design.micronToDBU(0),
        number_of_straps = 0,
        snap = False,
        starts_with = pdn.GRID,
        extend = pdn.RINGS,
        nets = [])
    pdngen.makeStrap(grid = g,
        layer = m8,
        width = design.micronToDBU(1.4),
        spacing = design.micronToDBU(1.4),
        pitch = design.micronToDBU(10.8),
        offset = design.micronToDBU(0),
        number_of_straps = 0,
        snap = False,
        starts_with = pdn.GRID,
        extend = pdn.BOUNDARY,
        nets = [])
  
    # Create via connections between power grid layers
    pdngen.makeConnect(grid = g,
        layer0 = m1,
        layer1 = m4, 
        cut_pitch_x = pdn_cut_pitch[0],
        cut_pitch_y = pdn_cut_pitch[1],
        vias = [],
        techvias = [],
        max_rows = 0,
        max_columns = 0,
        ongrid = [],
        split_cuts = dict(),
        dont_use_vias = """")
    pdngen.makeConnect(grid = g,
        layer0 = m4,
        layer1 = m7,
        cut_pitch_x = pdn_cut_pitch[0],
        cut_pitch_y = pdn_cut_pitch[1],
        vias = [],
        techvias = [],
        max_rows = 0,
        max_columns = 0,
        ongrid = [],
        split_cuts = dict(),
        dont_use_vias = """")
    pdngen.makeConnect(grid = g,
        layer0 = m7,
        layer1 = m8,
        cut_pitch_x = pdn_cut_pitch[0],
        cut_pitch_y = pdn_cut_pitch[1],
        vias = [],
        techvias = [],
        max_rows = 0,
        max_columns = 0,
        ongrid = [],
        split_cuts = dict(),
        dont_use_vias = """")

# Create power grid for macro blocks
macros = [inst for inst in design.getBlock().getInsts() if inst.getMaster().isBlock()]
m5 = design.getTech().getDB().getTech().findLayer(""metal5"")
m6 = design.getTech().getDB().getTech().findLayer(""metal6"")
for i in range(len(macros)):
    # Create power grid for each macro
    for domain in domains:
        pdngen.makeInstanceGrid(domain = domain,
            name = ""CORE_macro_grid_"" + str(i),
            starts_with = pdn.GROUND,
            inst = macros[i],
            halo = halo,
            pg_pins_to_boundary = True,
            default_grid = False, 
            generate_obstructions = [],
            is_bump = False)
    grid = pdngen.findGrid(""CORE_macro_grid_"" + str(i))
    for g in grid:
        # Create power straps on metal5 and metal6 for macro connections
        pdngen.makeStrap(grid = g,
            layer = m5,
            width = design.micronToDBU(1.2), 
            spacing = design.micronToDBU(1.2),
            pitch = design.micronToDBU(6),
            offset = design.micronToDBU(0),
            number_of_straps = 0,
            snap = True,
            starts_with = pdn.GRID,
            extend = pdn.CORE,
            nets = [])
        pdngen.makeStrap(grid = g,
            layer = m6,
            width = design.micronToDBU(1.2),
            spacing = design.micronToDBU(1.2),
            pitch = design.micronToDBU(6),
            offset = design.micronToDBU(0),
            number_of_straps = 0,
            snap = True,
            starts_with = pdn.GRID,
            extend = pdn.CORE,
            nets = [])
    
        # Create via connections between macro power grid layers
        pdngen.makeConnect(grid = g,
            layer0 = m4,
            layer1 = m5,
            cut_pitch_x = pdn_cut_pitch[0],
            cut_pitch_y = pdn_cut_pitch[1],
            vias = [],
            techvias = [],
            max_rows = 0,
            max_columns = 0,
            ongrid = [],
            split_cuts = dict(),
            dont_use_vias = """")
        pdngen.makeConnect(grid = g,
            layer0 = m5,
            layer1 = m6,
            cut_pitch_x = pdn_cut_pitch[0],
            cut_pitch_y = pdn_cut_pitch[1],
            vias = [],
            techvias = [],
            max_rows = 0,
            max_columns = 0,
            ongrid = [],
            split_cuts = dict(),
            dont_use_vias = """")
        pdngen.makeConnect(grid = g,
            layer0 = m6,
            layer1 = m7,
            cut_pitch_x = pdn_cut_pitch[0],
            cut_pitch_y = pdn_cut_pitch[1],
            vias = [],
            techvias = [],
            max_rows = 0,
            max_columns = 0,
            ongrid = [],
            split_cuts = dict(),
            dont_use_vias = """")

# Verify and build power grid
pdngen.checkSetup()
pdngen.buildGrids(False)
pdngen.writeToDb(True, )
pdngen.resetShapes()

# Configure and run clock tree synthesis
design.evalTclString(""set_propagated_clock [get_clocks {core_clock}]"")
# Set RC values for clock and signal nets
design.evalTclString(""set_wire_rc -clock -resistance 0.03574 -capacitance 0.07516"")
design.evalTclString(""set_wire_rc -signal -resistance 0.03574 -capacitance 0.07516"")
cts = design.getTritonCts()
parms = cts.getParms()
parms.setWireSegmentUnit(20)
# Configure clock buffers
cts.setBufferList(""BUF_X2"")
cts.setRootBuffer(""BUF_X2"")
cts.setSinkBuffer(""BUF_X2"")
cts.runTritonCts()

# Run final detailed placement
site = design.getBlock().getRows()[0].getSite()
max_disp_x = int(design.micronToDBU(1) / site.getWidth())
max_disp_y = int(design.micronToDBU(3) / site.getHeight())
design.getOpendp().detailedPlacement(max_disp_x, max_disp_y, """", False)

import openroad as ord
# Insert filler cells
db = ord.get_db()
filler_masters = list()
# filler cells' naming convention
filler_cells_prefix = ""FILLCELL_""
for lib in db.getLibs():
    for master in lib.getMasters():
        if master.getType() == ""CORE_SPACER"":
            filler_masters.append(master)
if len(filler_masters) == 0:
    print(""no filler cells in library!"")
else:
    design.getOpendp().fillerPlacement(filler_masters = filler_masters, 
                                     prefix = filler_cells_prefix,
                                     verbose = False)

# Configure and run global routing
# Set routing layer ranges for signal and clock nets
signal_low_layer = design.getTech().getDB().getTech().findLayer(""metal1"").getRoutingLevel()
signal_high_layer = design.getTech().getDB().getTech().findLayer(""metal7"").getRoutingLevel()
clk_low_layer = design.getTech().getDB().getTech().findLayer(""metal1"").getRoutingLevel()
clk_high_layer = design.getTech().getDB().getTech().findLayer(""metal7"").getRoutingLevel()

grt = design.getGlobalRouter()
grt.setMinRoutingLayer(signal_low_layer)
grt.setMaxRoutingLayer(signal_high_layer)
grt.setMinLayerForClock(clk_low_layer)
grt.setMaxLayerForClock(clk_high_layer)
grt.setAdjustment(0.5)
grt.setVerbose(True)
grt.globalRoute(True)

import drt

# Configure and run detailed routing
drter = design.getTritonRoute()
params = drt.ParamStruct()
params.outputMazeFile = """"
params.outputDrcFile = """"
params.outputCmapFile = """"
params.outputGuideCoverageFile = """"
params.dbProcessNode = """"
params.enableViaGen = True
params.drouteEndIter = 1
params.viaInPinBottomLayer = """"
params.viaInPinTopLayer = """"
params.orSeed = -1
params.orK = 0
params.bottomRoutingLayer = ""metal1""
params.topRoutingLayer = ""metal7""
params.verbose = 1
params.cleanPatches = True
params.doPa = True
params.singleStepDR = False
params.minAccessPoints = 1
params.saveGuideUpdates = False
drter.setParams(params)
drter.main()

# Write final DEF file
design.writeDef(""final.def"")

# Write final Verilog file
design.evalTclString(""write_verilog final.v"")

import psm

# Run static IR drop analysis
psm_obj = design.getPDNSim()
timing = Timing(design)
source_types = [psm.GeneratedSourceType_FULL,
    psm.GeneratedSourceType_STRAPS,
    psm.GeneratedSourceType_BUMPS]
# Analyze VDD power grid IR drop
psm_obj.analyzePowerGrid(net = design.getBlock().findNet(""VDD""),
    enable_em = False, corner = timing.getCorners()[0],
    use_prev_solution = False,
    em_file = """",
    error_file = """",
    voltage_source_file = """",
    voltage_file = """",
    source_type = source_types[2])

design.evalTclString(""report_power"")

# Write final odb file
design.writeDb(""final.odb"")
