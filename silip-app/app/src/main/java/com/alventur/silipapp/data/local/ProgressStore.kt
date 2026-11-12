package com.alventur.silipapp.data.local

import android.content.Context
import android.content.SharedPreferences
import com.alventur.silipapp.data.demo.ManilaZone
import com.alventur.silipapp.energy.MeralcoRate
import java.time.Clock
import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.temporal.ChronoUnit
import java.time.temporal.TemporalAdjusters
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Household size chip choices. */
enum class HouseholdSize(val label: String) { OneToTwo("1–2"), ThreeToFour("3–4"), FivePlus("5+") }

/** Last-bill chip choices with a representative amount used to set the budget. */
enum class BillRange(val label: String, val representativePhp: Int) {
    Under1500("Under ₱1,500", 1_200),
    From1500To3000("₱1,500–3,000", 2_250),
    From3000To5000("₱3,000–5,000", 4_000),
    Over5000("Over ₱5,000", 6_000)
}

/**
 * Answers from onboarding. All optional; null means "not answered".
 * [aircons] is 0..3 where 3 means "3 or more".
 */
data class HouseholdProfile(
    val householdSize: HouseholdSize? = null,
    val aircons: Int? = null,
    val lastBill: BillRange? = null
) {
    /**
     * Monthly budget target: 10% below the last bill, rounded to ₱50. Null when no bill answer.
     * This is the user's goal, not a forecast.
     */
    val monthlyBudgetPhp: Int?
        get() = lastBill?.let { (Math.round(it.representativePhp * 0.9 / 50.0) * 50).toInt() }

    /** Monthly budget / 30, for "today's cost vs daily budget". */
    val dailyBudgetPhp: Double?
        get() = monthlyBudgetPhp?.let { it / 30.0 }

    companion object {
        /** Defaults used by "Skip": a 3–4 person home with one aircon and a ₱1,500–3,000 bill. */
        val SkipDefaults = HouseholdProfile(HouseholdSize.ThreeToFour, 1, BillRange.From1500To3000)
    }
}

/**
 * Date-based Eco-Streak in Asia/Manila.
 * [count] is the streak as of [lastActiveDate]; use [displayCount] for what to show today.
 */
data class StreakState(
    val count: Int = 0,
    val lastActiveDate: LocalDate? = null,
    val freezes: Int = 0
) {
    /** Today already counts toward the streak. */
    fun isLitToday(today: LocalDate): Boolean = lastActiveDate == today

    /**
     * The streak that is still alive today: the stored count if the user was active today or
     * yesterday, or if the missed days can be covered by freezes. Otherwise 0.
     */
    fun displayCount(today: LocalDate): Int {
        val last = lastActiveDate ?: return 0
        val gap = ChronoUnit.DAYS.between(last, today)
        return when {
            gap <= 1 -> count
            gap - 1 <= freezes -> count
            else -> 0
        }
    }
}

/** What happened to the streak after an activity. */
enum class StreakChange { AlreadyCountedToday, Started, Continued, SavedByFreeze, Restarted }

data class StreakUpdate(val change: StreakChange, val streak: StreakState, val freezesUsed: Int = 0)

/** How the user resolved a safety alert. */
enum class AlertResolution { CheckedAllGood, CalledSomeone, Snoozed }

data class AlertRecord(val id: String, val resolution: AlertResolution, val atEpochMillis: Long)

/**
 * A finished grid event (pilot preview). [reductionKw] is the estimated load cut for one hour,
 * so it is also the estimated kWh saved. [rewardPhp] is pending: no payout service exists.
 */
data class GridEventRecord(val eventId: String, val date: LocalDate, val reductionKw: Double, val rewardPhp: Int) {
    val kwhSaved: Double get() = reductionKw
}

/** Monday of [date]'s week. Weekly XP resets every Monday, Manila time. */
fun weekStartOf(date: LocalDate): LocalDate = date.with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY))

