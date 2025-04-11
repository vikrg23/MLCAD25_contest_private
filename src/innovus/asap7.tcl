set libdir "../../platform/ASAP7/lib"
set lefdir "../../platform/ASAP7/lef"
set qrcdir "../../platform/ASAP7/qrc"

set_db init_lib_search_path { \
    ${libdir} \
    ${lefdir} \
}

set libworst [glob ${libdir}/*.lib]

set libbest $libworst

set lefs "
    ${lefdir}/asap7_tech_1x_201209.lef \
    ${lefdir}/asap7sc7p5t_27_R_1x_201211.lef \
    ${lefdir}/sram_asap7_32x256_1rw.lef \
    ${lefdir}/sram_asap7_64x64_1rw.lef \
    ${lefdir}/sram_asap7_16x256_1rw.lef \
    ${lefdir}/sram_asap7_64x256_1rw.lef \
    "

set qrc_max "${qrcdir}/ASAP7.tch"
set qrc_min "${qrcdir}/ASAP7.tch"
#
# Ensures proper and consistent library handling between Genus and Innovus
#set_db library_setup_ispatial true
setDesignMode -process 7
set TOP_ROUTING_LAYER 8

set pdn_config "pdn_config.tcl"
