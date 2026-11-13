package com.alventur.silipapp.education

import java.time.LocalDate

/**
 * Question pool for the daily 15-second quiz. One question per Manila day, rotating by date.
 *
 * Facts are general and well known (no statistics). Peso examples use round example rates and
 * say so; they are not the user's tariff. Keep explanations to one or two short sentences.
 */
internal object DailyQuizCatalog {
    private fun q(prompt: String, explanation: String, correct: String, vararg wrong: String): ChallengeQuestion {
        val answers = buildList {
            add(ChallengeAnswer("a", correct, true))
            wrong.forEachIndexed { i, text -> add(ChallengeAnswer("w$i", text, false)) }
        }
        return ChallengeQuestion(prompt = prompt, answers = answers, explanation = explanation)
    }

    /** Raw pool. Answer order is shuffled per day by [forDate], so "a" is not always first. */
    val pool: List<ChallengeQuestion> = listOf(
        q(
            "Which bulb gives the same light with less electricity?",
            "LED bulbs use much less power than incandescent bulbs for the same brightness.",
            "An LED bulb", "An incandescent bulb", "They use the same"
        ),
        q(
            "What does an inverter aircon do differently?",
            "It changes compressor speed to hold the temperature, instead of stopping and starting at full power.",
            "Adjusts its compressor speed", "Runs only at full power", "Cools without a compressor"
        ),
        q(
            "Why keep the fridge door closed?",
            "Cold air escapes each time the door opens, so the fridge works harder to cool down again.",
            "Cold air escapes when it is open", "It saves water", "The light uses most of the power"
        ),
        q(
            "Where is a good spot for the refrigerator?",
            "Heat around a fridge makes it work harder. Leave space behind it so air can move.",
            "Away from the stove and direct sun", "Right beside the stove", "Pressed flat against the wall"
        ),
        q(
            "Which usually uses less electricity per hour?",
            "A fan only moves air. An aircon runs a compressor to remove heat, which takes far more power.",
            "An electric fan", "An aircon", "They use the same"
        ),
        q(
            "What is \"peak demand\"?",
            "Peak demand is when many homes use power at once, often on hot evenings.",
            "When many homes use power at the same time", "The cheapest hour of the day", "When the meter is read"
        ),
        q(
            "A 2 kW aircon runs for 3 hours. How much energy is that?",
            "kW × hours = kWh. 2 kW × 3 h = 6 kWh.",
            "6 kWh", "5 kWh", "2 kWh"
        ),
        q(
            "You used 10 kWh. At an example rate of ₱12 per kWh, what is the estimate?",
            "kWh × rate = cost estimate. 10 × ₱12 = ₱120. Your own bill shows your real rate.",
            "₱120", "₱22", "₱1,200"
        ),
        q(
            "The energy label on a new aircon or fridge helps you...",
            "The label lets you compare how efficient models are before you buy.",
            "Compare how efficient models are", "Check the warranty", "Find the store price"
        ),
        q(
            "Rice is cooked. The rice cooker stays on \"warm\" for hours. Does it use power?",
            "Keep-warm still heats the pot, so it keeps using electricity. Switch it off when you can.",
            "Yes, keep-warm still uses power", "No, warm mode is free", "Only when the lid is open"
        ),
        q(
            "Which laundry habit saves energy?",
            "Full loads mean fewer runs of the motor and pump for the same clothes.",
            "Wash full loads, fewer times", "Wash one shirt at a time", "Run the dryer cycle twice"
        ),
        q(
            "Why iron clothes in one batch?",
            "A flat iron uses a lot of power to heat up. One session avoids heating it again and again.",
            "It avoids reheating the iron", "Irons work better when cold", "It makes clothes dry faster"
        ),
        q(
            "Raising the aircon setting a little, if it's still comfortable, usually...",
            "A slightly warmer setting means the compressor runs less to hold the room there.",
            "Lowers energy use", "Raises energy use", "Has no effect"
        ),
        q(
            "An electric shower heater is...",
            "Water heaters are high-power appliances. Shorter showers use less energy.",
            "A high-power appliance", "A low-power appliance", "Powered by water pressure"
        ),
        q(
            "It's a bright morning. What's a simple saving?",
            "Daylight is free. Open curtains on cooler mornings and switch off lights you don't need.",
            "Use daylight and switch off lights", "Turn on every light", "Close all curtains and use lamps"
        ),
        q(
            "What does the SILIP clamp measure?",
            "It measures the whole home's current. It can't tell which appliance is on.",
            "The whole home's power use", "Each appliance separately", "The heat in each room"
        ),
        q(
            "An aircon and a flat iron on one extension cord. Is that okay?",
            "Two high-power appliances can overload a cord and make it hot. Use a proper wall outlet.",
            "No, it can overload the cord", "Yes, cords have no limit", "Only if the cord is long"
        ),
        q(
            "Why might your street be asked to cut load at 8 PM on a hot night?",
            "Homes on a street share one transformer. Many aircons at once can push it near its limit.",
            "The shared transformer is near its limit", "The meters need a reset", "Power is free at 8 PM"
        ),
        q(
            "Where can you find how much power an appliance draws?",
            "The rating label or the manual lists its power in watts (W).",
            "On its rating label or manual", "On the plug color", "On the power strip"
        ),
        q(
            "Two appliances run for 1 hour: 100 W and 1,000 W. Which uses more energy?",
            "Same time, more watts, more energy. 1,000 W for 1 hour is 1 kWh. 100 W is 0.1 kWh.",
            "The 1,000 W appliance", "The 100 W appliance", "They use the same"
        )
    )

    /** Today's question, the same on a given Manila date. Answer order is stable for that date. */
    fun forDate(date: LocalDate): ChallengeQuestion {
        val day = date.toEpochDay()
        val base = pool[Math.floorMod(day, pool.size.toLong()).toInt()]
        val shift = Math.floorMod(day, base.answers.size.toLong()).toInt()
        val rotated = base.answers.drop(shift) + base.answers.take(shift)
        return base.copy(answers = rotated)
    }
}
