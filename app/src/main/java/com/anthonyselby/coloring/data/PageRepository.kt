package com.anthonyselby.coloring.data

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.LruCache
import androidx.core.content.FileProvider
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import kotlin.math.max

/** Built-in pages (assets), imported pages and saved work, all on disk. */
class PageRepository(private val app: Context) {

    val builtIn: List<PageInfo> by lazy {
        val json = app.assets.open("pages/index.json").bufferedReader().use { it.readText() }
        val arr = JSONArray(json)
        List(arr.length()) { i ->
            val o = arr.getJSONObject(i)
            PageInfo(
                id = o.getString("id"),
                title = o.getString("title"),
                category = o.getString("category"),
                difficulty = o.optInt("difficulty", 2),
                tags = o.optString("tags", ""),
            )
        }
    }

    private val importedDir: File get() = File(app.filesDir, "imported").apply { mkdirs() }
    private val workDir: File get() = File(app.filesDir, "work").apply { mkdirs() }

    private val thumbCache = object : LruCache<String, Bitmap>(40 * 1024 * 1024) {
        override fun sizeOf(key: String, value: Bitmap) = value.byteCount
    }

    fun importedPages(): List<PageInfo> =
        importedDir.listFiles()?.filter { File(it, "lines.png").exists() }?.mapNotNull { dir ->
            runCatching {
                val meta = JSONObject(File(dir, "meta.json").readText())
                PageInfo(
                    id = dir.name,
                    title = meta.optString("title", "My picture"),
                    category = "Imported",
                    difficulty = meta.optInt("difficulty", 2),
                    tags = "imported photo",
                    imported = true,
                    createdAt = meta.optLong("created", dir.lastModified()),
                )
            }.getOrNull()
        }?.sortedByDescending { it.createdAt } ?: emptyList()

    fun allPages(): List<PageInfo> = importedPages() + builtIn

    fun loadLineArt(page: PageInfo): Bitmap {
        val opts = BitmapFactory.Options().apply {
            inPreferredConfig = Bitmap.Config.ARGB_8888
            inScaled = false
            inMutable = false
        }
        return if (page.imported) {
            BitmapFactory.decodeFile(File(File(importedDir, page.id), "lines.png").absolutePath, opts)
        } else {
            app.assets.open("pages/${page.id}.png").use { BitmapFactory.decodeStream(it, null, opts)!! }
        }
    }

    // ------------------------------------------------------------------ work (progress)

    fun workKey(page: PageInfo, mode: ColoringMode) = "${page.id}_${mode.name.lowercase()}"
    private fun workDirFor(key: String) = File(workDir, key)

    fun hasWork(page: PageInfo, mode: ColoringMode) = File(workDirFor(workKey(page, mode)), "color.png").exists()

    fun workMeta(page: PageInfo, mode: ColoringMode): JSONObject? =
        File(workDirFor(workKey(page, mode)), "meta.json").takeIf { it.exists() }?.let {
            runCatching { JSONObject(it.readText()) }.getOrNull()
        }

    fun loadWork(key: String): Pair<Bitmap?, JSONObject?> {
        val dir = workDirFor(key)
        val color = File(dir, "color.png").takeIf { it.exists() }?.let {
            BitmapFactory.decodeFile(it.absolutePath, BitmapFactory.Options().apply {
                inPreferredConfig = Bitmap.Config.ARGB_8888
                inScaled = false
            })
        }
        val meta = File(dir, "meta.json").takeIf { it.exists() }?.let { runCatching { JSONObject(it.readText()) }.getOrNull() }
        return color to meta
    }

    fun saveWork(key: String, color: Bitmap, thumb: Bitmap, meta: JSONObject) {
        val dir = workDirFor(key).apply { mkdirs() }
        writePng(File(dir, "color.png"), color)
        writePng(File(dir, "thumb.png"), thumb)
        File(dir, "meta.json").writeText(meta.toString())
        thumbCache.remove("$key#work")
    }

    fun deleteWork(page: PageInfo, mode: ColoringMode) {
        val key = workKey(page, mode)
        workDirFor(key).deleteRecursively()
        thumbCache.remove("$key#work")
    }

