package com.anthonyselby.coloring.ui.editor

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.drag
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import java.util.Locale
import kotlin.math.roundToInt
import android.graphics.Color as AColor

/** Hue / saturation / value picker so any colour at all can be used. */
@Composable
fun ColorPickerDialog(initial: Int, onDismiss: () -> Unit, onPick: (Int) -> Unit) {
    val hsv0 = remember(initial) { FloatArray(3).also { AColor.colorToHSV(initial, it) } }
    var hue by remember { mutableFloatStateOf(hsv0[0]) }
    var sat by remember { mutableFloatStateOf(hsv0[1]) }
    var value by remember { mutableFloatStateOf(hsv0[2]) }
    val argb = AColor.HSVToColor(floatArrayOf(hue, sat, value)) or 0xFF000000.toInt()
    var hexText by remember { mutableStateOf(String.format(Locale.US, "%06X", argb and 0xFFFFFF)) }
    LaunchedEffect(argb) { hexText = String.format(Locale.US, "%06X", argb and 0xFFFFFF) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Custom color") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                var boxSize by remember { mutableStateOf(IntSize.Zero) }
                val hueColor = Color(AColor.HSVToColor(floatArrayOf(hue, 1f, 1f)))
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(180.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .onSizeChanged { boxSize = it }
                        .background(Brush.horizontalGradient(listOf(Color.White, hueColor)))
                        .background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black)))
                        .pointerInput(Unit) {
                            awaitEachGesture {
                                val down = awaitFirstDown()
                                fun update(p: Offset) {
                                    if (boxSize.width > 0 && boxSize.height > 0) {
                                        sat = (p.x / boxSize.width).coerceIn(0f, 1f)
                                        value = 1f - (p.y / boxSize.height).coerceIn(0f, 1f)
                                    }
                                }
                                update(down.position)
                                down.consume()
                                drag(down.id) { change ->
                                    update(change.position)
                                    change.consume()
                                }
                            }
                        },
                ) {
                    Box(
                        Modifier
                            .offset {
                                IntOffset(
                                    (sat * boxSize.width - 10.dp.toPx()).roundToInt(),
                                    ((1f - value) * boxSize.height - 10.dp.toPx()).roundToInt(),
                                )
                            }
                            .size(20.dp)
                            .border(2.dp, Color.White, CircleShape)
                            .border(3.dp, Color.Black.copy(alpha = 0.35f), CircleShape),
                    )
                }

                var barW by remember { mutableIntStateOf(0) }
                val hueColors = (0..6).map { Color(AColor.HSVToColor(floatArrayOf((it * 60f) % 360f, 1f, 1f))) }
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(28.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .onSizeChanged { barW = it.width }
                        .background(Brush.horizontalGradient(hueColors))
                        .pointerInput(Unit) {
                            awaitEachGesture {
                                val down = awaitFirstDown()
                                fun update(p: Offset) {
                                    if (barW > 0) hue = (p.x / barW * 360f).coerceIn(0f, 359.9f)
                                }
                                update(down.position)
                                down.consume()
                                drag(down.id) { change ->
                                    update(change.position)
                                    change.consume()
                                }
                            }
                        },
                ) {
                    Box(
                        Modifier
                            .offset { IntOffset((hue / 360f * barW - 8.dp.toPx()).roundToInt(), 0) }
                            .size(16.dp, 28.dp)
                            .border(2.dp, Color.White, RoundedCornerShape(8.dp)),
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Box(
                        Modifier.size(48.dp).clip(CircleShape).background(Color(argb))
                            .border(1.dp, MaterialTheme.colorScheme.outline, CircleShape),
                    )
                    OutlinedTextField(
                        value = hexText,
                        onValueChange = { t ->
                            val clean = t.trim().removePrefix("#").take(6)
                            hexText = clean
                            if (clean.length == 6) clean.toIntOrNull(16)?.let { rgb ->
                                val hsv = FloatArray(3)
                                AColor.colorToHSV(rgb or 0xFF000000.toInt(), hsv)
                                hue = hsv[0]; sat = hsv[1]; value = hsv[2]
                            }
                        },
                        prefix = { Text("#") },
                        label = { Text("Hex") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        },
        confirmButton = { TextButton(onClick = { onPick(argb) }) { Text("Use color") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