/** Immutable snapshot of everything SILIP stores on this phone for progress and setup. */
data class Progress(
    val onboarded: Boolean = false,
    val profile: HouseholdProfile = HouseholdProfile(),
    val usingDemoHome: Boolean = false,
    val xp: Int = 0,
    val completedLessons: Int = 0,
    val streak: StreakState = StreakState(),
    val quizDoneDate: LocalDate? = null,
    val badges: Set<String> = emptySet(),
    val alerts: Map<String, AlertRecord> = emptyMap(),
    /** XP earned in the week starting [weekStart]. Read it with [weeklyXp]. */
    val weekXp: Int = 0,
    val weekStart: LocalDate? = null,
    /** Finished grid events, newest first. */
    val gridEvents: List<GridEventRecord> = emptyList()
) {
    /** XP earned since Monday (Manila). 0 when the stored week is an older one. */
    fun weeklyXp(today: LocalDate = manilaToday()): Int = if (weekStart == weekStartOf(today)) weekXp else 0

    /** Estimated kWh saved in grid events this week. */
    fun weeklyKwhSaved(today: LocalDate = manilaToday()): Double {
        val monday = weekStartOf(today)
        return gridEvents.filter { !it.date.isBefore(monday) && !it.date.isAfter(today) }.sumOf { it.kwhSaved }
    }

    fun quizDoneToday(today: LocalDate = manilaToday()): Boolean = quizDoneDate == today

    /** Latest record for an alert, or null if never acted on. */
    fun alert(id: String): AlertRecord? = alerts[id]

    /** True if the alert is snoozed and the snooze has not ended. */
    fun isSnoozed(id: String, now: Instant = Instant.now()): Boolean =
        alerts[id]?.let { it.resolution == AlertResolution.Snoozed && it.atEpochMillis > now.toEpochMilli() } ?: false
}

/** Today's date in Asia/Manila. */
fun manilaToday(clock: Clock = Clock.systemUTC()): LocalDate = LocalDate.now(clock.withZone(ManilaZone))

/**
 * On-device progress and setup, in SharedPreferences (no account sync).
 *
 * Use the shared instance: `val store = ProgressStore.get(context)` and observe
 * `store.progress.collectAsState()` in Compose. Every write updates [progress] at once.
 *
 * Storage: the existing `silip_learning_preview` file, so Ale's lesson progress (`xp`,
 * `completed_lessons`, `streak_days`) carries over unchanged. Legacy `streak_days` without a date
 * is migrated once to a streak last active today. The bill rate stays in `silip_cost/rate`
 * (read by `selectedEnergyRate()`), and the device ID stays in `silip_demo_device/clamp_id`.
 */
