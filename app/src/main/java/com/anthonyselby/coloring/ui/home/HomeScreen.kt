package com.anthonyselby.coloring.ui.home

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.anthonyselby.coloring.data.ColoringMode
import com.anthonyselby.coloring.data.PageInfo
import com.anthonyselby.coloring.data.PageRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class WorkStatus { NONE, IN_PROGRESS, DONE }

fun PageRepository.workStatus(page: PageInfo, mode: ColoringMode): WorkStatus = when {
    !hasWork(page, mode) -> WorkStatus.NONE
    workMeta(page, mode)?.optBoolean("done") == true -> WorkStatus.DONE
    else -> WorkStatus.IN_PROGRESS
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    repo: PageRepository,
    refreshTick: Int,
    onOpen: (PageInfo, ColoringMode) -> Unit,
    externalImport: Uri? = null,
    onExternalImportHandled: () -> Unit = {},
) {
    val scope = rememberCoroutineScope()
    var mode by rememberSaveable { mutableStateOf(ColoringMode.FREE) }
    var query by rememberSaveable { mutableStateOf("") }
    var category by rememberSaveable { mutableStateOf("All") }
    var pages by remember { mutableStateOf<List<PageInfo>>(emptyList()) }
    var status by remember { mutableStateOf<Map<String, WorkStatus>>(emptyMap()) }
    var localTick by remember { mutableIntStateOf(0) }
    var importUri by remember { mutableStateOf<Uri?>(null) }
    var menuFor by remember { mutableStateOf<PageInfo?>(null) }

    LaunchedEffect(refreshTick, localTick, mode) {
        val (p, s) = withContext(Dispatchers.IO) {
            val all = repo.allPages()
            all to all.associate { it.id to repo.workStatus(it, mode) }
        }
        pages = p
        status = s
    }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> importUri = uri }
    LaunchedEffect(externalImport) {
        if (externalImport != null) {
            importUri = externalImport
            onExternalImportHandled()
        }
    }

    val categories = remember(pages) { listOf("All", "My Work") + pages.map { it.category }.distinct() }
    val filtered = remember(pages, query, category, status) {
        pages.filter { p ->
            p.matches(query) && when (category) {
                "All" -> true
                "My Work" -> (status[p.id] ?: WorkStatus.NONE) != WorkStatus.NONE
                else -> p.category == category
            }
        }
    }

    Column(Modifier.fillMaxSize().safeDrawingPadding()) {
        Row(
            Modifier.fillMaxWidth().padding(start = 16.dp, end = 4.dp, top = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Default.Palette, null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(8.dp))
            Text("Color Studio", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            IconButton(onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }) {
                Icon(Icons.Default.AddPhotoAlternate, contentDescription = "Import a picture")
            }
        }
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp)) {
            SegmentedButton(
                selected = mode == ColoringMode.FREE,
                onClick = { mode = ColoringMode.FREE },
                shape = SegmentedButtonDefaults.itemShape(0, 2),
            ) { Text("Free coloring") }
            SegmentedButton(
                selected = mode == ColoringMode.NUMBERS,
                onClick = { mode = ColoringMode.NUMBERS },
                shape = SegmentedButtonDefaults.itemShape(1, 2),
            ) { Text("Color by Numbers") }
        }
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            placeholder = { Text("Search for the pictures you like") },
            leadingIcon = { Icon(Icons.Default.Search, null) },
            trailingIcon = { if (query.isNotEmpty()) IconButton(onClick = { query = "" }) { Icon(Icons.Default.Close, "Clear") } },
            singleLine = true,
            shape = RoundedCornerShape(28.dp),
        )
        val selectedIdx = categories.indexOf(category).coerceAtLeast(0)
        ScrollableTabRow(selectedTabIndex = selectedIdx, edgePadding = 12.dp, divider = {}) {
            categories.forEachIndexed { i, c ->
                Tab(selected = i == selectedIdx, onClick = { category = c }, text = { Text(c) })
            }
        }
        if (filtered.isEmpty()) {
            Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text(
                    when {
                        pages.isEmpty() -> "Loading…"
                        category == "My Work" -> "Nothing here yet.\nPick a picture and start coloring!"
                        else -> "No pictures match that search."
                    },
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Adaptive(minSize = 150.dp),
                contentPadding = PaddingValues(12.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.weight(1f),
            ) {
                items(filtered, key = { it.id }) { page ->
                    PageCard(
                        repo = repo,
                        page = page,
                        mode = mode,
                        status = status[page.id] ?: WorkStatus.NONE,
                        refresh = refreshTick + localTick,
                        onClick = { onOpen(page, mode) },
                        onLongClick = { menuFor = page },
                    )
                }
            }
        }
    }

    menuFor?.let { page ->
        val st = status[page.id] ?: WorkStatus.NONE
        AlertDialog(
            onDismissRequest = { menuFor = null },
            title = { Text(page.title) },
            text = {
                Column {
                    TextButton(
                        enabled = st != WorkStatus.NONE,
                        onClick = {
                            scope.launch {
                                withContext(Dispatchers.IO) { repo.deleteWork(page, mode) }
                                localTick++
                                menuFor = null
                            }
                        },
                    ) { Text("Clear my progress on this picture") }
                    if (page.imported) {
                        TextButton(onClick = {
                            scope.launch {
                                withContext(Dispatchers.IO) { repo.deleteImported(page) }
                                localTick++
                                menuFor = null
                            }
                        }) { Text("Delete this imported picture", color = MaterialTheme.colorScheme.error) }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { menuFor = null }) { Text("Close") } },
        )
    }

    importUri?.let { uri ->
        ImportDialog(
            repo = repo,
            uri = uri,
            onDismiss = { importUri = null },
            onDone = { page ->
                importUri = null
                localTick++
                onOpen(page, mode)
            },
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun PageCard(
    repo: PageRepository,
    page: PageInfo,
    mode: ColoringMode,
    status: WorkStatus,
    refresh: Int,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    val thumb by produceState<ImageBitmap?>(null, page.id, mode, refresh) {
        value = withContext(Dispatchers.IO) {
            runCatching { repo.thumbnail(page, mode, 400) }.getOrNull()?.asImageBitmap()
        }
    }
    ElevatedCard(Modifier.fillMaxWidth().combinedClickable(onClick = onClick, onLongClick = onLongClick)) {
        Box(Modifier.fillMaxWidth().aspectRatio(0.8f).background(Color.White)) {
            val t = thumb
            if (t != null) {
                Image(t, contentDescription = page.title, modifier = Modifier.fillMaxSize().padding(6.dp), contentScale = ContentScale.Fit)
            } else {
                CircularProgressIndicator(Modifier.align(Alignment.Center).size(24.dp), strokeWidth = 2.dp)
            }
            if (status != WorkStatus.NONE) {
                Surface(
                    Modifier.align(Alignment.TopEnd).padding(8.dp),
                    shape = RoundedCornerShape(10.dp),
                    color = if (status == WorkStatus.DONE) Color(0xFF43A047) else MaterialTheme.colorScheme.primary,
                ) {
                    Text(
                        if (status == WorkStatus.DONE) "Finished" else "In progress",
                        Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White,
                    )
                }
            }
        }
        Column(Modifier.padding(horizontal = 10.dp, vertical = 8.dp)) {
            Text(page.title, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(page.category, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.weight(1f))
                repeat(4) { i ->
                    Box(
                        Modifier.padding(start = 3.dp).size(6.dp).clip(CircleShape)
                            .background(if (i < page.difficulty) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant),
                    )
                }
            }
        }
    }
}
