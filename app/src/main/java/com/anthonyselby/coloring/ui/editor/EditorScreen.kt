package com.anthonyselby.coloring.ui.editor

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Redo
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Brush
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Colorize
import androidx.compose.material.icons.filled.Create
import androidx.compose.material.icons.filled.FitScreen
import androidx.compose.material.icons.filled.FormatColorFill
import androidx.compose.material.icons.filled.Gradient
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.RestartAlt
import androidx.compose.material.icons.filled.SaveAlt
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Slider
import androidx.compose.material3.SmallFloatingActionButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.anthonyselby.coloring.ColoringApplication
import com.anthonyselby.coloring.R
import com.anthonyselby.coloring.data.ColoringMode
import com.anthonyselby.coloring.data.PageInfo
import com.anthonyselby.coloring.data.PageRepository
import com.anthonyselby.coloring.data.Palettes
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

@Composable
fun EditorScreen(repo: PageRepository, page: PageInfo, mode: ColoringMode, onBack: () -> Unit) {
    val context = LocalContext.current
    val app = context.applicationContext as ColoringApplication
    val scope = rememberCoroutineScope()
    val controller = remember(page.id, mode) {
        EditorController(context.applicationContext, repo, page, mode, scope, app.appScope)
    }
    LaunchedEffect(controller) { controller.load() }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, controller) {
        val obs = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_STOP) controller.save() }
        lifecycleOwner.lifecycle.addObserver(obs)
        onDispose { lifecycleOwner.lifecycle.removeObserver(obs) }
    }

    var leaving by remember { mutableStateOf(false) }
    val leave: () -> Unit = {
        if (!leaving) {
            leaving = true
            controller.save { onBack() }
        }
    }
    BackHandler(onBack = leave)

    var showDone by remember { mutableStateOf(false) }
    var showPicker by remember { mutableStateOf(false) }
    var showReset by remember { mutableStateOf(false) }
    var canvasView by remember { mutableStateOf<ColoringCanvasView?>(null) }
    val doc = controller.document

    Column(
        Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surface)
            .safeDrawingPadding(),
    ) {
        EditorTopBar(controller, onBack = leave, onReset = { showReset = true }, onDone = { showDone = true })
        Box(
            Modifier
                .weight(1f)
                .fillMaxWidth()
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)),
        ) {
            AndroidView(
                factory = { ctx ->
                    ColoringCanvasView(ctx).also { v ->
                        v.listener = controller
                        v.pageDrawer = { c -> controller.drawPage(c) }
                        controller.invalidate = { v.postInvalidateOnAnimation() }
                        canvasView = v
                    }
                },
                update = { v ->
                    v.singleFingerPans = controller.singleFingerPans
                    doc?.let { v.setPageSize(it.width, it.height) }
                },
                modifier = Modifier.fillMaxSize(),
            )
            if (controller.loading) {
                Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator()
                    Spacer(Modifier.height(12.dp))
                    Text("Preparing your picture…", style = MaterialTheme.typography.bodyMedium)
                }
            }
            controller.loadError?.let { Text(it, Modifier.align(Alignment.Center).padding(24.dp), textAlign = TextAlign.Center) }
            SmallFloatingActionButton(
                onClick = { canvasView?.fitToScreen() },
                modifier = Modifier.align(Alignment.TopEnd).padding(10.dp),
                containerColor = MaterialTheme.colorScheme.surface,
            ) { Icon(Icons.Default.FitScreen, contentDescription = "Fit picture to screen") }

            controller.message?.let { msg ->
                LaunchedEffect(controller.messageTick) {
                    delay(2000)
                    controller.message = null
                }
                Surface(
                    Modifier.align(Alignment.BottomCenter).padding(16.dp),
                    shape = RoundedCornerShape(20.dp),
                    color = MaterialTheme.colorScheme.inverseSurface,
                    contentColor = MaterialTheme.colorScheme.inverseOnSurface,
                    shadowElevation = 4.dp,
                ) { Text(msg, Modifier.padding(horizontal = 16.dp, vertical = 10.dp), style = MaterialTheme.typography.bodyMedium) }
            }
        }
        BottomPanel(controller, onCustomColor = { showPicker = true })
    }

    if (showPicker) {
        ColorPickerDialog(
            initial = controller.baseColor,
            onDismiss = { showPicker = false },
            onPick = { controller.pickCustomColor(it); showPicker = false },
        )
    }
    if (showReset) {
        AlertDialog(
            onDismissRequest = { showReset = false },
            title = { Text("Start over?") },
            text = { Text("This clears all the color on this picture.") },
            confirmButton = { TextButton(onClick = { controller.resetAll(); showReset = false }) { Text("Clear") } },
            dismissButton = { TextButton(onClick = { showReset = false }) { Text("Cancel") } },
        )
    }
    if (showDone) {
        DoneDialog(controller, onDismiss = { showDone = false }, onLeave = { showDone = false; leave() })
    }
}

