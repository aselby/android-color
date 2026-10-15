package com.anthonyselby.coloring

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.IntentCompat
import com.anthonyselby.coloring.data.ColoringMode
import com.anthonyselby.coloring.data.PageInfo
import com.anthonyselby.coloring.data.PageRepository
import com.anthonyselby.coloring.ui.editor.EditorScreen
import com.anthonyselby.coloring.ui.home.HomeScreen
import com.anthonyselby.coloring.ui.theme.ColorStudioTheme

sealed class Screen {
    data object Home : Screen()
    data class Editor(val page: PageInfo, val mode: ColoringMode) : Screen()
}

class MainActivity : ComponentActivity() {
    /** An image shared to the app from another app (gallery, browser), waiting to be imported. */
    private val sharedImage = mutableStateOf<Uri?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        sharedImage.value = sharedImageFrom(intent)
        val app = application as ColoringApplication
        setContent {
            ColorStudioTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    AppRoot(app.repository, sharedImage.value) { sharedImage.value = null }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        sharedImageFrom(intent)?.let { sharedImage.value = it }
    }

    private fun sharedImageFrom(intent: Intent?): Uri? {
        if (intent == null) return null
        return when (intent.action) {
            Intent.ACTION_SEND -> IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)
            Intent.ACTION_VIEW -> intent.data
            else -> null
        }
    }
}

@Composable
fun AppRoot(repo: PageRepository, sharedImage: Uri?, onSharedImageHandled: () -> Unit) {
    var screen by remember { mutableStateOf<Screen>(Screen.Home) }
    var refreshTick by remember { mutableIntStateOf(0) }
    if (sharedImage != null && screen !is Screen.Home) screen = Screen.Home
    when (val s = screen) {
        is Screen.Home -> HomeScreen(
            repo = repo,
            refreshTick = refreshTick,
            externalImport = sharedImage,
            onExternalImportHandled = onSharedImageHandled,
            onOpen = { page, mode -> screen = Screen.Editor(page, mode) },
        )
        is Screen.Editor -> EditorScreen(
            repo = repo,
            page = s.page,
            mode = s.mode,
            onBack = {
                refreshTick++
                screen = Screen.Home
            },
        )
    }
}
