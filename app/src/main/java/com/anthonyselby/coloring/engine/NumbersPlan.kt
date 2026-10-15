package com.anthonyselby.coloring.engine

import kotlin.math.sqrt
import kotlin.random.Random

/** Which colour (number) each region should receive in colour-by-numbers mode. */
class NumbersPlan(
    /** Palette for this picture; number N uses colors[N-1]. */
    val colors: IntArray,
    /** Palette index per region (regionId - 1). */
    val assignment: IntArray,
    /** Whether a region is large enough to carry a number; tiny ones are pre-filled. */
    val numbered: BooleanArray,
) {
    val numberCount get() = colors.size
}

object NumbersPlanner {
    private const val MIN_RADIUS = 3.5f
    private const val MIN_AREA = 40

    fun plan(map: RegionMap, palette: IntArray, seed: Long): NumbersPlan {
        val regions = map.regions
        val numbered = BooleanArray(regions.size) { i ->
            val r = regions[i]
            r.radius >= MIN_RADIUS && r.area >= MIN_AREA
        }
        val eligible = numbered.count { it }
        val k = sqrt(eligible.toDouble()).toInt().coerceIn(4, palette.size)
        val colors = palette.copyOf(k)
        val rnd = Random(seed)
        val assignment = IntArray(regions.size)
        val byArea = regions.indices.sortedByDescending { regions[it].area }
        var nextDistinct = 1
        for ((rank, idx) in byArea.withIndex()) {
            assignment[idx] = when {
                rank == 0 -> 0
                !numbered[idx] -> 1 + rnd.nextInt(k - 1)
                nextDistinct < k -> nextDistinct++
                else -> 1 + rnd.nextInt(k - 1)
            }
        }
        return NumbersPlan(colors, assignment, numbered)
    }
}
