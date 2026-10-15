package com.anthonyselby.coloring.engine

import android.graphics.Bitmap
import android.graphics.BlurMaskFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PorterDuff
import android.graphics.PorterDuffXfermode
import android.graphics.Rect
import android.graphics.RectF
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.sqrt

class Snapshot(val rect: Rect, val pixels: IntArray)

/**
 * A page being coloured: the immutable outline, the region map derived from it, and the
 * mutable colour layer that sits underneath the outline. All mutation goes through here so
 * that undo / redo stay consistent.
 */
class ColoringDocument(
    val lineBitmap: Bitmap,
    val regionMap: RegionMap,
    initialColor: Bitmap? = null,
) {
    val width = lineBitmap.width
    val height = lineBitmap.height
    val colorBitmap: Bitmap =
        if (initialColor != null && initialColor.width == width && initialColor.height == height)
            initialColor.copy(Bitmap.Config.ARGB_8888, true)
        else Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    private val colorCanvas = Canvas(colorBitmap)
    private val labels get() = regionMap.labels

    private val undoStack = ArrayDeque<Snapshot>()
    private val redoStack = ArrayDeque<Snapshot>()
    private var undoBytes = 0L

    /** Called on the main thread whenever the visible picture changes. */
    var onChanged: (() -> Unit)? = null

    var modified = false
        private set
    val canUndo get() = undoStack.isNotEmpty()
    val canRedo get() = redoStack.isNotEmpty()

    fun regionAt(x: Int, y: Int): Region? = regionMap.regionAt(x, y)

    private fun changed() {
        modified = true
        onChanged?.invoke()
    }

    // ------------------------------------------------------------------ undo

    private fun capture(rect: Rect): Snapshot {
        val w = rect.width()
        val h = rect.height()
        val px = IntArray(w * h)
        colorBitmap.getPixels(px, 0, w, rect.left, rect.top, w, h)
        return Snapshot(Rect(rect), px)
    }

    private fun restore(s: Snapshot) {
        colorBitmap.setPixels(s.pixels, 0, s.rect.width(), s.rect.left, s.rect.top, s.rect.width(), s.rect.height())
    }

    private fun pushUndo(s: Snapshot) {
        undoStack.addLast(s)
        undoBytes += s.pixels.size * 4L
        redoStack.clear()
        while (undoStack.size > MAX_UNDO || (undoBytes > MAX_UNDO_BYTES && undoStack.size > 1)) {
            val old = undoStack.removeFirst()
            undoBytes -= old.pixels.size * 4L
        }
    }

    fun clearHistory() {
        undoStack.clear()
        redoStack.clear()
        undoBytes = 0L
    }

    fun undo() {
        val s = undoStack.removeLastOrNull() ?: return
        undoBytes -= s.pixels.size * 4L
        redoStack.addLast(capture(s.rect))
        restore(s)
        changed()
    }

    fun redo() {
        val s = redoStack.removeLastOrNull() ?: return
        val cur = capture(s.rect)
        undoStack.addLast(cur)
        undoBytes += cur.pixels.size * 4L
        restore(s)
        changed()
    }

    // ------------------------------------------------------------------ fills

    /** Paint bucket: every pixel of [region] (plus the outline pixels hugging it) becomes [color]. */
    fun fillRegion(region: Region, color: Int) {
        val rect = region.rect()
        val before = capture(rect)
        val w = rect.width()
        val h = rect.height()
        val buf = before.pixels.copyOf()
        val id = region.id
        val lab = labels
        for (y in 0 until h) {
            val row = (rect.top + y) * width + rect.left
            val brow = y * w
            for (x in 0 until w) {
                val l = lab[row + x]
                if (l == id || l == -id) buf[brow + x] = color
            }
        }
        colorBitmap.setPixels(buf, 0, w, rect.left, rect.top, w, h)
        pushUndo(before)
        changed()
    }

    /** Radial gradient fill: [color] at the touch point fading to a light tint at the far edge. */
    fun gradientFillRegion(region: Region, color: Int, fx: Float, fy: Float) {
        val rect = region.rect()
        val before = capture(rect)
        val w = rect.width()
        val h = rect.height()
        val buf = before.pixels.copyOf()
        val id = region.id
        val lab = labels
        val corners = floatArrayOf(
            hypot(rect.left - fx, rect.top - fy), hypot(rect.right - fx, rect.top - fy),
            hypot(rect.left - fx, rect.bottom - fy), hypot(rect.right - fx, rect.bottom - fy),
        )
        val maxD = max(1f, corners.max())
        val a = Color.alpha(color)
        val r0 = Color.red(color); val g0 = Color.green(color); val b0 = Color.blue(color)
        val r1 = r0 + (255 - r0) * 0.7f; val g1 = g0 + (255 - g0) * 0.7f; val b1 = b0 + (255 - b0) * 0.7f
        for (y in 0 until h) {
            val row = (rect.top + y) * width + rect.left
            val brow = y * w
            val dy = (rect.top + y) - fy
            for (x in 0 until w) {
                val l = lab[row + x]
                if (l == id || l == -id) {
                    val dx = (rect.left + x) - fx
                    var t = sqrt(dx * dx + dy * dy) / maxD
                    if (t > 1f) t = 1f
                    val rr = (r0 + (r1 - r0) * t).toInt()
                    val gg = (g0 + (g1 - g0) * t).toInt()
                    val bb = (b0 + (b1 - b0) * t).toInt()
                    buf[brow + x] = Color.argb(a, rr, gg, bb)
                }
            }
        }
        colorBitmap.setPixels(buf, 0, w, rect.left, rect.top, w, h)
        pushUndo(before)
        changed()
    }

    /**
     * Fill many regions in one pass without touching the undo history (used to pre-fill
     * colour-by-number pictures). [colorOf] returns 0 for regions that should be left alone.
     */
    fun fillRegionsSilently(colorOf: (regionId: Int) -> Int) {
        val n = width * height
        val px = IntArray(n)
        colorBitmap.getPixels(px, 0, width, 0, 0, width, height)
        val cache = IntArray(regionMap.regions.size + 1)
        val known = BooleanArray(regionMap.regions.size + 1)
        val lab = labels
        for (i in 0 until n) {
            var l = lab[i]
            if (l == 0) continue
            if (l < 0) l = -l
            if (!known[l]) { cache[l] = colorOf(l); known[l] = true }
            val c = cache[l]
            if (c != 0) px[i] = c
        }
        colorBitmap.setPixels(px, 0, width, 0, 0, width, height)
        onChanged?.invoke()
    }

    /** Wipes all colour (undoable). */
    fun clearAll() {
        val rect = Rect(0, 0, width, height)
        val before = capture(rect)
        colorBitmap.eraseColor(Color.TRANSPARENT)
        pushUndo(before)
        changed()
    }

    /** The colour the user sees at a pixel (colour layer composited over white). */
    fun visibleColorAt(x: Int, y: Int): Int {
        if (x < 0 || y < 0 || x >= width || y >= height) return Color.WHITE
        val p = colorBitmap.getPixel(x, y)
        val a = Color.alpha(p)
        if (a == 0) return Color.WHITE
        val r = (Color.red(p) * a + 255 * (255 - a)) / 255
        val g = (Color.green(p) * a + 255 * (255 - a)) / 255
        val b = (Color.blue(p) * a + 255 * (255 - a)) / 255
        return Color.rgb(r, g, b)
    }

    // ------------------------------------------------------------------ strokes

    private var strokeLayer: Bitmap? = null
    private var strokeCanvas: Canvas? = null
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.DITHER_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val segPath = Path()
    private val segBounds = RectF()
    private val strokeDirty = Rect()
    private var strokeRegion = 0
    private var strokeSize = 10f
    private var strokeOpacity = 1f
    private var strokeEraser = false
    private var lastX = 0f
    private var lastY = 0f
    private var midX = 0f
    private var midY = 0f

    var strokeActive = false
        private set

    /**
     * Starts a brush / pencil / eraser stroke. When [regionId] is non-zero the stroke is
     * clipped to that region so paint never crosses the outline.
     */
    fun beginStroke(x: Float, y: Float, color: Int, size: Float, opacity: Float, eraser: Boolean, soft: Boolean, regionId: Int) {
        if (strokeLayer == null) {
            strokeLayer = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            strokeCanvas = Canvas(strokeLayer!!)
        }
        clearLayer()
        strokeActive = true
        strokeRegion = regionId
        strokeSize = size
        strokeOpacity = opacity
        strokeEraser = eraser
        strokePaint.color = if (eraser) Color.WHITE else (color or 0xFF000000.toInt())
        strokePaint.strokeWidth = size
        strokePaint.maskFilter = if (soft && size > 6f) BlurMaskFilter(size * 0.18f, BlurMaskFilter.Blur.NORMAL) else null
        lastX = x; lastY = y; midX = x; midY = y
        segPath.reset()
        segPath.moveTo(x, y)
        segPath.lineTo(x + 0.01f, y)
        drawSegment()
    }

    fun moveStroke(x: Float, y: Float) {
        if (!strokeActive) return
        val nmx = (lastX + x) / 2f
        val nmy = (lastY + y) / 2f
        segPath.reset()
        segPath.moveTo(midX, midY)
        segPath.quadTo(lastX, lastY, nmx, nmy)
        lastX = x; lastY = y; midX = nmx; midY = nmy
        drawSegment()
    }

    private fun drawSegment() {
        val canvas = strokeCanvas ?: return
        canvas.drawPath(segPath, strokePaint)
        segPath.computeBounds(segBounds, true)
        val pad = strokeSize + 4f
        val r = Rect(
            floor(segBounds.left - pad).toInt(), floor(segBounds.top - pad).toInt(),
            ceil(segBounds.right + pad).toInt(), ceil(segBounds.bottom + pad).toInt(),
        )
        if (!r.intersect(0, 0, width, height)) return
        if (strokeRegion != 0) maskRect(r)
        strokeDirty.union(r)
        onChanged?.invoke()
    }

    private fun maskRect(r: Rect) {
        val layer = strokeLayer ?: return
        val w = r.width()
        val h = r.height()
        if (w <= 0 || h <= 0) return
        val buf = IntArray(w * h)
        layer.getPixels(buf, 0, w, r.left, r.top, w, h)
        val id = strokeRegion
        val lab = labels
        for (y in 0 until h) {
            val row = (r.top + y) * width + r.left
            val b = y * w
            for (x in 0 until w) {
                val l = lab[row + x]
                if (l != id && l != -id) buf[b + x] = 0
            }
        }
        layer.setPixels(buf, 0, w, r.left, r.top, w, h)
    }

    fun endStroke() {
        if (!strokeActive) return
        strokeActive = false
        val layer = strokeLayer ?: return
        if (!strokeDirty.isEmpty) {
            val before = capture(strokeDirty)
            val p = Paint(Paint.FILTER_BITMAP_FLAG)
            p.alpha = (strokeOpacity * 255).toInt().coerceIn(0, 255)
            if (strokeEraser) p.xfermode = PorterDuffXfermode(PorterDuff.Mode.DST_OUT)
            colorCanvas.save()
            colorCanvas.clipRect(strokeDirty)
            colorCanvas.drawBitmap(layer, 0f, 0f, p)
            colorCanvas.restore()
            pushUndo(before)
            clearLayer()
            changed()
        }
    }

    fun cancelStroke() {
        strokeActive = false
        clearLayer()
        onChanged?.invoke()
    }

    private fun clearLayer() {
        val c = strokeCanvas ?: return
        if (strokeDirty.isEmpty) return
        c.save()
        c.clipRect(strokeDirty)
        c.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)
        c.restore()
        strokeDirty.setEmpty()
    }

    /** Draws the in-progress stroke so the user sees it before it is committed. */
    fun drawStrokePreview(canvas: Canvas, paint: Paint) {
        val layer = strokeLayer ?: return
        if (!strokeActive || strokeDirty.isEmpty) return
        paint.alpha = (strokeOpacity * 255).toInt().coerceIn(0, 255)
        canvas.drawBitmap(layer, strokeDirty, strokeDirty, paint)
        paint.alpha = 255
    }

    // ------------------------------------------------------------------ output

    fun renderComposite(maxSide: Int = 0): Bitmap {
        val scale = if (maxSide > 0 && max(width, height) > maxSide) maxSide.toFloat() / max(width, height) else 1f
        val out = Bitmap.createBitmap(
            max(1, (width * scale).toInt()), max(1, (height * scale).toInt()), Bitmap.Config.ARGB_8888,
        )
        val c = Canvas(out)
        c.drawColor(Color.WHITE)
        c.scale(scale, scale)
        val p = Paint(Paint.FILTER_BITMAP_FLAG)
        c.drawBitmap(colorBitmap, 0f, 0f, p)
        c.drawBitmap(lineBitmap, 0f, 0f, p)
        return out
    }

    fun markSaved() {
        modified = false
    }

    companion object {
        private const val MAX_UNDO = 40
        private const val MAX_UNDO_BYTES = 96L * 1024 * 1024
    }
}
