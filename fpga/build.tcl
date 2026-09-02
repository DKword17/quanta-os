#
# ─────────────────────────────────────────────────────────────
# Quanta OS — 版权与出处  |  Copyright & Provenance
# 作者    Author   : DKword17 <19832535010@163.com>
# 版权    Copyright: (c) 2026 DKword17
# 许可证  License  : Apache 2.0（见 LICENSE）
# 仓库    Repo     : https://github.com/DKword17/quanta-os
# Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
# ─────────────────────────────────────────────────────────────

#
# fpga/build.tcl
# Vivado 构建脚本
#
set project_name quanta_os_ctrl

create_project -force $project_name ./$project_name -part xc7k325tffg900-2

# 源文件
add_files -fileset sources_1 [glob *.v]
add_files -fileset sim_1    [glob *_tb.v]

# 约束
set_property -dict {PACKAGE_PIN Y23 IOSTANDARD LVDS} [get_ports clk_1ghz]

# 综合
synth_design -top pulse_gen -part xc7k325tffg900-2 -flatten_hierarchy full

# 布局布线
place_design
route_design

# 生成比特流
write_bitstream -force ./${project_name}.bit

puts "Build complete: ${project_name}.bit"
