package com.alventur.silipapp.data.remote

data class HouseholdUsage(
    val totalKwh: Double,
    val points: List<UsagePoint>,
    val isSimulated: Boolean
)

data class UsagePoint(
    val timestamp: String,
    val powerKw: Double,
    val isSimulated: Boolean
)

data class HouseholdDevice(
    val clampId: String,
    val transformerId: String,
    val lastSeenAt: String?,
    val isSimulated: Boolean
)

/** Authenticated household endpoints served by the SILIP API behind CloudFront. */
interface HouseholdApi {
    suspend fun getUsage(accessToken: String): HouseholdUsage

    suspend fun getDevice(accessToken: String): HouseholdDevice
}

object HouseholdApiRoutes {
    const val USAGE = "/api/v1/me/usage"
    const val DEVICE = "/api/v1/me/device"
}
