package com.alventur.silipapp.data.remote

data class DeviceUsage(
    val clampId: String,
    val transformerId: String,
    val lastSeenAt: String?,
    val totalKwh: Double,
    val isSimulated: Boolean,
    val points: List<UsagePoint>
)

data class UsagePoint(
    val timestamp: String,
    val powerKw: Double
)

/** Public PoC read endpoint for the allowlisted demo device. */
interface HouseholdApi {
    suspend fun getDeviceUsage(clampId: String): DeviceUsage
}

object HouseholdApiRoutes {
    fun demoDeviceUsage(clampId: String): String =
        "/mobile-api/v1/devices/$clampId/usage"
}
