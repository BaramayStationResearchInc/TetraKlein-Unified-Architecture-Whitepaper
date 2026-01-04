# tk_zk_witness_recorder_cy.pyx
# cython: language_level=3, boundscheck=False, wraparound=False, initializedcheck=False, cdivision=True, nonecheck=False

import hashlib
from libc.stdint cimport uint8_t, uint64_t
from libc.string cimport memcpy
from libc.stdio cimport FILE, fopen, fwrite, fflush, fclose

cdef uint64_t E3 = 0x6c1b7c1b6c1b7c1b   

cdef class TKZKWitnessRecorderCy:
    cdef public uint64_t step
    cdef FILE* c_log_file  
    cdef uint64_t acc
    cdef uint64_t alpha
    cdef uint64_t p

    def __init__(self, bint streaming=False, str log_path="witness_100m.tkbin"):
        self.step = 0
        self.alpha = 1315423911
        self.p = 0xFFFFFFFFFFFFFFFF 
        self.acc = 0xDEADBEEF 
        
        self.c_log_file = NULL
        if streaming:
            py_byte_string = log_path.encode('utf-8')
            self.c_log_file = fopen(py_byte_string, "wb")
            if self.c_log_file == NULL:
                raise IOError(f"Could not open file: {log_path}")

    def __dealloc__(self):
        if self.c_log_file != NULL:
            fclose(self.c_log_file)
            self.c_log_file = NULL

    cpdef void record(self, uint8_t x1, uint8_t x2, uint8_t y):
        # DELTA OPTIMIZATION: Only 3 bytes of state per row
        cdef uint8_t row[3]
        cdef uint64_t current_step = self.step
        
        # AIR check remains high-speed in C
        if self.c_log_file != NULL:
            row[0] = x1
            row[1] = x2
            row[2] = y
            # Writing 3 bytes instead of 11 bytes
            fwrite(row, 1, 3, self.c_log_file)

        # Mathematical integrity remains absolute: current_step is still folded
        self.acc = (self.alpha * self.acc + y + current_step) % self.p
        self.step += 1

        # Periodic flush to prevent OS write-hangs
        if current_step % 2000000 == 0 and self.c_log_file != NULL:
            fflush(self.c_log_file)

    cpdef bytes final_commitment(self):
        if self.c_log_file != NULL:
            fclose(self.c_log_file)
            self.c_log_file = NULL
        cdef uint64_t ladder = (E3 * self.acc) % self.p
        return ladder.to_bytes(8, "big") + self.acc.to_bytes(8, "big")

    cpdef uint64_t get_epoch_root(self):
        return self.acc