class ProgressStore private constructor(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val costPrefs: SharedPreferences =
        context.getSharedPreferences("silip_cost", Context.MODE_PRIVATE)
    private val devicePrefs: SharedPreferences =
        context.getSharedPreferences("silip_demo_device", Context.MODE_PRIVATE)

    private val state = MutableStateFlow(Progress())

    /** Current progress. Collect it with `collectAsState()`. */
    val progress: StateFlow<Progress> = state.asStateFlow()

    init {
        migrate()
        state.value = read()
    }

    // region Onboarding and profile

    /**
     * Finishes onboarding. [deviceId] non-blank connects a real clamp (and turns demo home off);
     * otherwise [useDemoHome] decides whether Rosa's demo home is shown.
     */
    fun completeOnboarding(profile: HouseholdProfile, useDemoHome: Boolean, deviceId: String? = null) {
        val id = deviceId?.trim().orEmpty()
        if (id.isNotEmpty()) devicePrefs.edit().putString("clamp_id", id).apply()
        prefs.edit()
            .putBoolean(K_ONBOARDED, true)
            .putBoolean(K_DEMO_HOME, id.isEmpty() && useDemoHome)
            .apply()
        saveProfile(profile)
    }

    /** "Replay intro" in Settings. Keeps all progress. */
    fun replayOnboarding() {
        prefs.edit().putBoolean(K_ONBOARDED, false).apply()
        refresh()
    }

    fun saveProfile(profile: HouseholdProfile) {
        prefs.edit()
            .putString(K_SIZE, profile.householdSize?.name)
            .putInt(K_AIRCONS, profile.aircons ?: -1)
            .putString(K_BILL, profile.lastBill?.name)
            .apply()
        refresh()
    }

    fun setUsingDemoHome(enabled: Boolean) {
        prefs.edit().putBoolean(K_DEMO_HOME, enabled).apply()
        refresh()
    }

    /** Saved device ID (default: the allowlisted PoC device). */
    fun deviceId(): String = devicePrefs.getString("clamp_id", DEFAULT_DEVICE) ?: DEFAULT_DEVICE

    /** User's bill rate if saved, else the dated Meralco benchmark. Same source as `selectedEnergyRate()`. */
    fun ratePhpPerKwh(): Double =
        costPrefs.getString("rate", null)?.toDoubleOrNull()?.takeIf { it.isFinite() && it > 0 }
            ?: MeralcoRate.PHP_PER_KWH

    /** True when [ratePhpPerKwh] comes from the user's own bill. */
    fun hasOwnRate(): Boolean = costPrefs.contains("rate")

    // endregion

    // region XP, lessons, streak, quiz

    fun addXp(amount: Int) {
        if (amount == 0) return
        val next = (state.value.xp + amount).coerceAtLeast(0)
        prefs.edit().putInt(K_XP, next).putWeeklyXp(amount).apply()
        refresh()
    }

    /**
     * Records a finished lesson (0-based [lessonIndex]). XP is awarded once per lesson, as before.
     * Counts as today's streak activity.
     */
    fun completeLesson(lessonIndex: Int, points: Int): StreakUpdate {
        val current = state.value
        if (lessonIndex >= current.completedLessons) {
            prefs.edit()
                .putInt(K_LESSONS, lessonIndex + 1)
                .putInt(K_XP, current.xp + points)
                .putWeeklyXp(points)
                .apply()
        }
        return recordActivity()
    }

    /**
     * Marks today's quiz done, adds [xp] (once per day) and counts today for the streak.
     * Calling it again on the same day changes nothing and returns AlreadyCountedToday.
     */
    fun completeDailyQuiz(xp: Int, today: LocalDate = manilaToday()): StreakUpdate {
        if (state.value.quizDoneDate == today) {
            return StreakUpdate(StreakChange.AlreadyCountedToday, state.value.streak)
        }
        prefs.edit()
            .putString(K_QUIZ_DATE, today.toString())
            .putInt(K_XP, state.value.xp + xp)
            .putWeeklyXp(xp, today)
            .apply()
        return recordActivity(today)
    }

    /**
     * Counts [today] toward the Eco-Streak. Yesterday active → +1. Missed days covered by
     * freezes → freezes used, +1. Otherwise the streak restarts at 1.
     */
    fun recordActivity(today: LocalDate = manilaToday()): StreakUpdate {
        val streak = state.value.streak
        val last = streak.lastActiveDate
        if (last == today) return StreakUpdate(StreakChange.AlreadyCountedToday, streak)
        if (last == null || streak.count == 0) {
            val started = streak.copy(count = 1, lastActiveDate = today)
            writeStreak(started)
            return StreakUpdate(StreakChange.Started, started)
        }
        val gap: Long = ChronoUnit.DAYS.between(last, today)
        val (change, next, used) = when {
            gap == 1L -> Triple(StreakChange.Continued, streak.copy(count = streak.count + 1, lastActiveDate = today), 0)
            gap > 1L && gap - 1 <= streak.freezes -> {
                val missed = (gap - 1).toInt()
                Triple(
                    StreakChange.SavedByFreeze,
                    streak.copy(count = streak.count + 1, lastActiveDate = today, freezes = streak.freezes - missed),
                    missed
                )
            }
            // A clock moved backwards: keep the streak, move the date.
            gap < 1L -> Triple(StreakChange.AlreadyCountedToday, streak.copy(lastActiveDate = today), 0)
            else -> Triple(StreakChange.Restarted, streak.copy(count = 1, lastActiveDate = today), 0)
        }
        writeStreak(next)
        return StreakUpdate(change, next, used)
    }

    /** Adds streak freezes, up to [MAX_FREEZES]. Returns the new count. */
    fun addStreakFreeze(count: Int = 1): Int {
        val next = (state.value.streak.freezes + count).coerceIn(0, MAX_FREEZES)
        writeStreak(state.value.streak.copy(freezes = next))
        return next
    }

    // endregion

    // region Badges and alerts

    /** Adds a badge. Returns true if it is new. */
    fun earnBadge(id: String): Boolean {
        val current = state.value.badges
        if (id in current) return false
        prefs.edit().putStringSet(K_BADGES, HashSet(current + id)).apply()
        refresh()
        return true
    }

    /** Records how an alert was handled. */
    fun resolveAlert(id: String, resolution: AlertResolution, at: Instant = Instant.now()) {
        writeAlert(AlertRecord(id, resolution, at.toEpochMilli()))
    }

    /** "Remind me in 10 min": stores the time the reminder is due. */
    fun snoozeAlert(id: String, minutes: Long = 10, now: Instant = Instant.now()) {
        writeAlert(AlertRecord(id, AlertResolution.Snoozed, now.plusSeconds(minutes * 60).toEpochMilli()))
    }

    /** Forget an alert's record so the demo alert can be shown fresh. */
    fun clearAlert(id: String) {
        val kept = state.value.alerts.filterKeys { it != id }.values.map(::encodeAlert).toSet()
        prefs.edit().putStringSet(K_ALERTS, HashSet(kept)).apply()
        refresh()
    }

    /**
     * Saves a finished grid event (pilot preview). One record per event per day; a replay on the
     * same day replaces it. Returns true if this is the first record for that event and day.
     */
    fun recordGridEvent(eventId: String, reductionKw: Double, rewardPhp: Int, date: LocalDate = manilaToday()): Boolean {
        val record = GridEventRecord(eventId, date, reductionKw.coerceAtLeast(0.0), rewardPhp)
        val others = state.value.gridEvents.filterNot { it.eventId == eventId && it.date == date }
        val isNew = others.size == state.value.gridEvents.size
        prefs.edit().putStringSet(K_GRID_EVENTS, HashSet((others + record).map(::encodeGridEvent))).apply()
        refresh()
        return isNew
    }

    // endregion

    /** Adds [amount] to this week's XP, starting a new week on Monday (Manila). */
    private fun SharedPreferences.Editor.putWeeklyXp(amount: Int, today: LocalDate = manilaToday()): SharedPreferences.Editor {
        val monday = weekStartOf(today)
        val base = state.value.weeklyXp(today)
        return putString(K_WEEK_START, monday.toString()).putInt(K_WEEK_XP, (base + amount).coerceAtLeast(0))
    }

    private fun writeAlert(record: AlertRecord) {
        val others = state.value.alerts.filterKeys { it != record.id }.values.map(::encodeAlert)
        prefs.edit().putStringSet(K_ALERTS, HashSet(others + encodeAlert(record))).apply()
        refresh()
    }

    private fun writeStreak(streak: StreakState) {
        prefs.edit()
            .putInt(K_STREAK, streak.count)
            .putString(K_STREAK_DATE, streak.lastActiveDate?.toString())
            .putInt(K_FREEZES, streak.freezes)
            .apply()
        refresh()
    }

    private fun refresh() {
        state.value = read()
    }

    private fun read(): Progress = Progress(
        onboarded = prefs.getBoolean(K_ONBOARDED, false),
        profile = HouseholdProfile(
            householdSize = prefs.getString(K_SIZE, null)?.let { runCatching { HouseholdSize.valueOf(it) }.getOrNull() },
            aircons = prefs.getInt(K_AIRCONS, -1).takeIf { it >= 0 },
            lastBill = prefs.getString(K_BILL, null)?.let { runCatching { BillRange.valueOf(it) }.getOrNull() }
        ),
        usingDemoHome = prefs.getBoolean(K_DEMO_HOME, false),
        xp = prefs.getInt(K_XP, 0).coerceAtLeast(0),
        completedLessons = prefs.getInt(K_LESSONS, 0).coerceAtLeast(0),
        streak = StreakState(
            count = prefs.getInt(K_STREAK, 0).coerceAtLeast(0),
            lastActiveDate = prefs.getString(K_STREAK_DATE, null)?.let { runCatching { LocalDate.parse(it) }.getOrNull() },
            freezes = prefs.getInt(K_FREEZES, 0).coerceIn(0, MAX_FREEZES)
        ),
        quizDoneDate = prefs.getString(K_QUIZ_DATE, null)?.let { runCatching { LocalDate.parse(it) }.getOrNull() },
        badges = prefs.getStringSet(K_BADGES, emptySet())?.toSet() ?: emptySet(),
        alerts = (prefs.getStringSet(K_ALERTS, emptySet()) ?: emptySet())
            .mapNotNull(::decodeAlert)
            .associateBy { it.id },
        weekXp = prefs.getInt(K_WEEK_XP, 0).coerceAtLeast(0),
        weekStart = prefs.getString(K_WEEK_START, null)?.let { runCatching { LocalDate.parse(it) }.getOrNull() },
        gridEvents = (prefs.getStringSet(K_GRID_EVENTS, emptySet()) ?: emptySet())
            .mapNotNull(::decodeGridEvent)
            .sortedByDescending { it.date }
    )

    /** One-time upgrade from the preview's count-only streak. */
    private fun migrate() {
        if (prefs.getInt(K_SCHEMA, 0) >= SCHEMA) return
        val edit = prefs.edit()
        val legacyStreak = prefs.getInt(K_STREAK, 0)
        if (legacyStreak > 0 && !prefs.contains(K_STREAK_DATE)) {
            edit.putString(K_STREAK_DATE, manilaToday().toString())
        }
        edit.putInt(K_SCHEMA, SCHEMA).apply()
    }

    private fun encodeAlert(record: AlertRecord) = "${record.id}|${record.resolution.name}|${record.atEpochMillis}"

    private fun decodeAlert(raw: String): AlertRecord? {
        val parts = raw.split('|')
        if (parts.size != 3) return null
        val resolution = runCatching { AlertResolution.valueOf(parts[1]) }.getOrNull() ?: return null
        val at = parts[2].toLongOrNull() ?: return null
        return AlertRecord(parts[0], resolution, at)
    }

    private fun encodeGridEvent(r: GridEventRecord) = "${r.eventId}|${r.date}|${r.reductionKw}|${r.rewardPhp}"

    private fun decodeGridEvent(raw: String): GridEventRecord? {
        val parts = raw.split('|')
        if (parts.size != 4) return null
        val date = runCatching { LocalDate.parse(parts[1]) }.getOrNull() ?: return null
        val kw = parts[2].toDoubleOrNull()?.takeIf { it.isFinite() } ?: return null
        val php = parts[3].toIntOrNull() ?: return null
        return GridEventRecord(parts[0], date, kw, php)
    }

    companion object {
        const val DEFAULT_DEVICE = "silip-esp32-test"
        const val MAX_FREEZES = 2

        /** Badge IDs. Art: chest and trophy drawables in res/drawable-nodpi. */
        const val BADGE_FIRST_DAY = "first-day"
        const val BADGE_FIRST_QUIZ = "first-quiz"
        const val BADGE_WEEK_STREAK = "week-streak"
        const val BADGE_ALERT_CHECKED = "alert-checked"
        const val BADGE_GRID_HELPER = "grid-helper"

        private const val PREFS = "silip_learning_preview"
        private const val SCHEMA = 2
        private const val K_SCHEMA = "schema"
        private const val K_ONBOARDED = "onboarded"
        private const val K_DEMO_HOME = "demo_home"
        private const val K_SIZE = "profile_household_size"
        private const val K_AIRCONS = "profile_aircons"
        private const val K_BILL = "profile_last_bill"
        private const val K_XP = "xp" // legacy key, kept
        private const val K_LESSONS = "completed_lessons" // legacy key, kept
        private const val K_STREAK = "streak_days" // legacy key, now the date-based count
        private const val K_STREAK_DATE = "streak_last_day"
        private const val K_FREEZES = "streak_freezes"
        private const val K_QUIZ_DATE = "quiz_done_date"
        private const val K_BADGES = "badges"
        private const val K_ALERTS = "alert_records"
        private const val K_WEEK_XP = "week_xp"
        private const val K_WEEK_START = "week_start"
        private const val K_GRID_EVENTS = "grid_event_records"

        @Volatile
        private var instance: ProgressStore? = null

        /** Shared instance for the app process. */
        fun get(context: Context): ProgressStore =
            instance ?: synchronized(this) {
                instance ?: ProgressStore(context.applicationContext).also { instance = it }
            }
    }
}
