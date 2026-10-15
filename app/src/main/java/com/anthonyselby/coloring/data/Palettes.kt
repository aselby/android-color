package com.anthonyselby.coloring.data

import android.graphics.Color

data class Palette(val name: String, val colors: List<Int>)

object Palettes {
    private fun hex(vararg h: String): List<Int> = h.map { ("FF$it").toLong(16).toInt() }

    /** Every palette is available; nothing is locked. */
    val all: List<Palette> = listOf(
        Palette("Basic", hex("5E4AB3", "1E90FF", "1E4DB7", "2E7D32", "FFFFFF", "000000", "FFB6C1", "F44336", "FF7043", "FFEB3B")),
        Palette("Rainbow", hex("E53935", "FB8C00", "FDD835", "7CB342", "43A047", "00897B", "00ACC1", "1E88E5", "3949AB", "8E24AA")),
        Palette("Pastel", hex("FFD1DC", "FFE4B5", "FFFACD", "D0F0C0", "B5EAD7", "C7CEEA", "E0BBE4", "FDCBFF", "F6E3CE", "D5F4FF")),
        Palette("Skin", hex("FFE0BD", "FFCD94", "EAC086", "D8A26D", "C68642", "A1665E", "8D5524", "6B4226", "4A2C17", "2E1A0F")),
        Palette("Eyes", hex("1E6FD9", "3C8DBC", "4F9A7A", "2F6B3A", "245026", "A48A4A", "6E5E2E", "7A4A33", "4B3030", "6E6E6E")),
        Palette("Make up", hex("C56BA3", "F2B6B6", "F8DCD2", "F6D7B0", "D07B7B", "8E4F5E", "283593", "8E24AA", "FF8A80", "C62828")),
        Palette("Hair", hex("FAF0BE", "E6BE8A", "C98F4D", "B55239", "8B4513", "5C3A21", "3B2A1A", "1C1C1C", "B0B0B0", "E0E0E0")),
        Palette("Forest", hex("1B4332", "2D6A4F", "40916C", "52B788", "74C69D", "95D5B2", "B7E4C7", "7F5539", "A68A64", "582F0E")),
        Palette("Ocean", hex("03045E", "023E8A", "0077B6", "0096C7", "00B4D8", "48CAE4", "90E0EF", "ADE8F4", "CAF0F8", "F1FAEE")),
        Palette("Sunset", hex("5A189A", "9D4EDD", "E63946", "F3722C", "F8961E", "F9C74F", "FFD6A5", "FFADAD", "FF8FAB", "FFB5A7")),
        Palette("Autumn", hex("6A040F", "9D0208", "D00000", "DC2F02", "E85D04", "F48C06", "FAA307", "FFBA08", "B08968", "7F5539")),
        Palette("Spring", hex("FF9AA2", "FFB7B2", "FFDAC1", "E2F0CB", "B5EAD7", "C7CEEA", "F8EDEB", "FEC89A", "D8E2DC", "FFE5D9")),
        Palette("Winter", hex("E8F1F2", "C9D6DF", "A9BCD0", "7A9CC6", "5B7DB1", "3F5E98", "26417A", "1A2C5B", "DDE6F0", "F7FBFF")),
        Palette("Neon", hex("FF007F", "FF3F00", "FFD300", "AAFF00", "00FF7F", "00FFFF", "0080FF", "7F00FF", "FF00FF", "FFFFFF")),
        Palette("Jewel", hex("9B111E", "B8336A", "4B0082", "0F52BA", "007BA7", "046307", "50C878", "FFC30B", "CC5500", "6E2C00")),
        Palette("Earth", hex("EDE0D4", "E6CCB2", "DDB892", "B08968", "9C6644", "7F5539", "582F0E", "936639", "A4AC86", "656D4A")),
        Palette("Candy", hex("FF99C8", "FCF6BD", "D0F4DE", "A9DEF9", "E4C1F9", "FFADAD", "FFD6A5", "FDFFB6", "CAFFBF", "9BF6FF")),
        Palette("Vintage", hex("8C6A5D", "C9ADA7", "F2E9E4", "9A8C98", "4A4E69", "22223B", "A3B18A", "DAD7CD", "BC6C25", "DDA15E")),
        Palette("Grays", hex("FFFFFF", "F0F0F0", "D9D9D9", "BFBFBF", "A6A6A6", "8C8C8C", "737373", "595959", "333333", "000000")),
        Palette("Metal", hex("FFD700", "DAA520", "B8860B", "C0C0C0", "A8A9AD", "71797E", "CD7F32", "B87333", "E5E4E2", "8A9597")),
        Palette("Berry", hex("4A0E2E", "7B1E4E", "A4306B", "C84B8F", "E673B5", "F2A1D1", "FFC8E6", "5E1B3A", "9E2A2B", "D1495B")),
        Palette("Tropical", hex("FF595E", "FF924C", "FFCA3A", "8AC926", "52A675", "1982C4", "4267AC", "6A4C93", "F15BB5", "00F5D4")),
        Palette("Desert", hex("F4E1C1", "E8C39E", "D9A066", "C97B4A", "A65E2E", "8C4A2F", "6E3B23", "C9C19F", "9FB7B9", "5C8D89")),
        Palette("Galaxy", hex("0B0C2A", "1B1F5E", "3A2E8C", "6C3FB3", "9B5DE5", "F15BB5", "FEE440", "00BBF9", "00F5D4", "FFFFFF")),
        Palette("Coffee", hex("3C2A21", "5C4033", "7B5B46", "9C7A5B", "BB9B7A", "D9C1A5", "EDE0D4", "4B2E2B", "A27B5C", "DCD7C9")),
        Palette("Flowers", hex("FF1744", "FF4081", "F50057", "D500F9", "651FFF", "FFC400", "FF9100", "FF3D00", "FFEA00", "C6FF00")),
        Palette("Sky", hex("E3F2FD", "BBDEFB", "90CAF9", "64B5F6", "42A5F5", "2196F3", "1E88E5", "1976D2", "1565C0", "0D47A1")),
        Palette("Nature", hex("8BC34A", "689F38", "33691E", "795548", "4E342E", "03A9F4", "0288D1", "FFC107", "FF9800", "F5F5DC")),
    )

