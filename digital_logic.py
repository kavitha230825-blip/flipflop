"""
EC2201 Digital Systems - Pure Digital Logic Simulation Module
4-Bit Synchronous Binary Up-Counter using Flip-Flop Concepts

State representation: Q3 Q2 Q1 Q0 (Q3 = MSB, Q0 = LSB)
State cycle: 0000 -> 0001 -> 0010 -> ... -> 1110 -> 1111 -> 0000 (mod 16)

Synchronous Counter Excitation Equations:
    T-Flip-Flop:
        T0 = 1
        T1 = Q0
        T2 = Q1 AND Q0
        T3 = Q2 AND Q1 AND Q0
        Next State: Qi+ = Qi XOR Ti

    D-Flip-Flop Equivalent:
        D0 = NOT Q0
        D1 = Q1 XOR Q0
        D2 = Q2 XOR (Q1 AND Q0)
        D3 = Q3 XOR (Q2 AND Q1 AND Q0)
        Next State: Qi+ = Di
"""

from typing import Dict, List, Tuple, Union
import numpy as np


class FourBitCounter:
    """
    Simulates a 4-bit synchronous binary up-counter constructed from flip-flops.
    Maintains internal flip-flop states [Q3, Q2, Q1, Q0].
    """

    def __init__(self, initial_state: Union[str, int, List[int]] = 0):
        """
        Initialize the counter with 4 flip-flop states.
        State order: [Q3, Q2, Q1, Q0] where Q3 is MSB and Q0 is LSB.
        """
        self.q3: int = 0
        self.q2: int = 0
        self.q1: int = 0
        self.q0: int = 0
        self.set_state(initial_state)

    def set_state(self, state: Union[str, int, List[int]]) -> None:
        """Set the counter state from an integer (0-15), binary string ('0101'), or list ([0,1,0,1])."""
        if isinstance(state, int):
            if not 0 <= state <= 15:
                raise ValueError(f"State integer must be between 0 and 15, got {state}")
            bits = [(state >> i) & 1 for i in reversed(range(4))]
        elif isinstance(state, str):
            clean = state.strip()
            if len(clean) != 4 or not all(c in ('0', '1') for c in clean):
                raise ValueError(f"Binary state string must be exactly 4 bits (e.g. '0101'), got '{state}'")
            bits = [int(c) for c in clean]
        elif isinstance(state, (list, tuple)):
            if len(state) != 4 or not all(b in (0, 1) for b in state):
                raise ValueError(f"State list must contain 4 binary elements, got {state}")
            bits = [int(b) for b in state]
        else:
            raise TypeError(f"Unsupported state type: {type(state)}")

        self.q3, self.q2, self.q1, self.q0 = bits

    @property
    def bits(self) -> List[int]:
        """Returns the current state as [Q3, Q2, Q1, Q0]."""
        return [self.q3, self.q2, self.q1, self.q0]

    @property
    def binary_string(self) -> str:
        """Returns the current state formatted as a 4-bit binary string 'Q3Q2Q1Q0'."""
        return f"{self.q3}{self.q2}{self.q1}{self.q0}"

    @property
    def decimal_value(self) -> int:
        """Calculates decimal value: Q3*8 + Q2*4 + Q1*2 + Q0*1."""
        return (self.q3 << 3) | (self.q2 << 2) | (self.q1 << 1) | self.q0

    @staticmethod
    def binary_to_decimal(bits: Union[str, List[int]]) -> int:
        """Convert a 4-bit binary string or list [Q3, Q2, Q1, Q0] to decimal (0-15)."""
        if isinstance(bits, str):
            clean = bits.strip()
            return int(clean, 2)
        elif isinstance(bits, (list, tuple)):
            return sum((bit << (len(bits) - 1 - idx)) for idx, bit in enumerate(bits))
        raise TypeError(f"Invalid input type for binary_to_decimal: {type(bits)}")

    @staticmethod
    def decimal_to_binary(val: int) -> str:
        """Convert a decimal integer (0-15) to a 4-bit binary string."""
        if not 0 <= val <= 15:
            raise ValueError(f"Value must be between 0 and 15, got {val}")
        return format(val, '04b')

    @staticmethod
    def compute_t_excitations(q3: int, q2: int, q1: int, q0: int) -> Tuple[int, int, int, int]:
        """
        Compute T-flip-flop inputs according to synchronous counter logic:
        T0 = 1
        T1 = Q0
        T2 = Q1 AND Q0
        T3 = Q2 AND Q1 AND Q0
        Returns (T3, T2, T1, T0).
        """
        t0 = 1
        t1 = q0
        t2 = q1 & q0
        t3 = q2 & q1 & q0
        return t3, t2, t1, t0

    @staticmethod
    def compute_d_excitations(q3: int, q2: int, q1: int, q0: int) -> Tuple[int, int, int, int]:
        """
        Compute equivalent D-flip-flop next-state inputs:
        D0 = NOT Q0
        D1 = Q1 XOR Q0
        D2 = Q2 XOR (Q1 AND Q0)
        D3 = Q3 XOR (Q2 AND Q1 AND Q0)
        Returns (D3, D2, D1, D0).
        """
        d0 = 1 - q0
        d1 = q1 ^ q0
        d2 = q2 ^ (q1 & q0)
        d3 = q3 ^ (q2 & q1 & q0)
        return d3, d2, d1, d0

    @classmethod
    def calculate_next_state(cls, q3: int, q2: int, q1: int, q0: int) -> Tuple[int, int, int, int]:
        """
        Calculate the next state [Q3+, Q2+, Q1+, Q0+] using T-flip-flop equations:
        Qi+ = Qi XOR Ti
        """
        t3, t2, t1, t0 = cls.compute_t_excitations(q3, q2, q1, q0)
        next_q0 = q0 ^ t0
        next_q1 = q1 ^ t1
        next_q2 = q2 ^ t2
        next_q3 = q3 ^ t3
        return next_q3, next_q2, next_q1, next_q0

    def clock_pulse(self) -> Dict[str, Union[str, int, bool, List[int], Dict[str, int]]]:
        """
        Simulate a rising-edge clock pulse triggering state transition.
        Calculates T and D excitations, updates Q3, Q2, Q1, Q0, and checks overflow.
        Returns a complete transition payload suitable for UI animation and logging.
        """
        prev_q3, prev_q2, prev_q1, prev_q0 = self.q3, self.q2, self.q1, self.q0
        prev_bin = self.binary_string
        prev_dec = self.decimal_value

        # Calculate excitations
        t3, t2, t1, t0 = self.compute_t_excitations(prev_q3, prev_q2, prev_q1, prev_q0)
        d3, d2, d1, d0 = self.compute_d_excitations(prev_q3, prev_q2, prev_q1, prev_q0)

        # Calculate next state
        next_q3, next_q2, next_q1, next_q0 = self.calculate_next_state(prev_q3, prev_q2, prev_q1, prev_q0)

        # Check for counter overflow (1111 -> 0000)
        overflow = (prev_dec == 15 and (next_q3, next_q2, next_q1, next_q0) == (0, 0, 0, 0))

        # Commit state update
        self.q3, self.q2, self.q1, self.q0 = next_q3, next_q2, next_q1, next_q0

        curr_bin = self.binary_string
        curr_dec = self.decimal_value

        return {
            "previous_state": {
                "binary": prev_bin,
                "bits": [prev_q3, prev_q2, prev_q1, prev_q0],
                "decimal": prev_dec,
                "q3": prev_q3,
                "q2": prev_q2,
                "q1": prev_q1,
                "q0": prev_q0
            },
            "excitations": {
                "T": {"t3": t3, "t2": t2, "t1": t1, "t0": t0},
                "D": {"d3": d3, "d2": d2, "d1": d1, "d0": d0}
            },
            "current_state": {
                "binary": curr_bin,
                "bits": [self.q3, self.q2, self.q1, self.q0],
                "decimal": curr_dec,
                "q3": self.q3,
                "q2": self.q2,
                "q1": self.q1,
                "q0": self.q0
            },
            "overflow": overflow
        }

    def reset(self) -> Dict[str, Union[str, int, List[int]]]:
        """
        Simulate an asynchronous counter reset (MR / Clear line active).
        Sets Q3 Q2 Q1 Q0 to 0000 and decimal value to 0.
        """
        prev_bin = self.binary_string
        prev_dec = self.decimal_value

        self.q3 = 0
        self.q2 = 0
        self.q1 = 0
        self.q0 = 0

        return {
            "previous_binary": prev_bin,
            "previous_decimal": prev_dec,
            "current_binary": "0000",
            "current_decimal": 0,
            "bits": [0, 0, 0, 0]
        }

    def get_state(self) -> Dict[str, Union[str, int, List[int], Dict[str, int]]]:
        """Returns the current state and excitation values for the upcoming clock pulse."""
        t3, t2, t1, t0 = self.compute_t_excitations(self.q3, self.q2, self.q1, self.q0)
        d3, d2, d1, d0 = self.compute_d_excitations(self.q3, self.q2, self.q1, self.q0)
        next_q3, next_q2, next_q1, next_q0 = self.calculate_next_state(self.q3, self.q2, self.q1, self.q0)

        return {
            "binary": self.binary_string,
            "decimal": self.decimal_value,
            "bits": self.bits,
            "q3": self.q3,
            "q2": self.q2,
            "q1": self.q1,
            "q0": self.q0,
            "next_binary": f"{next_q3}{next_q2}{next_q1}{next_q0}",
            "next_decimal": (next_q3 << 3) | (next_q2 << 2) | (next_q1 << 1) | next_q0,
            "excitations": {
                "t3": t3, "t2": t2, "t1": t1, "t0": t0,
                "d3": d3, "d2": d2, "d1": d1, "d0": d0
            }
        }

    @classmethod
    def get_truth_table(cls) -> List[Dict[str, Union[str, int]]]:
        """
        Generates the complete 16-row truth table for the 4-bit synchronous counter.
        Rows 0 to 15 show:
            - Current State (Binary & Decimal)
            - Next State (Binary & Decimal)
            - T-Flip-Flop inputs (T3, T2, T1, T0)
            - D-Flip-Flop inputs (D3, D2, D1, D0)
        """
        table = []
        for dec in range(16):
            q3 = (dec >> 3) & 1
            q2 = (dec >> 2) & 1
            q1 = (dec >> 1) & 1
            q0 = dec & 1
            curr_bin = f"{q3}{q2}{q1}{q0}"

            t3, t2, t1, t0 = cls.compute_t_excitations(q3, q2, q1, q0)
            d3, d2, d1, d0 = cls.compute_d_excitations(q3, q2, q1, q0)
            nxt_q3, nxt_q2, nxt_q1, nxt_q0 = cls.calculate_next_state(q3, q2, q1, q0)

            nxt_bin = f"{nxt_q3}{nxt_q2}{nxt_q1}{nxt_q0}"
            nxt_dec = (nxt_q3 << 3) | (nxt_q2 << 2) | (nxt_q1 << 1) | nxt_q0

            table.append({
                "current_decimal": dec,
                "current_binary": curr_bin,
                "q3": q3, "q2": q2, "q1": q1, "q0": q0,
                "t3": t3, "t2": t2, "t1": t1, "t0": t0,
                "d3": d3, "d2": d2, "d1": d1, "d0": d0,
                "next_binary": nxt_bin,
                "next_decimal": nxt_dec,
                "next_q3": nxt_q3, "next_q2": nxt_q2, "next_q1": nxt_q1, "next_q0": nxt_q0,
                "overflow": (dec == 15)
            })
        return table
