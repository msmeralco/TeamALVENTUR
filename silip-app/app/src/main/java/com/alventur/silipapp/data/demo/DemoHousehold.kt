package com.alventur.silipapp.data.demo

import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.data.remote.UsagePoint
import com.alventur.silipapp.energy.EnergySample
import com.alventur.silipapp.energy.MeralcoRate
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin

/*
 * DEMO DATA. Everything in this file is made up for the pitch story and the
 * "Explore the demo home (Rosa's)" mode. Any screen that shows it must carry a visible label:
 * [DemoLabels.SIMULATED] for readings, [DemoLabels.NEIGHBORHOOD] for the leaderboard,
 * [DemoLabels.PILOT] for grid events and rewards. No payment, consent or event service exists.
 */

/** Visible labels for demo content. Use these strings so the wording stays consistent. */
object DemoLabels {
    const val SIMULATED = "Simulated"
    const val NEIGHBORHOOD = "Demo neighborhood"
    const val PILOT = "Pilot preview"
}

/** Manila clock used for demo days and streaks. */
val ManilaZone: ZoneId = ZoneId.of("Asia/Manila")

/**
 * Estimated pesos per hour for a steady load: kW × 1 h × rate.
 * [rate] defaults to the dated Meralco residential benchmark in [MeralcoRate]; pass the user's
 * bill rate when known (see `selectedEnergyRate()` / `ProgressStore.ratePhpPerKwh()`).
 * Always label the result "estimate". Negative or invalid input returns 0.
 */
fun burnRatePhpPerHour(kw: Double, rate: Double = MeralcoRate.PHP_PER_KWH): Double {
    if (!kw.isFinite() || kw <= 0.0 || !rate.isFinite() || rate <= 0.0) return 0.0
    return MeralcoRate.cost(kw * 1.0, rate)
}

/**
 * Rosa's demo home: one day of whole-home power at 15-minute resolution (96 samples).
 *
 * Story beats (local Manila time):
 * - Background ≈ 0.30 kW (fridge, fans, router). Morning and evening bumps.
 * - 2:10 PM: the aircon turns on, a step of about +[AIRCON_STEP_KW] kW. Rosa leaves at 3:00 PM
 *   and switches the aircon off.
 * - 3:00 to 3:40 PM: away mode is on and a steady [AWAY_LOAD_KW] kW load stays on (the sample safety alert).
 * - 3:40 PM: the load stops (Rosa's neighbor checked; an iron had been left plugged in).
 * - 8 to 11 PM: aircon on again for the night.
 *
 * The clamp measures whole-home current only. Nothing here identifies an appliance; the
 * story names (aircon, iron) appear only as hedged suggestions in UI copy.
 */
object DemoHousehold {
    const val HOUSEHOLD_NAME = "Rosa's home"
    const val CLAMP_ID = "demo-rosa-home"
    const val TRANSFORMER_ID = "Demo street transformer"

    /**
     * Pitch numbers: Rosa's burn rate is ₱4.50/h before the aircon and ₱12.00/h after, at the dated
     * Meralco benchmark (₱15.0615/kWh). 4.50 / 15.0615 = 0.2988 kW; (12.00 − 4.50) / 15.0615 = 0.498 kW.
     */
    const val BACKGROUND_KW = 0.2988

    /** [VERIFY] Typical average draw of a 1-HP inverter aircon once it reaches its set point. */
    const val AIRCON_STEP_KW = 0.498
    const val AWAY_LOAD_KW = 1.1
    val AIRCON_ON: LocalTime = LocalTime.of(14, 10)
    val AWAY_START: LocalTime = LocalTime.of(15, 0)
    val AWAY_END: LocalTime = LocalTime.of(15, 40)

    /** Suggested "now" for the demo story: just after the aircon step. */
    val STORY_NOW: LocalTime = LocalTime.of(14, 20)

    /** Home's story beat: steady background just before the aircon step, in kW (₱4.50/h at the benchmark). */
    val storyKwBefore: Double get() = BACKGROUND_KW

    /** Home's story beat at [STORY_NOW]: background plus the aircon, in kW (₱12.00/h at the benchmark). */
    val storyKwNow: Double get() = BACKGROUND_KW + AIRCON_STEP_KW

    /** Estimated kWh Rosa used today up to [STORY_NOW]. */
    fun kwhUntilStoryNow(): Double =
        (0 until 96).map { LocalTime.of(it / 4, (it % 4) * 15) }
            .filter { it.isBefore(STORY_NOW) }
            .sumOf { kwAt(it) * 0.25 }

