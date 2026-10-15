package com.anthonyselby.coloring.ui.editor

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PorterDuff
import android.graphics.Typeface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.anthonyselby.coloring.data.ColoringMode
import com.anthonyselby.coloring.data.PageInfo
import com.anthonyselby.coloring.data.PageRepository
import com.anthonyselby.coloring.data.Palettes
import com.anthonyselby.coloring.engine.ColoringDocument
import com.anthonyselby.coloring.engine.NumbersPlan
import com.anthonyselby.coloring.engine.NumbersPlanner
import com.anthonyselby.coloring.engine.Region
import com.anthonyselby.coloring.engine.RegionAnalyzer
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.nio.ByteBuffer
import kotlin.math.abs
import kotlin.random.Random

enum class Tool { FILL, BRUSH, PENCIL, ERASER, GRADIENT, EYEDROPPER }

/** All editor state and behaviour for one page; the composables only render it. */
class EditorController(
    @Suppress("unused") private val context: Context,
    private val repo: PageRepository,
    val page: PageInfo,
    val mode: ColoringMode,
    private val scope: CoroutineScope,
    private val saveScope: CoroutineScope,
) : ColoringCanvasView.Listener {

    var document by mutableStateOf<ColoringDocument?>(null)
        private set
    var loading by mutableStateOf(true)
        private set
    var loadError by mutableStateOf<String?>(null)
        private set

    var tool by mutableStateOf(Tool.FILL)
        private set
    private var lastPaintTool = Tool.FILL
    var paletteIndex by mutableIntStateOf(0)
        private set
    var showingRecent by mutableStateOf(false)
    var baseColor by mutableIntStateOf(0xFF1E90FF.toInt())
        private set
    var shade by mutableIntStateOf(0)
    var opacity by mutableFloatStateOf(1f)
    var brushSize by mutableFloatStateOf(28f)
    var stayInside by mutableStateOf(true)
    val recentColors = mutableStateListOf<Int>()

    var canUndo by mutableStateOf(false)
        private set
    var canRedo by mutableStateOf(false)
        private set

    var message by mutableStateOf<String?>(null)
    var messageTick by mutableIntStateOf(0)
        private set
    var completed by mutableStateOf(false)
        private set

    // ---- colour by numbers
    var plan by mutableStateOf<NumbersPlan?>(null)
        private set
    val remaining = mutableStateListOf<Int>()
    var selectedNumber by mutableIntStateOf(1)
        private set
    private val doneRegions = HashSet<Int>()
    private val numbersHistory = ArrayDeque<Int>()
    private val numbersRedo = ArrayDeque<Int>()
    private var numbersLayer: Bitmap? = null
    private var numbersCanvas: Canvas? = null
    private var highlight: Bitmap? = null
    private var highlightBytes: ByteArray? = null
    private val numberPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF37474F.toInt()
        textAlign = Paint.Align.CENTER
        typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
    }

    /** Asks the canvas to redraw. */
    var invalidate: (() -> Unit)? = null
    private val bitmapPaint = Paint(Paint.FILTER_BITMAP_FLAG)
    private val previewPaint = Paint(Paint.FILTER_BITMAP_FLAG)
    private val highlightPaint = Paint().apply { color = 0x5A00A2FF }

    val currentColor: Int get() = Palettes.withOpacity(Palettes.shade(baseColor, shade), opacity)
    val isStrokeTool: Boolean get() = tool == Tool.BRUSH || tool == Tool.PENCIL || tool == Tool.ERASER
    val singleFingerPans: Boolean get() = mode == ColoringMode.NUMBERS || !isStrokeTool
    val paletteName: String get() = if (showingRecent) "Recent" else Palettes.all[paletteIndex].name
    val swatches: List<Int> get() = if (showingRecent) recentColors.toList() else Palettes.all[paletteIndex].colors

    // ------------------------------------------------------------------ loading

    private class NumbersSetup(
        val plan: NumbersPlan, val done: HashSet<Int>, val remaining: IntArray,
        val layer: Bitmap, val highlight: Bitmap, val highlightBytes: ByteArray, val selected: Int, val complete: Boolean,
    )

    fun load() {
        if (document != null || !loading) return
        scope.launch {
            try {
                val key = repo.workKey(page, mode)
                var numbers: NumbersSetup? = null
                var recents: List<Int> = emptyList()
                val doc = withContext(Dispatchers.Default) {
                    val lines = repo.loadLineArt(page)
                    val map = RegionAnalyzer.analyze(lines)
                    val (work, meta) = repo.loadWork(key)
                    val d = ColoringDocument(lines, map, work)
                    meta?.optJSONArray("recent")?.let { arr -> recents = List(arr.length()) { arr.getInt(it) } }
                    if (mode == ColoringMode.NUMBERS) numbers = buildNumbers(d, meta)
                    d
                }
                recentColors.addAll(recents.take(12))
                numbers?.let { n ->
                    plan = n.plan
                    doneRegions.addAll(n.done)
                    remaining.clear()
                    remaining.addAll(n.remaining.toList())
                    numbersLayer = n.layer
                    numbersCanvas = Canvas(n.layer)
                    highlight = n.highlight
                    highlightBytes = n.highlightBytes
                    selectedNumber = n.selected
                    completed = n.complete
                }
                doc.onChanged = {
                    refreshHistory()
                    invalidate?.invoke()
                }
                document = doc
                refreshHistory()
                invalidate?.invoke()
            } catch (t: Throwable) {
                loadError = "Sorry, this picture could not be opened."
            } finally {
                loading = false
            }
        }
    }

    private fun refreshHistory() {
        val doc = document
        if (mode == ColoringMode.NUMBERS) {
            canUndo = numbersHistory.isNotEmpty()
            canRedo = numbersRedo.isNotEmpty()
        } else {
            canUndo = doc?.canUndo == true
            canRedo = doc?.canRedo == true
        }
    }

    // ------------------------------------------------------------------ drawing

    fun drawPage(c: Canvas) {
        val doc = document ?: return
        c.drawBitmap(doc.colorBitmap, 0f, 0f, bitmapPaint)
        doc.drawStrokePreview(c, previewPaint)
        if (mode == ColoringMode.NUMBERS && !completed) highlight?.let { c.drawBitmap(it, 0f, 0f, highlightPaint) }
        c.drawBitmap(doc.lineBitmap, 0f, 0f, bitmapPaint)
        numbersLayer?.let { c.drawBitmap(it, 0f, 0f, bitmapPaint) }
    }

    // ------------------------------------------------------------------ tools & colours

    fun selectTool(t: Tool) {
        if (t != Tool.EYEDROPPER && t != Tool.ERASER) lastPaintTool = t
        tool = t
    }

    fun selectColor(color: Int) {
        baseColor = color or 0xFF000000.toInt()
        if (tool == Tool.EYEDROPPER || tool == Tool.ERASER) tool = lastPaintTool
    }

    fun pickCustomColor(color: Int) {
        shade = 0
        selectColor(color)
        rememberColor(color or 0xFF000000.toInt())
    }

    fun setPalette(index: Int) {
        paletteIndex = index.coerceIn(0, Palettes.all.lastIndex)
        showingRecent = false
    }

    fun nextPalette() = setPalette(if (showingRecent) 0 else (paletteIndex + 1) % Palettes.all.size)
    fun prevPalette() = setPalette(if (showingRecent) Palettes.all.lastIndex else (paletteIndex - 1 + Palettes.all.size) % Palettes.all.size)

    private fun rememberColor(color: Int) {
        val c = color or 0xFF000000.toInt()
        recentColors.remove(c)
        recentColors.add(0, c)
        while (recentColors.size > 12) recentColors.removeAt(recentColors.lastIndex)
    }

    private fun noteColorUsed() = rememberColor(Palettes.shade(baseColor, shade))

    fun showMessage(text: String) {
        message = text
        messageTick++
    }

    // ------------------------------------------------------------------ touch input

    override fun onTap(x: Float, y: Float): Boolean {
        val doc = document ?: return false
        val px = x.toInt()
        val py = y.toInt()
        if (px < 0 || py < 0 || px >= doc.width || py >= doc.height) return false
        if (mode == ColoringMode.NUMBERS) return tapNumbers(doc, px, py)
        return when (tool) {
            Tool.FILL -> {
                val r = doc.regionAt(px, py) ?: return false
                doc.fillRegion(r, currentColor)
                noteColorUsed()
                true
            }
            Tool.GRADIENT -> {
                val r = doc.regionAt(px, py) ?: return false
                doc.gradientFillRegion(r, currentColor, x, y)
                noteColorUsed()
                true
            }
            Tool.EYEDROPPER -> {
                baseColor = doc.visibleColorAt(px, py)
                shade = 0
                tool = lastPaintTool
                showMessage("Color picked")
                true
            }
            Tool.BRUSH, Tool.PENCIL, Tool.ERASER -> {
                onStrokeStart(x, y)
                onStrokeEnd()
                true
            }
        }
    }

    override fun onStrokeStart(x: Float, y: Float) {
        val doc = document ?: return
        if (mode == ColoringMode.NUMBERS || !isStrokeTool) return
        val regionId = if (stayInside) doc.regionMap.idAt(x.toInt(), y.toInt()) else 0
        val size = if (tool == Tool.PENCIL) brushSize * 0.45f else brushSize
        doc.beginStroke(
            x, y, currentColor, size.coerceAtLeast(1.5f), opacity,
            eraser = tool == Tool.ERASER, soft = tool == Tool.BRUSH, regionId = regionId,
        )
    }

    override fun onStrokeMove(x: Float, y: Float) {
        document?.moveStroke(x, y)
    }

    override fun onStrokeEnd() {
        val doc = document ?: return
        if (!doc.strokeActive) return
        doc.endStroke()
        if (tool != Tool.ERASER) noteColorUsed()
    }

    override fun onStrokeCancel() {
        document?.cancelStroke()
    }

    // ------------------------------------------------------------------ history

    fun undo() {
        val doc = document ?: return
        if (mode == ColoringMode.NUMBERS) {
            val plan = plan ?: return
            val id = numbersHistory.removeLastOrNull() ?: return
            doc.undo()
            doneRegions.remove(id)
            numbersRedo.addLast(id)
            val r = doc.regionMap.region(id)
            val n = plan.assignment[id - 1] + 1
            remaining[n - 1] = remaining[n - 1] + 1
            numbersCanvas?.let { drawNumber(it, r, n) }
            completed = false
            selectNumber(n)
        } else {
            doc.undo()
        }
        refreshHistory()
    }

    fun redo() {
        val doc = document ?: return
        if (mode == ColoringMode.NUMBERS) {
            val plan = plan ?: return
            val id = numbersRedo.removeLastOrNull() ?: return
            doc.redo()
            val r = doc.regionMap.region(id)
            val n = plan.assignment[id - 1] + 1
            markDone(r, n, pushHistory = true)
        } else {
            doc.redo()
        }
        refreshHistory()
    }

    fun resetAll() {
        val doc = document ?: return
        if (mode == ColoringMode.NUMBERS) {
            val plan = plan ?: return
            doc.clearAll()
            doc.clearHistory()
            doneRegions.clear()
            numbersHistory.clear()
            numbersRedo.clear()
            completed = false
            doc.fillRegionsSilently { id -> if (!plan.numbered[id - 1]) plan.colors[plan.assignment[id - 1]] else 0 }
            val regions = doc.regionMap.regions
            for (i in remaining.indices) remaining[i] = 0
            numbersCanvas?.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)
            for ((idx, r) in regions.withIndex()) if (plan.numbered[idx]) {
                remaining[plan.assignment[idx]]++
                numbersCanvas?.let { drawNumber(it, r, plan.assignment[idx] + 1) }
            }
            selectNumber(1)
        } else {
            doc.clearAll()
        }
        refreshHistory()
        invalidate?.invoke()
    }

    // ------------------------------------------------------------------ colour by numbers

    private fun buildNumbers(doc: ColoringDocument, meta: JSONObject?): NumbersSetup {
        val plan = NumbersPlanner.plan(doc.regionMap, Palettes.numbersPalette(page.category), page.id.hashCode().toLong())
        val done = HashSet<Int>()
        meta?.optJSONArray("completed")?.let { arr -> for (i in 0 until arr.length()) done.add(arr.getInt(i)) }
        doc.fillRegionsSilently { id ->
            val idx = id - 1
            if (!plan.numbered[idx] || done.contains(id)) plan.colors[plan.assignment[idx]] else 0
        }
        val regions = doc.regionMap.regions
        val remaining = IntArray(plan.numberCount)
        val layer = Bitmap.createBitmap(doc.width, doc.height, Bitmap.Config.ARGB_8888)
        val c = Canvas(layer)
        for ((idx, r) in regions.withIndex()) {
            if (plan.numbered[idx] && !done.contains(r.id)) {
                remaining[plan.assignment[idx]]++
                drawNumber(c, r, plan.assignment[idx] + 1)
            }
        }
        var selected = (meta?.optInt("selected", 1) ?: 1).coerceIn(1, plan.numberCount)
        if (remaining[selected - 1] == 0) selected = (remaining.indexOfFirst { it > 0 } + 1).coerceAtLeast(1)
        val complete = remaining.all { it == 0 }
        val hl = Bitmap.createBitmap(doc.width, doc.height, Bitmap.Config.ALPHA_8)
        val bytes = ByteArray(hl.rowBytes * doc.height)
        fillHighlight(doc, plan, done, bytes, hl, selected)
        return NumbersSetup(plan, done, remaining, layer, hl, bytes, selected, complete)
    }

    private fun textSizeFor(r: Region) = (r.radius * 1.25f).coerceIn(7f, 46f)

    private fun drawNumber(c: Canvas, r: Region, n: Int) {
        val ts = textSizeFor(r)
        numberPaint.textSize = ts
        c.drawText(n.toString(), r.cx.toFloat(), r.cy + ts * 0.36f, numberPaint)
    }

    private fun eraseNumber(r: Region) {
        val c = numbersCanvas ?: return
        val plan = plan ?: return
        val doc = document ?: return
        val half = textSizeFor(r) * 0.95f
        c.save()
        c.clipRect(r.cx - half, r.cy - half, r.cx + half, r.cy + half)
        c.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)
        c.restore()
        // Neighbouring numbers that overlapped the cleared square get redrawn.
        val regions = doc.regionMap.regions
        for ((idx, o) in regions.withIndex()) {
            if (o === r || !plan.numbered[idx] || doneRegions.contains(o.id)) continue
            val ots = textSizeFor(o)
            if (abs(o.cx - r.cx) < half + ots && abs(o.cy - r.cy) < half + ots) drawNumber(c, o, plan.assignment[idx] + 1)
        }
    }

    private fun fillHighlight(doc: ColoringDocument, plan: NumbersPlan, done: Set<Int>, bytes: ByteArray, hl: Bitmap, number: Int) {
        java.util.Arrays.fill(bytes, 0)
        val regions = doc.regionMap.regions
        val wanted = BooleanArray(regions.size + 1)
        for ((idx, r) in regions.withIndex()) {
            wanted[r.id] = plan.numbered[idx] && plan.assignment[idx] == number - 1 && !done.contains(r.id)
        }
        val lab = doc.regionMap.labels
        val w = doc.width
        val stride = hl.rowBytes
        for (y in 0 until doc.height) {
            val row = y * w
            val brow = y * stride
            for (x in 0 until w) {
                var l = lab[row + x]
                if (l < 0) l = -l
                if (l != 0 && wanted[l]) bytes[brow + x] = -1
            }
        }
        hl.copyPixelsFromBuffer(ByteBuffer.wrap(bytes))
    }

    private fun rebuildHighlight() {
        val doc = document ?: return
        val plan = plan ?: return
        val hl = highlight ?: return
        val bytes = highlightBytes ?: return
        fillHighlight(doc, plan, doneRegions, bytes, hl, selectedNumber)
    }

    fun selectNumber(n: Int) {
        val plan = plan ?: return
        selectedNumber = n.coerceIn(1, plan.numberCount)
        rebuildHighlight()
        invalidate?.invoke()
    }

    private fun tapNumbers(doc: ColoringDocument, px: Int, py: Int): Boolean {
        val plan = plan ?: return false
        val r = doc.regionAt(px, py) ?: return false
        val idx = r.id - 1
        if (!plan.numbered[idx] || doneRegions.contains(r.id)) return false
        val n = plan.assignment[idx] + 1
        if (n != selectedNumber) {
            showMessage("This area is number $n")
            return false
        }
        doc.fillRegion(r, plan.colors[n - 1])
        numbersRedo.clear()
        markDone(r, n, pushHistory = true)
        return true
    }

    private fun markDone(r: Region, n: Int, pushHistory: Boolean) {
        val plan = plan ?: return
        doneRegions.add(r.id)
        if (pushHistory) numbersHistory.addLast(r.id)
        remaining[n - 1] = (remaining[n - 1] - 1).coerceAtLeast(0)
        eraseNumber(r)
        if (remaining[n - 1] == 0) {
            val next = (0 until plan.numberCount).firstOrNull { remaining[it] > 0 }
            if (next == null) {
                completed = true
                showMessage("Picture complete! Tap ✓ to save or share it.")
                invalidate?.invoke()
            } else {
                showMessage("Number $n done! Next: ${next + 1}")
                selectNumber(next + 1)
            }
        } else {
            rebuildHighlight()
            invalidate?.invoke()
        }
        refreshHistory()
    }

    /** Fills one remaining area of the current number for the user. Returns its region. */
    fun hint(): Region? {
        val doc = document ?: return null
        val plan = plan ?: return null
        var n = selectedNumber
        if (remaining[n - 1] == 0) n = (remaining.indexOfFirst { it > 0 } + 1).takeIf { it > 0 } ?: return null
        val regions = doc.regionMap.regions
        val candidates = regions.filterIndexed { idx, r -> plan.numbered[idx] && plan.assignment[idx] == n - 1 && !doneRegions.contains(r.id) }
        if (candidates.isEmpty()) return null
        val r = candidates[Random.nextInt(candidates.size)]
        if (n != selectedNumber) selectNumber(n)
        doc.fillRegion(r, plan.colors[n - 1])
        numbersRedo.clear()
        markDone(r, n, pushHistory = true)
        return r
    }

    // ------------------------------------------------------------------ saving & export

    /** Persists progress; [onDone] runs on the main thread afterwards (also when nothing needed saving). */
    fun save(onDone: (() -> Unit)? = null) {
        val doc = document
        if (doc == null || !doc.modified) {
            onDone?.invoke()
            return
        }
        val key = repo.workKey(page, mode)
        val colorCopy = doc.colorBitmap.copy(Bitmap.Config.ARGB_8888, false)
        val thumb = doc.renderComposite(480)
        val meta = JSONObject()
            .put("updated", System.currentTimeMillis())
            .put("recent", JSONArray(recentColors.toList()))
        if (mode == ColoringMode.NUMBERS) {
            meta.put("completed", JSONArray(doneRegions.toList()))
            meta.put("selected", selectedNumber)
            meta.put("done", completed)
        }
        doc.markSaved()
        saveScope.launch {
            withContext(Dispatchers.IO) { repo.saveWork(key, colorCopy, thumb, meta) }
            onDone?.invoke()
        }
    }

    fun composite(): Bitmap? = document?.renderComposite()

    suspend fun exportToGallery(): Boolean {
        val bmp = composite() ?: return false
        return withContext(Dispatchers.IO) { repo.exportToGallery(bmp, page.title) }
    }

    suspend fun shareIntent(): Intent? {
        val bmp = composite() ?: return null
        return withContext(Dispatchers.IO) { repo.shareIntent(bmp, page.title) }
    }
}
