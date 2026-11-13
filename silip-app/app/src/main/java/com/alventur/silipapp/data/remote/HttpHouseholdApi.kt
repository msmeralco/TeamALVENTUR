package com.alventur.silipapp.data.remote

import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class HouseholdApiException(
    val statusCode: Int,
    val detail: String
) : IOException(detail)

class HttpHouseholdApi(
    private val baseUrl: String = ApiConfig.baseUrl,
    private val connectTimeoutMs: Int = 10_000,
    private val readTimeoutMs: Int = 15_000
) : HouseholdApi {
    override suspend fun getDeviceUsage(clampId: String): DeviceUsage = withContext(Dispatchers.IO) {
        require(clampId.isNotBlank()) { "Enter a device ID." }
        val encodedId = Uri.encode(clampId.trim())
        val connection = URL(
            "${baseUrl.trimEnd('/')}${HouseholdApiRoutes.demoDeviceUsage(encodedId)}"
        ).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = connectTimeoutMs
            connection.readTimeout = readTimeoutMs
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cache-Control", "no-cache")

            val status = connection.responseCode
            val responseStream = if (status in 200..299) connection.inputStream else connection.errorStream
            val responseBody = responseStream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                throw HouseholdApiException(status, responseBody.toApiDetail())
            }
            JSONObject(responseBody).toDeviceUsage()
        } finally {
            connection.disconnect()
        }
    }
}

private fun JSONObject.toDeviceUsage(): DeviceUsage = DeviceUsage(
    clampId = getString("clamp_id"),
    transformerId = getString("transformer_id"),
    lastSeenAt = nullableString("last_seen_at"),
    totalKwh = getDouble("total_kwh"),
    isSimulated = optBoolean("is_simulated", false),
    points = getJSONArray("points").toUsagePoints()
)

private fun JSONArray.toUsagePoints(): List<UsagePoint> = List(length()) { index ->
    val point = getJSONObject(index)
    UsagePoint(timestamp = point.getString("ts"), powerKw = point.getDouble("kw"))
}

private fun JSONObject.nullableString(key: String): String? =
    if (isNull(key)) null else optString(key).takeIf(String::isNotBlank)

private fun String.toApiDetail(): String = runCatching {
    JSONObject(this).optString("detail").takeIf(String::isNotBlank) ?: this
}.getOrDefault(this).ifBlank { "The device service returned an error." }
