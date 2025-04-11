set_time_unit -picoseconds 1.0
set_load_unit -femtofarads 1.0
set_max_fanout 16.000 [current_design]
create_clock -name clk -period 200.0 [get_ports clk]
set_input_delay  -max -clock [get_clocks "clk"] -add_delay 20.0 [all_inputs -no_clocks]
set_output_delay -max -clock [get_clocks "clk"] -add_delay 20.0 [all_outputs]
set_input_delay  -min -clock [get_clocks "clk"] -add_delay 10.0 [all_inputs -no_clocks]
set_output_delay -min -clock [get_clocks "clk"] -add_delay 10.0 [all_outputs]

set_max_transition 2.0 [all_outputs]
set_input_transition -max 10.0 [all_inputs]
set_input_transition -min 2.0 [all_inputs]
