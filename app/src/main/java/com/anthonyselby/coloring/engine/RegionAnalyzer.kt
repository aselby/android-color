package com.anthonyselby.coloring.engine

import android.graphics.Bitmap
import android.graphics.Rect

/** One contiguous paintable area of a page, bounded by line pixels. */
class Region(val id: Int) {
    var area = 0
    var left = Int.MAX_VALUE
    var top = Int.MAX_VALUE
    var right = -1
    var bottom = -1

    /** Pixel deepest inside the region (best spot for a number) and its inscribed radius. */
    var cx = 0
    var cy = 0
    var radius = 0f
    internal var maxDist = -1

    fun rect(): Rect = Rect(left, top, right + 1, bottom + 1)
}

/**
 * Per-pixel region labels for a page.
 *  - label > 0 : pixel belongs to region `label`
 *  - label < 0 : line pixel that borders region `-label` (so fills can tuck under the outline)
 *  - label == 0: pixel deep inside a line
 */
class RegionMap(val width: Int, val height: Int, val labels: IntArray, val regions: List<Region>) {
    fun idAt(x: Int, y: Int): Int {
        if (x < 0 || y < 0 || x >= width || y >= height) return 0
        val l = labels[y * width + x]
        return if (l >= 0) l else -l
    }

    fun regionAt(x: Int, y: Int): Region? {
        val id = idAt(x, y)
        return if (id > 0) regions[id - 1] else null
    }

    fun region(id: Int): Region = regions[id - 1]
}

private class IntStack(cap: Int = 1 shl 14) {
    var data = IntArray(cap)
    var size = 0
    fun push(v: Int) {
        if (size == data.size) data = data.copyOf(data.size * 2)
        data[size++] = v
    }
    fun pop(): Int = data[--size]
    fun isNotEmpty() = size > 0
}

object RegionAnalyzer {
    private const val LINE = Int.MIN_VALUE

    /** Splits the page into regions. A pixel is a line when the outline alpha is at or above [threshold]. */
    fun analyze(lineBitmap: Bitmap, threshold: Int = 128): RegionMap {
        val w = lineBitmap.width
        val h = lineBitmap.height
        val n = w * h
        val labels = IntArray(n)
        lineBitmap.getPixels(labels, 0, w, 0, 0, w, h)
        for (i in 0 until n) labels[i] = if ((labels[i] ushr 24) >= threshold) LINE else 0

        val regions = ArrayList<Region>()
        val stack = IntStack()
        var next = 1
        for (seed in 0 until n) {
            if (labels[seed] != 0) continue
            val r = Region(next)
            stack.push(seed)
            while (stack.isNotEmpty()) {
                val idx = stack.pop()
                if (labels[idx] != 0) continue
                val y = idx / w
                val row = y * w
                var x0 = idx - row
                var x1 = x0
                while (x0 > 0 && labels[row + x0 - 1] == 0) x0--
                while (x1 < w - 1 && labels[row + x1 + 1] == 0) x1++
                for (x in x0..x1) labels[row + x] = next
                r.area += x1 - x0 + 1
                if (x0 < r.left) r.left = x0
                if (x1 > r.right) r.right = x1
                if (y < r.top) r.top = y
                if (y > r.bottom) r.bottom = y
                if (y > 0) pushRuns(labels, stack, row - w, x0, x1)
                if (y < h - 1) pushRuns(labels, stack, row + w, x0, x1)
            }
            regions.add(r)
            next++
        }

        // Line pixels adopt (negated) the id of a neighbouring region.
        for (y in 0 until h) {
            val row = y * w
            for (x in 0 until w) {
                val i = row + x
                if (labels[i] != LINE) continue
                var nb = 0
                if (x > 0 && labels[i - 1] > 0) nb = labels[i - 1]
                else if (x < w - 1 && labels[i + 1] > 0) nb = labels[i + 1]
                else if (y > 0 && labels[i - w] > 0) nb = labels[i - w]
                else if (y < h - 1 && labels[i + w] > 0) nb = labels[i + w]
                labels[i] = -nb
            }
        }
        computeCenters(labels, w, h, regions)
        return RegionMap(w, h, labels, regions)
    }

    private fun pushRuns(labels: IntArray, stack: IntStack, row: Int, x0: Int, x1: Int) {
        var x = x0
        while (x <= x1) {
            if (labels[row + x] == 0) {
                stack.push(row + x)
                while (x <= x1 && labels[row + x] == 0) x++
            } else {
                x++
            }
        }
    }

    /** Chamfer (3-4) distance transform; the farthest pixel from any line is each region's centre. */
    private fun computeCenters(labels: IntArray, w: Int, h: Int, regions: List<Region>) {
        if (w < 3 || h < 3) {
            for (r in regions) { r.cx = (r.left + r.right) / 2; r.cy = (r.top + r.bottom) / 2; r.radius = 1f }
            return
        }
        val n = w * h
        val big = 1 shl 28
        val dist = IntArray(n)
        for (i in 0 until n) dist[i] = if (labels[i] > 0) big else 0
        for (x in 0 until w) {
            if (dist[x] > 3) dist[x] = 3
            val b = (h - 1) * w + x
            if (dist[b] > 3) dist[b] = 3
        }
        for (y in 0 until h) {
            val l = y * w
            if (dist[l] > 3) dist[l] = 3
            val r = l + w - 1
            if (dist[r] > 3) dist[r] = 3
        }
        for (y in 1 until h) {
            val row = y * w
            for (x in 1 until w - 1) {
                val i = row + x
                var d = dist[i]
                if (d == 0) continue
                var c = dist[i - 1] + 3; if (c < d) d = c
                c = dist[i - w] + 3; if (c < d) d = c
                c = dist[i - w - 1] + 4; if (c < d) d = c
                c = dist[i - w + 1] + 4; if (c < d) d = c
                dist[i] = d
            }
        }
        for (y in h - 2 downTo 0) {
            val row = y * w
            for (x in w - 2 downTo 1) {
                val i = row + x
                var d = dist[i]
                if (d == 0) continue
                var c = dist[i + 1] + 3; if (c < d) d = c
                c = dist[i + w] + 3; if (c < d) d = c
                c = dist[i + w + 1] + 4; if (c < d) d = c
                c = dist[i + w - 1] + 4; if (c < d) d = c
                dist[i] = d
            }
        }
        for (i in 0 until n) {
            val l = labels[i]
            if (l > 0) {
                val r = regions[l - 1]
                val d = dist[i]
                if (d > r.maxDist) {
                    r.maxDist = d
                    r.cx = i % w
                    r.cy = i / w
                }
            }
        }
        for (r in regions) {
            if (r.maxDist < 0) { r.cx = (r.left + r.right) / 2; r.cy = (r.top + r.bottom) / 2; r.maxDist = 3 }
            r.radius = r.maxDist / 3f
        }
    }
}