    /** Palettes used by colour-by-numbers; the first colour is for the biggest (background) area. */
    fun numbersPalette(category: String): IntArray = when (category) {
        "Nature" -> hex("CDEBFF", "6DBB4A", "3E8E2F", "FFD23F", "FF7A59", "F45B69", "8C5A3C", "B8E0FF", "FFB6E0", "9AD5CA", "E8D8A0", "5C4033", "F9F871", "A1C181", "FFA6C9", "72B5E8")
        "Space" -> hex("1B2451", "4B3F9C", "8A62D9", "F9D65C", "FF8C42", "E8E8F0", "5BC0EB", "C84B8F", "2E9E6B", "F45B69", "9BE564", "7A6F9B", "FFE8A3", "3A86FF", "FB5607", "C5C5D9")
        "Mandalas", "Patterns" -> hex("FFF6E5", "E63946", "F4A261", "E9C46A", "2A9D8F", "264653", "8338EC", "FF006E", "3A86FF", "FB5607", "06D6A0", "FFD166", "EF476F", "118AB2", "9B5DE5", "F15BB5")
        "Easy", "Food" -> hex("DFF3FF", "FF595E", "FFCA3A", "8AC926", "1982C4", "6A4C93", "FF924C", "F15BB5", "00BBF9", "FEE440", "9BF6FF", "FFADAD", "CAFFBF", "BDB2FF", "FDFFB6", "A0C4FF")
        "Animals" -> hex("E8F4F8", "F4A261", "E76F51", "2A9D8F", "E9C46A", "8D6E63", "FFB6B9", "5C6BC0", "81C784", "FFD54F", "4DB6AC", "BA68C8", "A1887F", "90CAF9", "F48FB1", "FFF176")
        "Anime", "Hero Academy" -> hex("DFF1FF", "FFE0BD", "5C3A21", "E63946", "1E4DB7", "FFD166", "2A9D8F", "F8BBD0", "8338EC", "FF924C", "3A86FF", "06D6A0", "FFFFFF", "9C27B0", "FDFFB6", "C77DFF")
        "Advanced" -> hex("FFF8E7", "E63946", "F4A261", "E9C46A", "2A9D8F", "264653", "8338EC", "FF006E", "3A86FF", "FB5607", "06D6A0", "FFD166", "EF476F", "118AB2", "9B5DE5", "F15BB5")
        else -> hex("F1F3F5", "E63946", "F4A261", "E9C46A", "2A9D8F", "457B9D", "8338EC", "FF006E", "3A86FF", "FB5607", "06D6A0", "FFD166", "EF476F", "118AB2", "9B5DE5", "A8DADC")
    }.toIntArray()

    /** Lighter (negative steps) or darker (positive steps) variants of a colour. */
    fun shade(color: Int, step: Int): Int {
        if (step == 0) return color
        val r = Color.red(color); val g = Color.green(color); val b = Color.blue(color)
        return if (step < 0) {
            val t = (-step) * 0.22f
            Color.argb(Color.alpha(color), (r + (255 - r) * t).toInt(), (g + (255 - g) * t).toInt(), (b + (255 - b) * t).toInt())
        } else {
            val t = 1f - step * 0.2f
            Color.argb(Color.alpha(color), (r * t).toInt(), (g * t).toInt(), (b * t).toInt())
        }
    }

    fun withOpacity(color: Int, opacity: Float): Int =
        (color and 0x00FFFFFF) or ((opacity.coerceIn(0f, 1f) * 255).toInt() shl 24)
}
