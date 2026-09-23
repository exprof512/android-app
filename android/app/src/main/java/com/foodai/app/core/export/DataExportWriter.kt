package com.foodai.app.core.export

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.core.content.FileProvider
import java.io.File
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

data class ExportFileResult(
    val uri: Uri,
    val displayName: String,
    val absolutePathHint: String?,
)

/**
 * Persists account export JSON to a real file (Downloads when possible),
 * then returns a shareable content Uri.
 */
object DataExportWriter {
    private val stampFormat =
        DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss").withZone(ZoneOffset.UTC)

    fun writeJson(context: Context, json: String): ExportFileResult {
        val stamp = stampFormat.format(Instant.now())
        val displayName = "foodai-export-$stamp.json"
        val bytes = json.toByteArray(Charsets.UTF_8)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, displayName)
                put(MediaStore.Downloads.MIME_TYPE, "application/json")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val collection = MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
            val uri = resolver.insert(collection, values)
                ?: error("Не удалось создать файл экспорта")
            resolver.openOutputStream(uri)?.use { stream ->
                stream.write(bytes)
                stream.flush()
            } ?: error("Не удалось записать файл экспорта")
            values.clear()
            values.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
            return ExportFileResult(
                uri = uri,
                displayName = displayName,
                absolutePathHint = "Downloads/$displayName",
            )
        }

        val dir = context.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS)
            ?: File(context.cacheDir, "exports").also { it.mkdirs() }
        if (!dir.exists()) dir.mkdirs()
        val file = File(dir, displayName)
        file.writeBytes(bytes)
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file,
        )
        return ExportFileResult(
            uri = uri,
            displayName = displayName,
            absolutePathHint = file.absolutePath,
        )
    }
}
