package com.anthonyselby.coloring.ui.home

import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.anthonyselby.coloring.data.PageInfo
import com.anthonyselby.coloring.data.PageRepository
import com.anthonyselby.coloring.engine.LineArtConverter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private enum class ImportKind { CARTOON, PHOTO, DRAWING }

/** Turns a picked image into a new coloring page, with a live preview. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ImportDialog(repo: PageRepository, uri: Uri, onDismiss: () -> Unit, onDone: (PageInfo) -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var source by remember { mutableStateOf<Bitmap?>(null) }
    var failed by remember { mutableStateOf(false) }
    var kind by remember { mutableStateOf(ImportKind.CARTOON) }
    var detail by remember { mutableFloatStateOf(0.5f) }
    var preview by remember { mutableStateOf<Bitmap?>(null) }
    var title by remember { mutableStateOf("My picture") }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(uri) {
        source = withContext(Dispatchers.IO) { runCatching { LineArtConverter.decodeScaled(context, uri, 1600) }.getOrNull() }
        if (source == null) failed = true
    }
    LaunchedEffect(source, kind, detail) {
        val s = source ?: return@LaunchedEffect
        busy = true
        preview = withContext(Dispatchers.Default) {
            when (kind) {
                ImportKind.CARTOON -> LineArtConverter.fromCartoon(s, 900, detail)
                ImportKind.PHOTO -> LineArtConverter.fromPhoto(s, 900, detail)
                ImportKind.DRAWING -> LineArtConverter.fromDrawing(s, 900)
            }
        }
        busy = false
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Make a coloring page") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(
                    Modifier.fillMaxWidth().height(260.dp).clip(RoundedCornerShape(12.dp)).background(Color.White),
                    contentAlignment = Alignment.Center,
                ) {
                    val p = preview
                    when {
                        failed -> Text("That image could not be opened.", color = MaterialTheme.colorScheme.error)
                        p != null -> Image(p.asImageBitmap(), null, Modifier.fillMaxSize().padding(4.dp), contentScale = ContentScale.Fit)
                    }
                    if (busy || (source == null && !failed)) CircularProgressIndicator()
                }
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    SegmentedButton(
                        selected = kind == ImportKind.CARTOON,
                        onClick = { kind = ImportKind.CARTOON },
                        shape = SegmentedButtonDefaults.itemShape(0, 3),
                    ) { Text("Anime", maxLines = 1) }
                    SegmentedButton(
                        selected = kind == ImportKind.PHOTO,
                        onClick = { kind = ImportKind.PHOTO },
                        shape = SegmentedButtonDefaults.itemShape(1, 3),
                    ) { Text("Photo", maxLines = 1) }
                    SegmentedButton(
                        selected = kind == ImportKind.DRAWING,
                        onClick = { kind = ImportKind.DRAWING },
                        shape = SegmentedButtonDefaults.itemShape(2, 3),
                    ) { Text("Sketch", maxLines = 1) }
                }
                Text(
                    when (kind) {
                        ImportKind.CARTOON -> "Best for anime, cartoons and drawings with black outlines."
                        ImportKind.PHOTO -> "Finds the edges in a photograph."
                        ImportKind.DRAWING -> "For scanned pencil or ink sketches on white paper."
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (kind != ImportKind.DRAWING) {
                    Text("Detail", style = MaterialTheme.typography.labelSmall)
                    Slider(value = detail, onValueChange = { detail = it }, valueRange = 0f..1f, modifier = Modifier.height(24.dp))
                }
                OutlinedTextField(value = title, onValueChange = { title = it }, label = { Text("Name") }, singleLine = true, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(
                enabled = source != null && !busy,
                onClick = {
                    val s = source ?: return@TextButton
                    scope.launch {
                        busy = true
                        val lines = withContext(Dispatchers.Default) {
                            when (kind) {
                                ImportKind.CARTOON -> LineArtConverter.fromCartoon(s, 1600, detail)
                                ImportKind.PHOTO -> LineArtConverter.fromPhoto(s, 1500, detail)
                                ImportKind.DRAWING -> LineArtConverter.fromDrawing(s, 1800)
                            }
                        }
                        val page = withContext(Dispatchers.IO) { repo.importLineArt(lines, title.ifBlank { "My picture" }) }
                        busy = false
                        onDone(page)
                    }
                },
            ) { Text("Add & color") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
