from z3 import *

class RNG(object):
    def __init__(self):
        self.seed = BitVec('seed', 32)
        contexts = [self.seed]
        for i in range(1, 5):
            contexts.append(
                0x6C078965 * (contexts[-1] ^ LShR(contexts[-1], 30)) + i
            )
        self.contexts = contexts[1:]

    def getU32(self):
        n = self.contexts[0] ^ (self.contexts[0] << 11)
        self.contexts = self.contexts[1:]
        self.contexts.append(n ^ LShR(n, 8) ^ self.contexts[2] ^ LShR(self.contexts[2], 19))
        return self.contexts[3]


class TurnipPrices(object):
    def __init__(self):
        self.rng = RNG()
        self.basePrice = BitVec('basePrice', 32)
        self.whatPattern = BitVec('whatPattern', 32)
        self.nextPattern = BitVec('nextPattern', 32)
        self.sellPrices = [
            BitVec('sellPrice{}'.format(i), 32)
            for i in range(4)
        ]
        self.conditions = []

    def randbool(self):
        u32 = self.rng.getU32()
        bitvec = Extract(30, 30, u32)
        return If(bitvec == BitVecVal(1, 1), BoolVal(True), BoolVal(False))

    def randint(self, minimum, maximum):
        diff = maximum - minimum + 1
        rngval = Concat(BitVecVal(0, 32), self.rng.getU32())
        return Extract(31, 0, LShR(rngval * diff, 32) + minimum)

    def randfloat(self, a, b):
        val = 0x3F800000 | LShR(self.rng.getU32(), 9)
        floatingPoint = fpBVToFP(val, Float32())
        a = FPVal(a, Float32())
        b = FPVal(b, Float32())
        one = FPVal(1, Float32())
        return a + ((floatingPoint - one) * (b - a))

    # def intceil(self, val):
    #     summed = val + 0.99999
    #     return fpToSBV(RoundTowardZero(), summed, BitVecSort(32))

    def float_times_bitvec_ceil(self, float_val, bitvec):
        return fpToSBV(RoundTowardPositive(), float_val * fpSignedToFP(RNE(), bitvec, Float32()), BitVecSort(32))

    def _get_next_pattern(self):
        chance = self.randint(0, 99)

        maps = {
            0: (20, 50, 65),
            1: (50, 55, 75),
            2: (25, 70, 75),
            3: (45, 70, 85),
        }

        nextPattern = BitVecVal(2, 32)

        for val, cutoffs in sorted(maps.iteritems(), reverse=True):
            baseClause = BitVecVal(3, 32)
            for i, cutoff in zip([2, 1, 0], cutoffs[::-1]):
                baseClause = If(chance < cutoff, BitVecVal(i, 32), baseClause)
            nextPattern = If(self.whatPattern == val, baseClause, nextPattern)

        self.conditions.append(self.nextPattern == nextPattern)
        return nextPattern


    def _sell_prices_pattern_zero(self):
        return [self.basePrice] * 6

    def _sell_prices_pattern_one(self):
        return [self.basePrice] * 6

    def _sell_prices_pattern_two(self):
        vals = [self.basePrice] * 2
        rate = FPVal(0.9, Float32())
        rate -= self.randfloat(0, 0.05)
        for i in range(2):
            vals.append(self.float_times_bitvec_ceil(rate, self.basePrice))
            rate -= 0.03
            rate -= self.randfloat(0, 0.02)
        return vals

    def _sell_prices_pattern_three(self):
        return [self.basePrice] * 6

    def calculate(self):
        basePrice = self.randint(90, 110)
        self.conditions.append(self.basePrice == basePrice)

        nextPattern = self._get_next_pattern()


        # sellPriceMatrix = [
        #     self._sell_prices_pattern_zero(),
        #     self._sell_prices_pattern_one(),
        #     self._sell_prices_pattern_two(),
        #     self._sell_prices_pattern_three()
        # ]

        self.conditions.extend([
            sellPrice == val
            for sellPrice, val in zip(self.sellPrices, self._sell_prices_pattern_two())
        ])

        # for i, (zero, one, two, three) in enumerate(zip(*sellPriceMatrix)):
        #     cond = If(
        #         nextPattern == 0,
        #         zero,
        #         If(
        #             nextPattern == 1,
        #             one,
        #             If(
        #                 nextPattern == 2,
        #                 two,
        #                 three
        #             )
        #         )
        #     )
        #     self.conditions.append(self.sellPrices[i] == cond)


def solve():
    solver = Solver()
    turnip = TurnipPrices()
    turnip.calculate()
    # turnip.conditions.append(turnip.rng.seed == 2485914517)
    turnip.conditions.append(turnip.whatPattern == 0)
    turnip.conditions.append(turnip.nextPattern == 2)
    turnip.conditions.append(turnip.basePrice == 93)
    turnip.conditions.append(turnip.sellPrices[2] == 84)
    turnip.conditions.append(turnip.sellPrices[3] == 80)
    # turnip.conditions.append(turnip.sellPrices[4] == 77)
    # turnip.conditions.append(turnip.sellPrices[5] == 73)
    if solver.check(turnip.conditions) == sat:
        m = solver.model()
        print m[turnip.rng.seed].as_long()
        print m[turnip.basePrice].as_long()
        print m[turnip.whatPattern].as_long()
        print m[turnip.nextPattern].as_long()
        for sellPrice in turnip.sellPrices:
            print m[sellPrice].as_long()
    else:
        print "unsat"


if __name__ == "__main__":
    solve()
