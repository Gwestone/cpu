package mask_types;

    typedef enum logic [2:0] {
        MASK_8_BIT,
        MASK_16_BIT,
        MASK_32_BIT,
        MASK_64_BIT,
        MASK_8_BIT_EXTENDED,
        MASK_16_BIT_EXTENDED,
        MASK_32_BIT_EXTENDED,
        MASK_64_BIT_EXTENDED
    } mask_type_t;

endpackage
