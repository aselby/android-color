package com.anthonyselby.coloring

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
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val app = application as ColoringApplication
        setContent {
            ColorStudioTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    AppRoot(app.repository)
                }
            }
        }
    }
}

@Composable
fun AppRoot(repo: PageRepository) {
    var screen by remember { mutableStateOf<Screen>(Screen.Home) }
    var refreshTick by remember { mutableIntStateOf(0) }
    when (val s = screen) {
        is Screen.Home -> HomeScreen(
            repo = repo,
            refreshTick = refreshTick,
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
