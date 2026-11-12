package com.alventur.silipapp.energy

import com.alventur.silipapp.data.remote.UsagePoint
import org.junit.Assert.*
import org.junit.Test
import java.time.ZoneId

class SolarProfileTest {
    private val manila = ZoneId.of("Asia/Manila")
    @Test fun separatesDaytimeUsingHouseholdLocalTime() {
        val points = listOf(
            UsagePoint("2026-11-12T00:45:00Z", 1.0), // 08:45 local, outside
            UsagePoint("2026-11-12T01:00:00Z", 2.0), // 09:00 local
            UsagePoint("2026-11-12T07:45:00Z", 2.0), // 15:45 local
            UsagePoint("2026-11-12T08:00:00Z", 3.0)  // 16:00 local, outside
        )
        val profile = SolarProfile.from(points, manila)!!
        assertEquals(1.0, profile.daytimeKwh, 0.0001)
        assertEquals(1.0, profile.otherKwh, 0.0001)
        assertEquals(0.5, profile.daytimeShare, 0.0001)
        assertEquals(2, profile.daytimeIntervals)
        assertEquals(1, profile.observedDays)
        assertEquals(0.5, profile.avoidedImportKwh(0.5), 0.0001)
        assertEquals(0.0, profile.avoidedImportKwh(0.0), 0.0001)
        assertEquals(1.0, profile.avoidedImportKwh(1.0), 0.0001)
    }
    @Test fun doesNotTurnEmptyOrInvalidReadingsIntoSolarPotential() {
        assertNull(SolarProfile.from(emptyList(), manila))
        assertNull(SolarProfile.from(listOf(UsagePoint("invalid", 3.0)), manila))
        val zero = SolarProfile.from(listOf(UsagePoint("2026-11-12T01:00:00Z", 0.0)), manila)!!
        assertEquals(0.0, zero.daytimeShare, 0.0)
        assertEquals(0.0, zero.avoidedImportKwh(1.0), 0.0)
    }
    @Test(expected = IllegalArgumentException::class)
    fun scenarioCannotExceedObservedDaytimeEnergy() {
        val profile = SolarProfile.from(listOf(UsagePoint("2026-11-12T01:00:00Z", 2.0)), manila)!!
        profile.avoidedImportKwh(1.1)
    }
}