    /** Rosa's power at a time of day, in kW. Deterministic. */
    fun kwAt(time: LocalTime): Double {
        val h = time.hour + time.minute / 60.0
        var kw = BACKGROUND_KW
        // Gentle ripple so the line does not look ruled.
        kw += 0.03 * sin(h / 24.0 * 2 * PI * 5)
        // Breakfast 6 to 8 AM (rice cooker, kettle).
        if (h in 6.0..8.0) kw += 0.45 * bump(h, 7.0, 0.8)
        // Aircon afternoon block.
        if (!time.isBefore(AIRCON_ON) && time.isBefore(AWAY_START)) kw += AIRCON_STEP_KW
        // Away-mode steady load.
        if (!time.isBefore(AWAY_START) && time.isBefore(AWAY_END)) kw += AWAY_LOAD_KW
        // Dinner 5:30 to 7:30 PM.
        if (h in 17.5..19.5) kw += 0.55 * bump(h, 18.5, 0.9)
        // Night aircon 8 to 11 PM.
        if (h >= 20.0 && h < 23.0) kw += AIRCON_STEP_KW
        return max(0.05, kw)
    }

    /** 96 quarter-hour samples for [date] in Manila time. */
    fun day(date: LocalDate = LocalDate.now(ManilaZone)): List<EnergySample> =
        (0 until 96).map { slot ->
            val time = LocalTime.of(slot / 4, (slot % 4) * 15)
            EnergySample(date.atTime(time).atZone(ManilaZone).toInstant(), kwAt(time))
        }

    /**
     * The demo home as the API shape the Usage chart already reads: [days] days ending with
     * Rosa's story day (today in Manila). Earlier days are calmer copies with no away-mode load
     * and small day-to-day changes. `isSimulated = true`, so every existing label shows "Simulated".
     */
    fun deviceUsage(today: LocalDate = LocalDate.now(ManilaZone), days: Int = 7): DeviceUsage {
        val samples = (days - 1 downTo 0).flatMap { back ->
            val date = today.minusDays(back.toLong())
            if (back == 0) {
                day(date)
            } else {
                val factor = 0.88 + 0.06 * ((date.dayOfYear * 7) % 5)
                (0 until 96).map { slot ->
                    val time = LocalTime.of(slot / 4, (slot % 4) * 15)
                    val away = !time.isBefore(AWAY_START) && time.isBefore(AWAY_END)
                    val kw = kwAt(time) - if (away) AWAY_LOAD_KW else 0.0
                    EnergySample(date.atTime(time).atZone(ManilaZone).toInstant(), max(0.05, kw * factor))
                }
            }
        }
        val points = samples.map { UsagePoint(timestamp = it.at.toString(), powerKw = round3(it.kw)) }
        return DeviceUsage(
            clampId = CLAMP_ID,
            transformerId = TRANSFORMER_ID,
            lastSeenAt = samples.lastOrNull()?.at?.toString(),
            totalKwh = samples.sumOf { it.kw * 0.25 },
            isSimulated = true,
            points = points
        )
    }

    /** The sample safety alert shown by Settings → "Show a sample safety alert". */
    val safetyAlert = DemoSafetyAlert(
        id = "demo-away-steady-load",
        steadyKw = AWAY_LOAD_KW,
        minutes = 40,
        startedAt = AWAY_START,
        awayMode = true
    )

    /** The sample grid event (pilot preview). */
    val gridEvent = DemoGridEvent()

    /**
     * Weekly leaderboard for the demo neighborhood: 8 neighbors plus "You", ranked by weekly XP.
     * [yourWeeklyXp] and [yourKwhSaved] come from the user's real on-device progress.
     */
    fun leaderboard(yourWeeklyXp: Int, yourKwhSaved: Double = 0.0): List<LeaderboardEntry> {
        val neighbors = listOf(
            Triple("Aling Nena", 185, 6.4),
            Triple("Mang Jun", 160, 5.1),
            Triple("Tess", 140, 4.8),
            Triple("Kuya Ben", 120, 3.9),
            Triple("Lorna", 95, 3.2),
            Triple("Carlo", 70, 2.6),
            Triple("Joy", 45, 1.4),
            Triple("Aling Baby", 30, 0.9)
        ).mapIndexed { index, (name, xp, saved) ->
            LeaderboardEntry(name, xp, saved, isYou = false, previousRank = previousRanks[index])
        }
        // Where "You" sat last week: just below your current XP band, for a visible climb.
        val you = LeaderboardEntry("You", yourWeeklyXp, yourKwhSaved, isYou = true, previousRank = null)
        val ranked = (neighbors + you).sortedWith(
            compareByDescending<LeaderboardEntry> { it.weeklyXp }.thenBy { if (it.isYou) 0 else 1 }
        )
        return ranked.mapIndexed { index, entry ->
            val rank = index + 1
            entry.copy(
                rank = rank,
                previousRank = entry.previousRank ?: (rank + 2).coerceAtMost(ranked.size)
            )
        }
    }

