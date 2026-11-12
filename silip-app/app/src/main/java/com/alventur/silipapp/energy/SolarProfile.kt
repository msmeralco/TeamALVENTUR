package com.alventur.silipapp.energy

import com.alventur.silipapp.data.remote.UsagePoint
import java.time.Instant
import java.time.ZoneId

/** A time-of-use summary, not an assessment of irradiance, roof suitability or PV output. */
data class SolarProfile(
    val daytimeKwh: Double,
    val otherKwh: Double,
    val daytimeIntervals: Int,
    val observedDays: Int,
    val first: Instant,
    val last: Instant
) {
    val daytimeShare: Double get() = if (daytimeKwh + otherKwh > 0) daytimeKwh / (daytimeKwh + otherKwh) else 0.0
    fun avoidedImportKwh(coverage: Double): Double {
        require(coverage.isFinite() && coverage in 0.0..1.0)
        return daytimeKwh * coverage
    }
    companion object {
        fun from(points: List<UsagePoint>, zone: ZoneId = ZoneId.systemDefault()): SolarProfile? {
            val data = EnergyAnalysis.samples(points)
            if (data.isEmpty()) return null
            val daylight = data.filter { it.at.atZone(zone).hour in 9..15 }
            val total = data.sumOf { it.kw * 0.25 }
            val day = daylight.sumOf { it.kw * 0.25 }
            return SolarProfile(day, (total - day).coerceAtLeast(0.0), daylight.size,
                daylight.map { it.at.atZone(zone).toLocalDate() }.distinct().size, data.first().at, data.last().at)
        }
    }
}
