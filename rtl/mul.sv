import mul_types::*;

module mul(
    input wire [63:0] a_in,
    input wire [63:0] b_in,
    input mul_op_t mul_op,
    input mask_type_t mask_in,
    output wire [63:0] result_out
);
    logic [63:0] result;

    logic [63:0] mask;
    assign mask = (mask_in == MASK_8_BIT  || mask_in == MASK_8_BIT_EXTENDED) ? { {56{1'b0}}, {8{1'b1}}  } :
                (mask_in == MASK_16_BIT || mask_in == MASK_16_BIT_EXTENDED) ? { {48{1'b0}}, {16{1'b1}} } :
                (mask_in == MASK_32_BIT || mask_in == MASK_32_BIT_EXTENDED) ? { {32{1'b0}}, {32{1'b1}} } :
                (mask_in == MASK_64_BIT || mask_in == MASK_64_BIT_EXTENDED) ? {64{1'b1}} :
                                                        {64{1'b1}};

    logic is_word;
    assign is_word = (mask_in == MASK_32_BIT || mask_in == MASK_32_BIT_EXTENDED);

    logic is_extended;
    assign is_extended =    mask_in == MASK_8_BIT_EXTENDED ||
                            mask_in == MASK_16_BIT_EXTENDED ||
                            mask_in == MASK_32_BIT_EXTENDED ||
                            mask_in == MASK_64_BIT_EXTENDED;

    logic [63:0] a;
    logic [63:0] b;
    assign a = is_word ?
        (is_extended ?  {{32{a_in[31]}}, a_in[31:0]} :
                        {{32{1'b0}}, a_in[31:0]})
    : a_in;
    assign b = is_word ?
        (is_extended ?  {{32{b_in[31]}}, b_in[31:0]} :
                        {{32{1'b0}}, b_in[31:0]})
    : b_in;

    logic signed [127:0] prod_ss, prod_su;
    logic        [127:0] prod_uu;
    assign prod_ss = $signed(a)  * $signed(b);
    assign prod_uu = a * b;                        // both unsigned
    assign prod_su = $signed({{64{a[63]}}, a}) * $signed({1'b0, b});

    logic signed [127:0] div_s;
    logic        [127:0] div_u;
    assign div_s = $signed({{64{a[63]}}, a}) / $signed({{64{b[63]}}, b});
    assign div_u = $unsigned({{64{1'b0}}, a}) / $unsigned({{64{1'b0}}, b});

    logic signed [127:0] rem_s;
    logic        [127:0] rem_u;
    assign rem_s = $signed({{64{a[63]}}, a}) % $signed({{64{b[63]}}, b});
    assign rem_u = $unsigned({{64{1'b0}}, a}) % $unsigned({{64{1'b0}}, b});


    always_comb begin
        case (mul_op)
            MUL_MUL: result = prod_ss[63:0];
            MUL_MUL_H: result = prod_ss[127:64];
            MUL_MUL_HU: result = prod_uu[127:64];
            MUL_MUL_HSU: result = prod_su[127:64];
            MUL_DIV: result = div_s[63:0];
            MUL_DIV_U: result = div_u[63:0];
            MUL_REM: result = rem_s[63:0];
            MUL_REM_U: result = rem_u[63:0];
            default: begin
                result = 0;
                $error("Illegal mul operation");
            end
        endcase

        //edgecases of divide by zero and rem by zero
        if((mul_op == MUL_DIV || mul_op == MUL_DIV_U) && (b == 0))
            result = {64{1'b1}};
        if((mul_op == MUL_REM || mul_op == MUL_REM_U) && (b == 0))
            result = a;

        result_out = is_word ?
            (is_extended ?  {{32{result[31]}}, result[31:0]} :
                            {{32{1'b0}}, result[31:0]})
            : result;

    end

endmodule;
