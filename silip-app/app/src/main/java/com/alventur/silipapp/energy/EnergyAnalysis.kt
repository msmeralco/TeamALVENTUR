package com.alventur.silipapp.energy

import com.alventur.silipapp.data.remote.DeviceUsage
import com.alventur.silipapp.data.remote.UsagePoint
import java.time.Duration
import java.time.Instant
import java.time.ZoneId
import kotlin.math.*

object MeralcoRate {
    const val PHP_PER_KWH = 15.0615
    const val MONTH = "October 2026"
    const val SOURCE = "https://www.meralco.com.ph/uploads/documents/source-delta/2026-10-25/5afca4c86acee54e324a937c7481894500ae62aa0a92140d65f6a0e6ea943f79.pdf?v=1793354026"
    fun cost(kwh: Double, rate: Double = PHP_PER_KWH): Double {
        require(kwh.isFinite() && kwh >= 0 && rate.isFinite() && rate > 0)
        return kwh * rate
    }
}

data class EnergySample(val at: Instant, val kw: Double)
data class DemandForecast(
    val points: List<EnergySample>, val model: String, val validationMaeKw: Double,
    val baselineMaeKw: Double, val coverage: Double
) {
    val kwh: Double get() = points.sumOf { it.kw * 0.25 }
    val busiestHour: List<EnergySample> get() = points.chunked(4).maxBy { hour -> hour.sumOf { it.kw } }
}

object EnergyAnalysis {
    fun samples(points: List<UsagePoint>): List<EnergySample> = points.mapNotNull { p ->
        runCatching {
            require(p.powerKw.isFinite() && p.powerKw >= 0)
            EnergySample(Instant.parse(p.timestamp), p.powerKw)
        }.getOrNull()
    }.groupBy { Math.floorDiv(it.at.epochSecond, 900) * 900 }
        .map { (ts, group) -> EnergySample(Instant.ofEpochSecond(ts), group.map { it.kw }.average()) }
        .sortedBy { it.at }

    fun isFresh(at: Instant, now: Instant): Boolean = Duration.between(at, now).seconds in 0..1800

    /** Fourier daily regression + weekend and trend; last 24h is held out before final fitting. */
    fun forecast(points: List<UsagePoint>, zone: ZoneId = ZoneId.systemDefault()): DemandForecast? {
        val data = samples(points)
        if (data.size < 480) return null
        val start = data.first().at
        val end = data.last().at
        val slots = Duration.between(start, end).seconds / 900 + 1
        val coverage = data.size.toDouble() / slots
        if (slots < 480 || coverage < 0.8 || slots > 8 * 96) return null
        val split = end.minusSeconds(24 * 3600)
        val train = data.filter { it.at <= split }
        val valid = data.filter { it.at > split }
        if (train.size < 4 * 96 || valid.size < 77) return null
        val index = data.associateBy { it.at }
        fun features(at: Instant): DoubleArray {
            val local = at.atZone(zone)
            val phase = (local.hour + local.minute / 60.0) / 24.0 * 2 * PI
            return doubleArrayOf(1.0, Duration.between(start, at).seconds / 604800.0,
                sin(phase), cos(phase), sin(2 * phase), cos(2 * phase), sin(3 * phase), cos(3 * phase),
                if (local.dayOfWeek.value >= 6) 1.0 else 0.0)
        }
        fun fit(rows: List<EnergySample>): DoubleArray {
            val n = 9
            val matrix = Array(n) { DoubleArray(n + 1) }
            rows.forEach { row ->
                val x = features(row.at)
                for (i in 0 until n) {
                    for (j in 0 until n) matrix[i][j] += x[i] * x[j]
                    matrix[i][n] += x[i] * row.kw
                }
            }
            for (i in 1 until n) matrix[i][i] += 0.5
            for (i in 0 until n) {
                val pivot = (i until n).maxBy { abs(matrix[it][i]) }
                val swap = matrix[i]; matrix[i] = matrix[pivot]; matrix[pivot] = swap
                val divisor = matrix[i][i]
                if (abs(divisor) < 1e-10) return DoubleArray(n)
                for (j in i..n) matrix[i][j] /= divisor
                for (r in 0 until n) if (r != i) {
                    val factor = matrix[r][i]
                    for (j in i..n) matrix[r][j] -= factor * matrix[i][j]
                }
            }
            return DoubleArray(n) { matrix[it][n] }
        }
        val cap = data.maxOf { it.kw } * 1.5
        fun predict(weights: DoubleArray, at: Instant) = features(at).zip(weights.toList()).sumOf { it.first * it.second }.coerceIn(0.0, cap)
        fun seasonal(at: Instant, rows: List<EnergySample>): Double {
            val atLocal = at.atZone(zone)
            // Repeat the observed previous local day; fall back to a matching hour, never fill training gaps.
            val previous = atLocal.minusDays(1).toInstant()
            return index[previous]?.kw ?: rows.filter { it.at.atZone(zone).hour == atLocal.hour }
                .map { it.kw }.takeIf { it.isNotEmpty() }?.average() ?: rows.map { it.kw }.average()
        }
        val heldOutFit = fit(train)
        val regressionMae = valid.map { abs(predict(heldOutFit, it.at) - it.kw) }.average()
        val baselineMae = valid.map { abs(seasonal(it.at, train) - it.kw) }.average()
        val regressionWins = regressionMae <= baselineMae
        val finalFit = fit(data)
        val future = (1..96).map { step ->
            val at = end.plusSeconds(step * 900L)
            EnergySample(at, if (regressionWins) predict(finalFit, at) else seasonal(at, data))
        }
        return DemandForecast(future, if (regressionWins) "Daily-pattern regression" else "Previous-day pattern",
            if (regressionWins) regressionMae else baselineMae, baselineMae, coverage)
    }

    /** Two consecutive post-departure quarter hours; excludes stale, mixed/demo and pre-exit data. */
    fun awayDemand(device: DeviceUsage, departed: Instant, thresholdKw: Double, now: Instant): Double? {
        if (device.isSimulated || !thresholdKw.isFinite() || thresholdKw <= 0) return null
        val seen = device.lastSeenAt?.let { runCatching { Instant.parse(it) }.getOrNull() } ?: return null
        if (!isFresh(seen, now)) return null
        val samples = samples(device.points)
        val newest = samples.lastOrNull() ?: return null
        if (newest.at > now || newest.kw < thresholdKw) return null
        val last = samples.filter { it.at.plusSeconds(900) <= now }.takeLast(2)
        if (last.size != 2 || !isFresh(last.last().at, now)) return null
        if (last.first().at < departed || last.last().at > now) return null
        if (Duration.between(last.first().at, last.last().at).seconds != 900L) return null
        if (last.any { it.kw < thresholdKw }) return null
        return last.map { it.kw }.average()
    }
}
