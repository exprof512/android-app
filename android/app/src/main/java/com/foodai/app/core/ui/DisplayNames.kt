package com.foodai.app.core.ui

/**
 * Strip legacy "(YYYY-MM-DD)" suffixes from recipe titles for display.
 * Identity on the backend is unchanged; this is presentation only.
 */
fun displayRecipeName(name: String): String {
    val stripped = name.replace(Regex("""\s*\(\d{4}-\d{2}-\d{2}\)\s*$"""), "").trim()
    return stripped.ifBlank { name }
}