@Composable
private fun EditorTopBar(c: EditorController, onBack: () -> Unit, onReset: () -> Unit, onDone: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
        Text(
            c.page.title,
            style = MaterialTheme.typography.titleMedium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        IconButton(onClick = c::undo, enabled = c.canUndo) { Icon(Icons.AutoMirrored.Filled.Undo, contentDescription = "Undo") }
        IconButton(onClick = c::redo, enabled = c.canRedo) { Icon(Icons.AutoMirrored.Filled.Redo, contentDescription = "Redo") }
        if (c.mode == ColoringMode.NUMBERS) {
            IconButton(onClick = { if (c.hint() == null) c.showMessage("Nothing left to hint!") }) {
                Icon(Icons.Default.Lightbulb, contentDescription = "Hint", tint = Color(0xFFE91E63))
            }
        }
        IconButton(onClick = onReset, enabled = c.document != null) { Icon(Icons.Default.RestartAlt, contentDescription = "Start over") }
        IconButton(onClick = onDone, enabled = c.document != null) {
            Icon(Icons.Default.Check, contentDescription = "Done", tint = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun BottomPanel(c: EditorController, onCustomColor: () -> Unit) {
    Surface(tonalElevation = 3.dp, shadowElevation = 8.dp) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            if (c.mode == ColoringMode.FREE) {
                ToolRow(c)
                if (c.isStrokeTool) BrushSizeRow(c)
                SlidersRow(c)
                SwatchRow(c)
                PaletteNav(c, onCustomColor)
            } else {
                NumberChips(c)
                Text(
                    if (c.completed) "All done! Tap ✓ to save or share." else "Tap the areas marked ${c.selectedNumber}. Drag to move, pinch to zoom.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Composable
private fun ToolRow(c: EditorController) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.Top,
    ) {
        ToolButton(c.tool == Tool.FILL, "Fill", { c.selectTool(Tool.FILL) }) { Icon(Icons.Default.FormatColorFill, null) }
        ToolButton(c.tool == Tool.GRADIENT, "Shine", { c.selectTool(Tool.GRADIENT) }) { Icon(Icons.Default.Gradient, null) }
        ToolButton(c.tool == Tool.BRUSH, "Brush", { c.selectTool(Tool.BRUSH) }) { Icon(Icons.Default.Brush, null) }
        ToolButton(c.tool == Tool.PENCIL, "Pencil", { c.selectTool(Tool.PENCIL) }) { Icon(Icons.Default.Create, null) }
        ToolButton(c.tool == Tool.ERASER, "Eraser", { c.selectTool(Tool.ERASER) }) { Icon(painterResource(R.drawable.ic_eraser), null) }
        ToolButton(c.tool == Tool.EYEDROPPER, "Pick", { c.selectTool(Tool.EYEDROPPER) }) { Icon(Icons.Default.Colorize, null) }
    }
}

@Composable
private fun ToolButton(selected: Boolean, label: String, onClick: () -> Unit, icon: @Composable () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.clip(RoundedCornerShape(12.dp)).clickable(onClick = onClick).padding(horizontal = 6.dp, vertical = 2.dp),
    ) {
        Box(
            Modifier
                .size(42.dp)
                .clip(CircleShape)
                .background(if (selected) scheme.primaryContainer else scheme.surfaceVariant)
                .then(if (selected) Modifier.border(2.dp, scheme.primary, CircleShape) else Modifier),
            contentAlignment = Alignment.Center,
        ) { icon() }
        Text(label, style = MaterialTheme.typography.labelSmall, color = if (selected) scheme.primary else scheme.onSurfaceVariant)
    }
}

@Composable
private fun BrushSizeRow(c: EditorController) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(
            Modifier.size(28.dp),
            contentAlignment = Alignment.Center,
        ) {
            Box(
                Modifier
                    .size((6 + 22 * (c.brushSize / 160f)).dp)
                    .clip(CircleShape)
                    .background(Color(Palettes.shade(c.baseColor, c.shade)))
                    .border(1.dp, Color.Black.copy(alpha = 0.2f), CircleShape),
            )
        }
        Slider(
            value = c.brushSize,
            onValueChange = { c.brushSize = it },
            valueRange = 3f..160f,
            modifier = Modifier.weight(1f).height(24.dp),
        )
        FilterChip(
            selected = c.stayInside,
            onClick = { c.stayInside = !c.stayInside },
            label = { Text("In lines", style = MaterialTheme.typography.labelSmall) },
        )
    }
}

@Composable
private fun SlidersRow(c: EditorController) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Column(Modifier.weight(1f)) {
            Text("Opacity ${(c.opacity * 100).roundToInt()}%", style = MaterialTheme.typography.labelSmall)
            Slider(
                value = c.opacity,
                onValueChange = { c.opacity = it },
                valueRange = 0.1f..1f,
                modifier = Modifier.fillMaxWidth().height(24.dp),
            )
        }
        Column(Modifier.weight(1f)) {
            Text("Shade", style = MaterialTheme.typography.labelSmall)
            ShadeBar(c)
        }
    }
}

