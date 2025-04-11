source asap7.tcl

# Change the design name here
set DESIGN_NAME mc_top
set design_dir "../../designs/$DESIGN_NAME"

setLibraryUnit -time 1ps -cap 1ff
setMultiCpuUsage -reset
setMultiCpuUsage -localCpu 8

set init_pwr_net   "VDD"
set init_gnd_net   "VSS"
set init_lef_file  "${lefs}"
set init_mmmc_file "mmmc_innovus.tcl"
set init_verilog   "$design_dir/genus.v"

source $init_mmmc_file
# initial design
init_design -setup {WC_VIEW} -hold {BC_VIEW}
set_analysis_view -setup WC_VIEW -hold BC_VIEW -leakage WC_VIEW -dynamic WC_VIEW
set_interactive_constraint_modes {CON}
setAnalysisMode -reset
setAnalysisMode -analysisType onChipVariation -cppr both
setDesignMode -topRoutingLayer 9

# read floorplan
defIn "$design_dir/fp.def.gz"

defOut -netlist -unplaced "$design_dir/$DESIGN_NAME\_fp.def.gz"
