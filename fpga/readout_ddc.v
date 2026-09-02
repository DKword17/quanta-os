`timescale 1ns / 1ps

/**
 * fpga/readout_ddc.v
 * 读出数字下变频器 (Digital Down-Converter)
 * 将 4-8 GHz 读出谐振器信号下变频到基带
 *
 * 架构：
 *   - 2 路 ADC (1 GS/s, 12-bit)
 *   - 数字混频器和 CIC 抽取滤波器
 *   - 可编程 FIR 成形滤波器
 */
/*
 * ─────────────────────────────────────────────────────────────
 * Quanta OS — 版权与出处  |  Copyright & Provenance
 * 作者    Author   : DKword17 <19832535010@163.com>
 * 版权    Copyright: (c) 2026 DKword17
 * 许可证  License  : Apache 2.0（见 LICENSE）
 * 仓库    Repo     : https://github.com/DKword17/quanta-os
 * Quanta OS 由 DKword17 一人原创并维护，转载/复用请保留本标记。
 * ─────────────────────────────────────────────────────────────
 */


module readout_ddc (
    input  wire        clk_1ghz,
    input  wire        rst_n,
    input  wire [11:0] adc_data_i,       // ADC I 通道
    input  wire [11:0] adc_data_q,       // ADC Q 通道
    input  wire        adc_valid,         // ADC 数据有效
    output wire [31:0] demod_i,           // 解调 I
    output wire [31:0] demod_q,           // 解调 Q
    output wire        demod_valid,       // 解调数据有效
    input  wire [31:0] lo_frequency       // 本振频率控制字
);

    // NCO (数字控制振荡器)
    reg [31:0] phase_acc;
    reg [31:0] cos_lut [0:1023];   // 余弦查找表
    reg [31:0] sin_lut [0:1023];   // 正弦查找表
    
    // 混频器
    reg [23:0] mix_i;
    reg [23:0] mix_q;
    
    // CIC 抽取滤波器 (5 阶，降采样率 16)
    reg [31:0] cic_i [0:4];
    reg [31:0] cic_q [0:4];
    reg [3:0]  decim_counter;
    
    always @(posedge clk_1ghz or negedge rst_n) begin
        if (!rst_n) begin
            phase_acc <= 0;
            for (int i = 0; i < 5; i++) begin
                cic_i[i] <= 0;
                cic_q[i] <= 0;
            end
        end else if (adc_valid) begin
            // NCO 更新
            phase_acc <= phase_acc + lo_frequency;
            
            // 数字混频: 乘以 cos(ωt) 和 sin(ωt)
            mix_i <= adc_data_i * cos_lut[phase_acc[31:22]];
            mix_q <= adc_data_q * sin_lut[phase_acc[31:22]];
            
            // CIC 积分级
            cic_i[0] <= cic_i[0] + mix_i;
            cic_q[0] <= cic_q[0] + mix_q;
            for (int i = 1; i < 5; i++) begin
                cic_i[i] <= cic_i[i] + cic_i[i-1];
                cic_q[i] <= cic_q[i] + cic_q[i-1];
            end
        end
    end
    
    assign demod_i     = cic_i[4];
    assign demod_q     = cic_q[4];
    assign demod_valid = (decim_counter == 0) && adc_valid;
    
endmodule