@Composable
private fun ShadeBar(c: EditorController) {
    val steps = (-3..3).toList()
    val colors = steps.map { Color(Palettes.shade(c.baseColor, it)) }
    Box(
        Modifier
            .fillMaxWidth()
            .height(30.dp)
            .clip(RoundedCornerShape(15.dp))
            .background(Brush.horizontalGradient(colors))
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(15.dp)),
    ) {
        Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
            steps.forEach { s ->
                val sel = s == c.shade
                Box(
                    Modifier
                        .size(if (sel) 24.dp else 14.dp)
                        .clip(CircleShape)
                        .background(if (sel) Color(Palettes.shade(c.baseColor, s)) else Color.Transparent)
                        .border(2.dp, Color.White, CircleShape)
                        .clickable { c.shade = s },
                )
            }
        }
    }
}

@Composable
private fun SwatchRow(c: EditorController) {
    val colors = c.swatches
    Row(
        Modifier.fillMaxWidth().height(46.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (colors.isEmpty()) {
            Text("Colors you use will show up here", style = MaterialTheme.typography.bodySmall)
        }
        colors.take(12).forEach { col ->
            Swatch(color = col, selected = col == c.baseColor, size = if (colors.size > 10) 32.dp else 38.dp) { c.selectColor(col) }
        }
    }
}

@Composable
fun Swatch(color: Int, selected: Boolean, size: Dp = 38.dp, onClick: () -> Unit) {
    val cc = Color(color)
    Box(
        Modifier
            .size(size)
            .clip(CircleShape)
            .background(cc)
            .border(
                if (selected) 3.dp else 1.dp,
                if (selected) MaterialTheme.colorScheme.primary else Color.Black.copy(alpha = 0.18f),
                CircleShape,
            )
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        if (selected) {
            Box(
                Modifier.size(size / 3).clip(CircleShape)
                    .background(if (cc.luminance() > 0.5f) Color.Black.copy(alpha = 0.55f) else Color.White.copy(alpha = 0.9f)),
            )
        }
    }
}

@Composable
private fun PaletteNav(c: EditorController, onCustomColor: () -> Unit) {
    var menu by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = { c.showingRecent = !c.showingRecent }) {
            Icon(
                Icons.Default.History, contentDescription = "Recent colors",
                tint = if (c.showingRecent) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        IconButton(onClick = onCustomColor) { Icon(Icons.Default.Palette, contentDescription = "Custom color") }
        Spacer(Modifier.weight(1f))
        IconButton(onClick = c::prevPalette) { Icon(Icons.Default.ChevronLeft, contentDescription = "Previous palette") }
        Box {
            TextButton(onClick = { menu = true }) {
                Text(c.paletteName, style = MaterialTheme.typography.titleSmall)
                Icon(Icons.Default.ArrowDropDown, null)
            }
            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }, modifier = Modifier.heightIn(max = 420.dp)) {
                Palettes.all.forEachIndexed { i, p ->
                    DropdownMenuItem(
                        text = {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                p.colors.take(6).forEach { col ->
                                    Box(Modifier.size(14.dp).clip(CircleShape).background(Color(col)).border(1.dp, Color.Black.copy(alpha = 0.15f), CircleShape))
                                }
                                Spacer(Modifier.width(6.dp))
                                Text(p.name, fontWeight = if (i == c.paletteIndex && !c.showingRecent) FontWeight.Bold else FontWeight.Normal)
                            }
                        },
                        onClick = { c.setPalette(i); menu = false },
                    )
                }
            }
        }
        IconButton(onClick = c::nextPalette) { Icon(Icons.Default.ChevronRight, contentDescription = "Next palette") }
        Spacer(Modifier.weight(1f))
        Box(
            Modifier.size(34.dp).clip(CircleShape).background(Color(c.currentColor)).border(1.dp, Color.Black.copy(alpha = 0.2f), CircleShape),
        )
    }
}

