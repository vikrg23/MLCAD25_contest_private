set_time_unit -picoseconds 1.0
set_load_unit -femtofarads 1.0
set_max_fanout 16.000 [current_design]
create_clock -name clk -period 450.0 [get_ports clk]
set_input_delay  -max -clock [get_clocks "clk"] -add_delay 45.0 [all_inputs -no_clocks]
set_output_delay -max -clock [get_clocks "clk"] -add_delay 45.0 [all_outputs]
set_input_delay  -min -clock [get_clocks "clk"] -add_delay 22.5 [all_inputs -no_clocks]
set_output_delay -min -clock [get_clocks "clk"] -add_delay 22.5 [all_outputs]

set_max_transition 4.5 [all_outputs]
set_input_transition -max 22.5 [all_inputs]
set_input_transition -min 4.5 [all_inputs]
