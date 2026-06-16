package load_types;
    typedef enum logic[2:0] {
        LB  = 3'b000,
        LH  = 3'b001,
        LW  = 3'b010,
        LD  = 3'b011,
        LBU = 3'b100,
        LHU = 3'b101,
        LWU = 3'b110,
        LDU = 3'b111
    } load_func_t;
endpackage