    private val previousRanks = listOf(2, 1, 3, 5, 4, 6, 8, 7)

    private fun bump(h: Double, center: Double, width: Double): Double {
        val x = (h - center) / width
        return ((cos(x.coerceIn(-1.0, 1.0) * PI) + 1) / 2)
    }

    private fun round3(v: Double) = kotlin.math.round(v * 1000) / 1000
}

/**
 * Demo safety alert. Truthful wording only: the clamp sees a steady whole-home load,
 * not heat or a specific appliance. Use [message] as written.
 */
data class DemoSafetyAlert(
    val id: String,
    val steadyKw: Double,
    val minutes: Int,
    val startedAt: LocalTime,
    val awayMode: Boolean
) {
    val title: String get() = "Something is still on at home"
    val message: String
        get() = "A steady ${"%.1f".format(steadyKw)} kW load has been on for $minutes min while you're away " +
            "(away mode on). Did someone leave something plugged in, like an iron?"
    val limits: String
        get() = "SILIP measures whole-home power. It can't see heat or tell which appliance is on."
}

/** Neighborhood leaderboard row. [rank] is 1-based; [previousRank] is last week's position. */
data class LeaderboardEntry(
    val name: String,
    val weeklyXp: Int,
    val kwhSaved: Double,
    val isYou: Boolean,
    val previousRank: Int?,
    val rank: Int = 0
) {
    /** Positive = moved up. */
    val rankChange: Int get() = (previousRank ?: rank) - rank
}

/**
 * Demo grid event: the street transformer nears its rating on a hot April night.
 * Participation cools the transformer from [startLoadPercent] toward [targetLoadPercent].
 * Pilot preview: no event, consent or payout service exists.
 */
data class DemoGridEvent(
    val id: String = "demo-april-peak",
    val headline: String = "Grid Alert",
    val message: String = "Your street's transformer is near its limit tonight. " +
        "Reduce load 8–9 PM to earn ₱50 (pilot preview).",
    val start: LocalTime = LocalTime.of(20, 0),
    val end: LocalTime = LocalTime.of(21, 0),
    val rewardPhp: Int = 50,
    val targetHouseholds: Int = 60,
    /** Households already joined when the user opens the event. */
    val initialJoined: Int = 38,
    /** Households joined by the end of the story (Rosa plus 50 neighbors). */
    val finalJoined: Int = 51,
    val startLoadPercent: Double = 95.0,
    val targetLoadPercent: Double = 78.0,
    /** Suggested action and its approximate reduction. */
    val suggestedActions: List<Pair<String, Double>> = listOf(
        "Turn off one aircon" to DemoHousehold.AIRCON_STEP_KW,
        "Use a fan instead of the second aircon" to 1.0,
        "Run the washing machine after 9 PM" to 0.5
    )
) {
    /** Transformer load for a number of joined households, linear between start and target. */
    fun transformerLoadPercent(joined: Int): Double {
        val share = (joined.toDouble() / targetHouseholds).coerceIn(0.0, 1.0)
        return startLoadPercent - (startLoadPercent - targetLoadPercent) * share
    }

    /** Words for the gauge. Pair them with the color. */
    fun loadStatus(percent: Double): TransformerStatus = when {
        percent >= 90.0 -> TransformerStatus.NearLimit
        percent >= 85.0 -> TransformerStatus.Easing
        else -> TransformerStatus.Comfortable
    }

    val disclaimer: String
        get() = "Pilot preview. Demo data. No payout service is connected yet."
}

/** Transformer gauge states. [label] is the visible word paired with the gauge color. */
enum class TransformerStatus(val label: String) {
    NearLimit("Near its limit"),
    Easing("Cooling down"),
    Comfortable("Comfortable")
}
