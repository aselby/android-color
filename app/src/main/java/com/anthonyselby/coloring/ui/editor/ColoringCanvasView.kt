package com.anthonyselby.coloring.ui.editor

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.os.Build
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import android.view.ViewConfiguration
import kotlin.math.hypot
import kotlin.math.min

/**
 * Shows a page with pinch-zoom and pan, and turns touches into taps or strokes in page
 * coordinates. Two fingers always zoom/pan; one finger paints or pans depending on
 * [singleFingerPans].
 */
class ColoringCanvasView(context: Context) : View(context) {

    interface Listener {
        /** Single tap in page coordinates; return true when something was painted. */
        fun onTap(x: Float, y: Float): Boolean
        fun onStrokeStart(x: Float, y: Float)
        fun onStrokeMove(x: Float, y: Float)
        fun onStrokeEnd()
        fun onStrokeCancel()
    }

    var listener: Listener? = null

    /** Draws the page content in page coordinates (0,0)-(pageW,pageH). */
    var pageDrawer: ((Canvas) -> Unit)? = null

    /** When true a one-finger drag pans the picture instead of painting. */
    var singleFingerPans = true

    private var pageW = 0f
    private var pageH = 0f
    private val matrix = Matrix()
    private val inverse = Matrix()
    private val values = FloatArray(9)
    private var fitScale = 1f
    private val pt = FloatArray(2)
    private val pageRect = RectF()
    private val pagePaint = Paint().apply { color = Color.WHITE }
    private val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = 0xFFB0B0B0.toInt()
    }

    private enum class Mode { NONE, PENDING, DRAW, TRANSFORM }

    private var mode = Mode.NONE
    private var downX = 0f
    private var downY = 0f
    private var lastFocusX = 0f
    private var lastFocusY = 0f
    private var strokeStarted = false
    private val touchSlop = ViewConfiguration.get(context).scaledTouchSlop.toFloat()

    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScale(d: ScaleGestureDetector): Boolean {
            val f = d.scaleFactor
            matrix.postScale(f, f, d.focusX, d.focusY)
            clampMatrix()
            invalidate()
            return true
        }
    }).apply { isQuickScaleEnabled = false }

    init {
        // The Android emulator's GPU translation layer crashes on this view's large bitmap draws,
        // so emulators rasterise it in software; real devices keep hardware rendering.
        if (isEmulator()) setLayerType(LAYER_TYPE_SOFTWARE, null)
    }

    private fun isEmulator(): Boolean =
        Build.HARDWARE.contains("ranchu") || Build.HARDWARE.contains("goldfish") ||
            Build.FINGERPRINT.contains("generic") || Build.MODEL.contains("Emulator") ||
            Build.MODEL.contains("Android SDK built for")

    fun setPageSize(w: Int, h: Int) {
        if (pageW == w.toFloat() && pageH == h.toFloat()) return
        pageW = w.toFloat()
        pageH = h.toFloat()
        pageRect.set(0f, 0f, pageW, pageH)
        fitToScreen()
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        fitToScreen()
    }

    fun fitToScreen() {
        if (width == 0 || height == 0 || pageW == 0f || pageH == 0f) return
        fitScale = min(width / pageW, height / pageH) * 0.97f
        matrix.reset()
        matrix.postScale(fitScale, fitScale)
        matrix.postTranslate((width - pageW * fitScale) / 2f, (height - pageH * fitScale) / 2f)
        invalidate()
    }

    /** Centres the view on a page point at the given zoom factor relative to "fit". */
    fun zoomTo(px: Float, py: Float, factor: Float) {
        if (width == 0 || pageW == 0f) return
        val s = fitScale * factor
        matrix.reset()
        matrix.postScale(s, s)
        matrix.postTranslate(width / 2f - px * s, height / 2f - py * s)
        clampMatrix()
        invalidate()
    }

    private fun currentScale(): Float {
        matrix.getValues(values)
        return values[Matrix.MSCALE_X]
    }

    private fun clampMatrix() {
        if (width == 0 || pageW == 0f) return
        matrix.getValues(values)
        var scale = values[Matrix.MSCALE_X]
        val minS = fitScale * 0.85f
        val maxS = fitScale * 16f
        if (scale < minS || scale > maxS) {
            val ns = scale.coerceIn(minS, maxS)
            matrix.postScale(ns / scale, ns / scale, width / 2f, height / 2f)
            matrix.getValues(values)
            scale = ns
        }
        val contentW = pageW * scale
        val contentH = pageH * scale
        val vw = width.toFloat()
        val vh = height.toFloat()
        val margin = 48f
        values[Matrix.MTRANS_X] =
            if (contentW <= vw) (vw - contentW) / 2f
            else values[Matrix.MTRANS_X].coerceIn(vw - contentW - margin, margin)
        values[Matrix.MTRANS_Y] =
            if (contentH <= vh) (vh - contentH) / 2f
            else values[Matrix.MTRANS_Y].coerceIn(vh - contentH - margin, margin)
        matrix.setValues(values)
    }

    private fun toPage(x: Float, y: Float): FloatArray {
        matrix.invert(inverse)
        pt[0] = x
        pt[1] = y
        inverse.mapPoints(pt)
        return pt
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (pageW == 0f) return
        canvas.save()
        canvas.concat(matrix)
        canvas.drawRect(pageRect, pagePaint)
        pageDrawer?.invoke(canvas)
        borderPaint.strokeWidth = 1.5f / currentScale()
        canvas.drawRect(pageRect, borderPaint)
        canvas.restore()
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        scaleDetector.onTouchEvent(e)
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                parent?.requestDisallowInterceptTouchEvent(true)
                downX = e.x
                downY = e.y
                lastFocusX = e.x
                lastFocusY = e.y
                mode = Mode.PENDING
                strokeStarted = false
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                if (strokeStarted) {
                    listener?.onStrokeCancel()
                    strokeStarted = false
                }
                mode = Mode.TRANSFORM
                updateFocus(e, -1)
            }
            MotionEvent.ACTION_MOVE -> {
                when (mode) {
                    Mode.TRANSFORM -> {
                        var sx = 0f
                        var sy = 0f
                        for (i in 0 until e.pointerCount) { sx += e.getX(i); sy += e.getY(i) }
                        val fx = sx / e.pointerCount
                        val fy = sy / e.pointerCount
                        matrix.postTranslate(fx - lastFocusX, fy - lastFocusY)
                        lastFocusX = fx
                        lastFocusY = fy
                        clampMatrix()
                        invalidate()
                    }
                    Mode.PENDING, Mode.DRAW -> {
                        if (mode == Mode.PENDING && hypot(e.x - downX, e.y - downY) > touchSlop) {
                            if (singleFingerPans) {
                                mode = Mode.TRANSFORM
                                lastFocusX = e.x
                                lastFocusY = e.y
                            } else {
                                mode = Mode.DRAW
                                val p = toPage(downX, downY)
                                listener?.onStrokeStart(p[0], p[1])
                                strokeStarted = true
                            }
                        }
                        if (mode == Mode.DRAW && strokeStarted) {
                            for (i in 0 until e.historySize) {
                                val p = toPage(e.getHistoricalX(i), e.getHistoricalY(i))
                                listener?.onStrokeMove(p[0], p[1])
                            }
                            val p = toPage(e.x, e.y)
                            listener?.onStrokeMove(p[0], p[1])
                        }
                    }
                    Mode.NONE -> {}
                }
            }
            MotionEvent.ACTION_POINTER_UP -> updateFocus(e, e.actionIndex)
            MotionEvent.ACTION_UP -> {
                if (strokeStarted) {
                    listener?.onStrokeEnd()
                    strokeStarted = false
                } else if (mode == Mode.PENDING) {
                    val p = toPage(e.x, e.y)
                    if (listener?.onTap(p[0], p[1]) == true) {
                        performHapticFeedback(HapticFeedbackConstants.CONTEXT_CLICK)
                    }
                    performClick()
                }
                mode = Mode.NONE
            }
            MotionEvent.ACTION_CANCEL -> {
                if (strokeStarted) listener?.onStrokeCancel()
                strokeStarted = false
                mode = Mode.NONE
            }
        }
        return true
    }

    private fun updateFocus(e: MotionEvent, skipIndex: Int) {
        var sx = 0f
        var sy = 0f
        var n = 0
        for (i in 0 until e.pointerCount) {
            if (i == skipIndex) continue
            sx += e.getX(i)
            sy += e.getY(i)
            n++
        }
        if (n > 0) {
            lastFocusX = sx / n
            lastFocusY = sy / n
        }
    }
}