@Composable
private fun NumberChips(c: EditorController) {
    val plan = c.plan ?: return
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = PaddingValues(horizontal = 4.dp, vertical = 4.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        items((1..plan.numberCount).toList()) { n ->
            val left = c.remaining.getOrNull(n - 1) ?: 0
            val done = left == 0
            val col = Color(plan.colors[n - 1])
            val selected = n == c.selectedNumber
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.clickable { c.selectNumber(n) }) {
                Box(
                    Modifier
                        .size(if (selected) 50.dp else 42.dp)
                        .clip(CircleShape)
                        .background(if (done) col.copy(alpha = 0.35f) else col)
                        .border(if (selected) 3.dp else 1.dp, if (selected) MaterialTheme.colorScheme.primary else Color.Black.copy(alpha = 0.2f), CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    if (done) Icon(Icons.Default.Check, null, tint = if (col.luminance() > 0.5f) Color.Black else Color.White)
                    else Text(
                        n.toString(),
                        fontWeight = FontWeight.Bold,
                        color = if (col.luminance() > 0.5f) Color.Black else Color.White,
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
                Text(if (done) "done" else "$left left", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun DoneDialog(c: EditorController, onDismiss: () -> Unit, onLeave: () -> Unit) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val preview = remember { c.document?.renderComposite(720)?.asImageBitmap() }
    var status by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val doExport: () -> Unit = {
        scope.launch {
            busy = true
            status = if (c.exportToGallery()) "Saved to Pictures / Color Studio" else "Sorry, the picture could not be saved."
            busy = false
        }
    }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) doExport() else status = "Storage permission is needed to save."
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(c.page.title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                preview?.let {
                    androidx.compose.foundation.Image(
                        it, contentDescription = null,
                        modifier = Modifier.fillMaxWidth().heightIn(max = 300.dp).clip(RoundedCornerShape(12.dp)).background(Color.White),
                        contentScale = ContentScale.Fit,
                    )
                }
                status?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(
                        enabled = !busy,
                        onClick = {
                            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
                                ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED
                            ) permission.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE) else doExport()
                        },
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.Default.SaveAlt, null)
                        Spacer(Modifier.width(6.dp))
                        Text("Save")
                    }
                    OutlinedButton(
                        enabled = !busy,
                        onClick = {
                            scope.launch {
                                busy = true
                                c.shareIntent()?.let { context.startActivity(Intent.createChooser(it, "Share your picture")) }
                                busy = false
                            }
                        },
                        modifier = Modifier.weight(1f),
                    ) {
                        Icon(Icons.Default.Share, null)
                        Spacer(Modifier.width(6.dp))
                        Text("Share")
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onLeave) { Text("Back to gallery") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Keep coloring") } },
    )
}
