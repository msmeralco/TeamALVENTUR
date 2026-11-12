package com.alventur.silipapp.energy

import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.data.remote.UsagePoint
import org.junit.Assert.*
import org.junit.Test
import java.time.Instant
import java.time.ZoneId
import kotlin.math.PI
import kotlin.math.sin

class EnergyAnalysisTest {
    private val start = Instant.parse("2026-11-01T00:00:00Z")
    private fun point(step: Int, kw: Double) = UsagePoint(start.plusSeconds(step * 900L).toString(), kw)
    private fun device(points: List<UsagePoint>, simulated: Boolean = false) = DeviceUsage(
        "test", "T-test", points.last().timestamp, points.sumOf { it.powerKw * 0.25 }, simulated, points)

    @Test fun meralcoBenchmarkAndHouseholdCost() {
        assertEquals(3012.30, MeralcoRate.cost(200.0), 0.001)
        assertEquals(1071.78, MeralcoRate.cost(71.16), 0.01)
    }
    @Test fun forecastRejectsSparseAndShortHistory() {
        assertNull(EnergyAnalysis.forecast((0..30).map { point(it, 0.5) }))
        assertNull(EnergyAnalysis.forecast((0..671).filter { it % 3 == 0 }.map { point(it, 0.5) }))
    }
    @Test fun learnsDailyPatternWithHeldOutErrorAndNonnegativeForecast() {
        val history = (0..671).map { point(it, 0.6 + 0.4 * sin(it * 2 * PI / 96)) }
        val result = EnergyAnalysis.forecast(history, ZoneId.of("UTC"))!!
        assertEquals(96, result.points.size)
        assertTrue(result.validationMaeKw < 0.01)
        assertTrue(result.points.all { it.kw.isFinite() && it.kw >= 0 })
        assertTrue(result.points.first().at > Instant.parse(history.last().timestamp))
        assertEquals(14.4, result.kwh, 0.05)
    }
    @Test fun regressionUsesHeldOutSelectionRatherThanClaimingBestFit() {
        val history = (0..671).map { point(it, if (it % 96 in 72..79) 2.0 else 0.1) }
        val result = EnergyAnalysis.forecast(history, ZoneId.of("UTC"))!!
        assertEquals("Previous-day pattern", result.model)
        assertEquals(0.0, result.baselineMaeKw, 0.0001)
    }
    @Test fun awayCheckRequiresFreshConsecutiveRealPostDepartureReadings() {
        val points = listOf(point(0, 0.8), point(1, 0.7))
        val now = start.plusSeconds(1800)
        val valid = device(points)
        assertEquals(0.75, EnergyAnalysis.awayDemand(valid, start, 0.3, now)!!, 0.001)
        assertNull(EnergyAnalysis.awayDemand(device(points, true), start, 0.3, now))
        assertNull(EnergyAnalysis.awayDemand(valid, start.plusSeconds(1), 0.3, now))
        assertNull(EnergyAnalysis.awayDemand(valid, start, 0.3, now.plusSeconds(3600)))
        assertNull(EnergyAnalysis.awayDemand(device(listOf(point(0, 0.8), point(2, 0.7))), start, 0.3, now))
        assertNull(EnergyAnalysis.awayDemand(device(listOf(point(0, 0.2), point(1, 0.7))), start, 0.3, now))
        assertNull(EnergyAnalysis.awayDemand(valid, start, 0.3, start.minusSeconds(1)))
        val switchedOff = device(listOf(point(0, 0.8), point(1, 0.7), point(2, 0.0)))
        assertNull(EnergyAnalysis.awayDemand(switchedOff, start, 0.3, now.plusSeconds(60)))
    }
    @Test fun invalidReadingsAreExcludedAndDuplicatesDoNotInflateUsage() {
        val data = EnergyAnalysis.samples(listOf(point(0, 1.0), point(0, 2.0), point(1, Double.NaN), point(2, -1.0)))
        assertEquals(1, data.size)
        assertEquals(1.5, data.single().kw, 0.001)
    }
}
