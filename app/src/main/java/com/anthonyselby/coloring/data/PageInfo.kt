package com.anthonyselby.coloring.data

enum class ColoringMode { FREE, NUMBERS }

data class PageInfo(
    val id: String,
    val title: String,
    val category: String,
    val difficulty: Int,
    val tags: String,
    val imported: Boolean = false,
    val createdAt: Long = 0L,
) {
    fun matches(query: String): Boolean {
        if (query.isBlank()) return true
        val q = query.trim().lowercase()
        return title.lowercase().contains(q) || category.lowercase().contains(q) || tags.lowercase().contains(q)
    }
}