    // ------------------------------------------------------------------ thumbnails

    /** Thumbnail for the gallery: the saved work if any, otherwise the plain outline on white. */
    fun thumbnail(page: PageInfo, mode: ColoringMode, maxSide: Int): Bitmap? {
        val key = workKey(page, mode)
        val workThumb = File(workDirFor(key), "thumb.png")
        val cacheKey = if (workThumb.exists()) "$key#work" else "${page.id}#line"
        thumbCache.get(cacheKey)?.let { return it }
        val bmp = if (workThumb.exists()) {
            BitmapFactory.decodeFile(workThumb.absolutePath)
        } else {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            openPage(page) { BitmapFactory.decodeStream(it, null, bounds) }
            var sample = 1
            while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
            val opts = BitmapFactory.Options().apply { inSampleSize = sample; inScaled = false }
            val lines = openPage(page) { BitmapFactory.decodeStream(it, null, opts) } ?: return null
            val out = Bitmap.createBitmap(lines.width, lines.height, Bitmap.Config.ARGB_8888)
            val c = Canvas(out)
            c.drawColor(Color.WHITE)
            c.drawBitmap(lines, 0f, 0f, Paint(Paint.FILTER_BITMAP_FLAG))
            out
        } ?: return null
        thumbCache.put(cacheKey, bmp)
        return bmp
    }

    private fun <T> openPage(page: PageInfo, block: (java.io.InputStream) -> T): T =
        if (page.imported) File(File(importedDir, page.id), "lines.png").inputStream().use(block)
        else app.assets.open("pages/${page.id}.png").use(block)

    // ------------------------------------------------------------------ import

    fun importLineArt(lines: Bitmap, title: String): PageInfo {
        val id = "import_${System.currentTimeMillis()}"
        val dir = File(importedDir, id).apply { mkdirs() }
        writePng(File(dir, "lines.png"), lines)
        val meta = JSONObject().put("title", title).put("created", System.currentTimeMillis())
        File(dir, "meta.json").writeText(meta.toString())
        return PageInfo(id, title, "Imported", 2, "imported photo", imported = true, createdAt = System.currentTimeMillis())
    }

    fun deleteImported(page: PageInfo) {
        if (!page.imported) return
        File(importedDir, page.id).deleteRecursively()
        for (mode in ColoringMode.entries) deleteWork(page, mode)
        thumbCache.remove("${page.id}#line")
    }

    // ------------------------------------------------------------------ export

    /** Saves a finished picture to the device gallery (Pictures/Color Studio). */
    fun exportToGallery(bitmap: Bitmap, name: String): Boolean {
        val fileName = "${name.replace(Regex("[^A-Za-z0-9_-]"), "_")}_${System.currentTimeMillis()}.png"
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                    put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                    put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/Color Studio")
                    put(MediaStore.Images.Media.IS_PENDING, 1)
                }
                val resolver = app.contentResolver
                val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return false
                resolver.openOutputStream(uri)?.use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) } ?: return false
                values.clear()
                values.put(MediaStore.Images.Media.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            } else {
                @Suppress("DEPRECATION")
                val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), "Color Studio").apply { mkdirs() }
                val file = File(dir, fileName)
                writePng(file, bitmap)
                @Suppress("DEPRECATION")
                app.sendBroadcast(Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE, Uri.fromFile(file)))
            }
            true
        } catch (_: Exception) {
            false
        }
    }

    /** Builds a share sheet intent for a picture. */
    fun shareIntent(bitmap: Bitmap, name: String): Intent {
        val dir = File(app.cacheDir, "shared").apply { mkdirs() }
        val file = File(dir, "${name.replace(Regex("[^A-Za-z0-9_-]"), "_")}.png")
        writePng(file, bitmap)
        val uri = FileProvider.getUriForFile(app, "${app.packageName}.fileprovider", file)
        return Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }

    private fun writePng(file: File, bitmap: Bitmap) {
        val tmp = File(file.parentFile, file.name + ".tmp")
        FileOutputStream(tmp).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        if (!tmp.renameTo(file)) {
            file.delete()
            tmp.renameTo(file)
        }
    }
}
