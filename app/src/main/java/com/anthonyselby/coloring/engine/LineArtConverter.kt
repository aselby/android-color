package com.anthonyselby.coloring.engine

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.math.sqrt

/** Turns photos and scanned drawings into outline bitmaps (black with alpha) the engine can use. */
object LineArtConverter {

    /** Decodes a content Uri at a sensible size and applies EXIF rotation. */
    fun decodeScaled(context: Context, uri: Uri, maxSide: Int = 2000): Bitmap? {
        val resolver = context.contentResolver
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        val probe = resolver.openInputStream(uri) ?: return null
        probe.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
        val opts = BitmapFactory.Options().apply {
            inSampleSize = sample
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        var bmp = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) } ?: return null
        val rotation = try {
            resolver.openInputStream(uri)?.use { s ->
                when (ExifInterface(s).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                    ExifInterface.ORIENTATION_ROTATE_90 -> 90f
                    ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                    ExifInterface.ORIENTATION_ROTATE_270 -> 270f
                    else -> 0f
                }
            } ?: 0f
        } catch (_: Exception) { 0f }
        if (rotation != 0f) {
            val m = Matrix().apply { postRotate(rotation) }
            bmp = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
        }
        return bmp
    }

    private fun scaleTo(src: Bitmap, maxSide: Int): Bitmap {
        val longest = max(src.width, src.height)
        if (longest <= maxSide) return src
        val s = maxSide.toFloat() / longest
        return Bitmap.createScaledBitmap(src, max(1, (src.width * s).roundToInt()), max(1, (src.height * s).roundToInt()), true)
    }

    private fun luminance(px: IntArray, out: IntArray) {
        for (i in px.indices) {
            val p = px[i]
            out[i] = (((p shr 16) and 0xFF) * 299 + ((p shr 8) and 0xFF) * 587 + (p and 0xFF) * 114) / 1000
        }
    }

    /** For scans / existing line drawings: dark pixels become lines, light pixels become paper. */
    fun fromDrawing(src: Bitmap, maxSide: Int = 1800): Bitmap {
        val b = scaleTo(src, maxSide)
        val w = b.width
        val h = b.height
        val px = IntArray(w * h)
        b.getPixels(px, 0, w, 0, 0, w, h)
        val lum = IntArray(w * h)
        luminance(px, lum)
        val hist = IntArray(256)
        for (v in lum) hist[v]++
        val thr = otsu(hist, lum.size).coerceIn(60, 200)
        val soft = 20
        for (i in lum.indices) {
            val v = lum[i]
            val a = when {
                v <= thr - soft -> 255
                v >= thr + soft -> 0
                else -> (thr + soft - v) * 255 / (2 * soft)
            }
            px[i] = a shl 24
        }
        val out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        out.setPixels(px, 0, w, 0, 0, w, h)
        return out
    }

    private fun otsu(hist: IntArray, total: Int): Int {
        var sum = 0L
        for (i in 0 until 256) sum += i.toLong() * hist[i]
        var sumB = 0L
        var wB = 0L
        var best = 0.0
        var thr = 128
        for (t in 0 until 256) {
            wB += hist[t]
            if (wB == 0L) continue
            val wF = total - wB
            if (wF == 0L) break
            sumB += t.toLong() * hist[t]
            val mB = sumB.toDouble() / wB
            val mF = (sum - sumB).toDouble() / wF
            val between = wB.toDouble() * wF * (mB - mF) * (mB - mF)
            if (between > best) { best = between; thr = t }
        }
        return thr
    }

    /** For photos: smooth, find edges, keep the strongest few percent, thicken and de-speckle. */
    fun fromPhoto(src: Bitmap, maxSide: Int = 1500, detail: Float = 0.5f): Bitmap {
        val b = scaleTo(src, maxSide)
        val w = b.width
        val h = b.height
        val n = w * h
        val px = IntArray(n)
        b.getPixels(px, 0, w, 0, 0, w, h)
        var gray = IntArray(n)
        luminance(px, gray)
        // Smooth: separable box blur, run twice (close to a Gaussian).
        val tmp = IntArray(n)
        repeat(2) {
            boxBlurH(gray, tmp, w, h, 2)
            boxBlurV(tmp, gray, w, h, 2)
        }
        // Sobel magnitude.
        val mag = IntArray(n)
        var maxMag = 1
        for (y in 1 until h - 1) {
            val row = y * w
            for (x in 1 until w - 1) {
                val i = row + x
                val gx = -gray[i - w - 1] - 2 * gray[i - 1] - gray[i + w - 1] + gray[i - w + 1] + 2 * gray[i + 1] + gray[i + w + 1]
                val gy = -gray[i - w - 1] - 2 * gray[i - w] - gray[i - w + 1] + gray[i + w - 1] + 2 * gray[i + w] + gray[i + w + 1]
                val m = sqrt((gx * gx + gy * gy).toDouble()).toInt()
                mag[i] = m
                if (m > maxMag) maxMag = m
            }
        }
        // Threshold at a percentile so busy and calm photos both give a usable amount of line.
        val hist = IntArray(1024)
        for (m in mag) hist[(m * 1023L / maxMag).toInt()]++
        val keep = (0.04f + 0.10f * detail.coerceIn(0f, 1f))
        var acc = 0L
        var bin = 1023
        while (bin > 0 && acc < n * keep) { acc += hist[bin]; bin-- }
        val thr = max(14, (bin.toLong() * maxMag / 1023).toInt())
        val edge = BooleanArray(n) { mag[it] >= thr }
        despeckle(edge, w, h, 12)
        // Thicken by one pixel in each direction so lines close properly.
        val out = IntArray(n)
        for (y in 0 until h) {
            val row = y * w
            for (x in 0 until w) {
                val i = row + x
                if (!edge[i]) continue
                out[i] = 0xFF shl 24
                if (x > 0 && out[i - 1] == 0) out[i - 1] = 0xB4 shl 24
                if (x < w - 1 && out[i + 1] == 0) out[i + 1] = 0xB4 shl 24
                if (y > 0 && out[i - w] == 0) out[i - w] = 0xB4 shl 24
                if (y < h - 1 && out[i + w] == 0) out[i + w] = 0xB4 shl 24
            }
        }
        // A frame keeps the picture tidy and gives the outer area a clean edge.
        for (x in 0 until w) { out[x] = 0xFF shl 24; out[(h - 1) * w + x] = 0xFF shl 24; if (h > 2) { out[w + x] = 0xFF shl 24; out[(h - 2) * w + x] = 0xFF shl 24 } }
        for (y in 0 until h) { out[y * w] = 0xFF shl 24; out[y * w + w - 1] = 0xFF shl 24; if (w > 2) { out[y * w + 1] = 0xFF shl 24; out[y * w + w - 2] = 0xFF shl 24 } }
        val result = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        result.setPixels(out, 0, w, 0, 0, w, h)
        return result
    }

    /**
     * For anime / cartoon art: keeps strokes that are darker than their surroundings (the inked
     * outlines) and adds strong colour boundaries that have no outline of their own.
     */
    fun fromCartoon(src: Bitmap, maxSide: Int = 1500, detail: Float = 0.5f): Bitmap {
        val b = scaleTo(src, maxSide)
        val w = b.width
        val h = b.height
        val n = w * h
        val px = IntArray(n)
        b.getPixels(px, 0, w, 0, 0, w, h)
        val lum = IntArray(n)
        luminance(px, lum)
        val tmp = IntArray(n)
        val local = IntArray(n)
        boxBlurH(lum, tmp, w, h, 8)
        boxBlurV(tmp, local, w, h, 8)
        val d = detail.coerceIn(0f, 1f)
        val sensitivity = (24 + (1f - d) * 36).toInt()
        val dark = BooleanArray(n) { lum[it] < local[it] - sensitivity && lum[it] < 170 }
        // Colour boundaries: strongest per-channel gradient on lightly smoothed channels.
        val mag = IntArray(n)
        var maxMag = 1
        for (shift in intArrayOf(16, 8, 0)) {
            val ch = IntArray(n) { (px[it] shr shift) and 0xFF }
            boxBlurH(ch, tmp, w, h, 1)
            boxBlurV(tmp, ch, w, h, 1)
            for (y in 1 until h - 1) {
                val row = y * w
                for (x in 1 until w - 1) {
                    val i = row + x
                    val gx = -ch[i - w - 1] - 2 * ch[i - 1] - ch[i + w - 1] + ch[i - w + 1] + 2 * ch[i + 1] + ch[i + w + 1]
                    val gy = -ch[i - w - 1] - 2 * ch[i - w] - ch[i - w + 1] + ch[i + w - 1] + 2 * ch[i + w] + ch[i + w + 1]
                    val m = sqrt((gx * gx + gy * gy).toDouble()).toInt()
                    if (m > mag[i]) mag[i] = m
                    if (m > maxMag) maxMag = m
                }
            }
        }
        val hist = IntArray(1024)
        for (m in mag) hist[(m * 1023L / maxMag).toInt()]++
        val keep = 0.012f + 0.03f * d
        var acc = 0L
        var bin = 1023
        while (bin > 0 && acc < n * keep) { acc += hist[bin]; bin-- }
        val thr = max(90, (bin.toLong() * maxMag / 1023).toInt())
        val edge = BooleanArray(n) { mag[it] >= thr && !dark[it] }
        despeckle(dark, w, h, 8)
        despeckle(edge, w, h, 14)
        val out = IntArray(n)
        for (y in 0 until h) {
            val row = y * w
            for (x in 0 until w) {
                val i = row + x
                if (dark[i]) {
                    out[i] = 0xFF shl 24
                    if (x > 0 && out[i - 1] == 0) out[i - 1] = 0xB4 shl 24
                    if (x < w - 1 && out[i + 1] == 0) out[i + 1] = 0xB4 shl 24
                    if (y > 0 && out[i - w] == 0) out[i - w] = 0xB4 shl 24
                    if (y < h - 1 && out[i + w] == 0) out[i + w] = 0xB4 shl 24
                } else if (edge[i] && out[i] == 0) {
                    out[i] = 0xFF shl 24
                }
            }
        }
        for (x in 0 until w) { out[x] = 0xFF shl 24; out[(h - 1) * w + x] = 0xFF shl 24; if (h > 2) { out[w + x] = 0xFF shl 24; out[(h - 2) * w + x] = 0xFF shl 24 } }
        for (y in 0 until h) { out[y * w] = 0xFF shl 24; out[y * w + w - 1] = 0xFF shl 24; if (w > 2) { out[y * w + 1] = 0xFF shl 24; out[y * w + w - 2] = 0xFF shl 24 } }
        val result = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        result.setPixels(out, 0, w, 0, 0, w, h)
        return result
    }

    private fun boxBlurH(src: IntArray, dst: IntArray, w: Int, h: Int, r: Int) {
        val div = 2 * r + 1
        for (y in 0 until h) {
            val row = y * w
            var sum = 0
            for (x in -r..r) sum += src[row + x.coerceIn(0, w - 1)]
            for (x in 0 until w) {
                dst[row + x] = sum / div
                sum += src[row + (x + r + 1).coerceIn(0, w - 1)] - src[row + (x - r).coerceIn(0, w - 1)]
            }
        }
    }

    private fun boxBlurV(src: IntArray, dst: IntArray, w: Int, h: Int, r: Int) {
        val div = 2 * r + 1
        for (x in 0 until w) {
            var sum = 0
            for (y in -r..r) sum += src[y.coerceIn(0, h - 1) * w + x]
            for (y in 0 until h) {
                dst[y * w + x] = sum / div
                sum += src[(y + r + 1).coerceIn(0, h - 1) * w + x] - src[(y - r).coerceIn(0, h - 1) * w + x]
            }
        }
    }

    /** Removes 8-connected edge blobs smaller than [minSize] pixels. */
    private fun despeckle(edge: BooleanArray, w: Int, h: Int, minSize: Int) {
        val n = w * h
        val seen = BooleanArray(n)
        var stack = IntArray(1024)
        val comp = ArrayList<Int>()
        for (start in 0 until n) {
            if (!edge[start] || seen[start]) continue
            var sp = 0
            stack[sp++] = start
            seen[start] = true
            comp.clear()
            while (sp > 0) {
                val i = stack[--sp]
                comp.add(i)
                val x = i % w
                val y = i / w
                for (dy in -1..1) {
                    val yy = y + dy
                    if (yy < 0 || yy >= h) continue
                    for (dx in -1..1) {
                        val xx = x + dx
                        if (xx < 0 || xx >= w) continue
                        val j = yy * w + xx
                        if (edge[j] && !seen[j]) {
                            seen[j] = true
                            if (sp == stack.size) stack = stack.copyOf(stack.size * 2)
                            stack[sp++] = j
                        }
                    }
                }
                if (comp.size > minSize * 4) {
                    // Big enough: drain without tracking membership.
                    while (sp > 0) {
                        val k = stack[--sp]
                        val kx = k % w
                        val ky = k / w
                        for (dy in -1..1) {
                            val yy = ky + dy
                            if (yy < 0 || yy >= h) continue
                            for (dx in -1..1) {
                                val xx = kx + dx
                                if (xx < 0 || xx >= w) continue
                                val j = yy * w + xx
                                if (edge[j] && !seen[j]) {
                                    seen[j] = true
                                    if (sp == stack.size) stack = stack.copyOf(stack.size * 2)
                                    stack[sp++] = j
                                }
                            }
                        }
                    }
                    comp.clear()
                    break
                }
            }
            if (comp.isNotEmpty() && comp.size < minSize) for (i in comp) edge[i] = false
        }
    }
}
