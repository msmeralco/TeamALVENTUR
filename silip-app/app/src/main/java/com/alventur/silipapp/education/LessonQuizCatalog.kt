package com.alventur.silipapp.education

internal data class ChallengeAnswer(
    val id: String,
    val text: String,
    val correct: Boolean
)

internal data class ChallengeQuestion(
    val prompt: String,
    val answers: List<ChallengeAnswer>,
    val explanation: String
)

internal object LessonQuizCatalog {
    private val quizzes = mapOf(
        "phantom-loads" to listOf(
            ChallengeQuestion(
                prompt = "TV off. Standby light on. What does it mean?",
                answers = listOf(
                    ChallengeAnswer("standby-draw", "It may still draw power.", true),
                    ChallengeAnswer("full-power", "It uses as much power as when on.", false),
                    ChallengeAnswer("zero-draw", "It uses no power while off.", false)
                ),
                explanation = "Standby lights can signal power use. Switch devices off safely when not needed."
            ),
            ChallengeQuestion(
                prompt = "You rarely use a game console. What can help reduce standby use?",
                answers = listOf(
                    ChallengeAnswer("leave-console", "Leave it in standby all week.", false),
                    ChallengeAnswer("power-strip", "Switch it off at the power strip when safe.", true),
                    ChallengeAnswer("unplug-fridge", "Unplug the refrigerator instead.", false)
                ),
                explanation = "A switched-off power strip can cut standby power for grouped devices. Keep essential appliances on."
            ),
            ChallengeQuestion(
                prompt = "Which appliance should usually stay plugged in while you are away?",
                answers = listOf(
                    ChallengeAnswer("fan", "A fan in an empty room.", false),
                    ChallengeAnswer("tv", "A TV nobody is watching.", false),
                    ChallengeAnswer("refrigerator", "The refrigerator.", true)
                ),
                explanation = "The refrigerator needs power to keep food safely cold. Switch off nonessential devices instead."
            ),
            ChallengeQuestion(
                prompt = "Your phone is fully charged. What is a good next step?",
                answers = listOf(
                    ChallengeAnswer("unplug-charger", "Unplug the charger when it is safe.", true),
                    ChallengeAnswer("leave-charger", "Leave the charger plugged in all day.", false),
                    ChallengeAnswer("charge-again", "Keep charging it overnight every day.", false)
                ),
                explanation = "Unplugging chargers when they are not in use avoids unnecessary standby draw."
            ),
            ChallengeQuestion(
                prompt = "Why pay attention to small standby loads?",
                answers = listOf(
                    ChallengeAnswer("one-device", "One device always uses more than an aircon.", false),
                    ChallengeAnswer("add-up", "Many small loads can add up over time.", true),
                    ChallengeAnswer("no-cost", "Standby use is always free.", false)
                ),
                explanation = "A single standby load may be small, but several devices running all day can add up."
            )
        ),
        "cooling-wisely" to listOf(
            ChallengeQuestion(
                prompt = "Which aircon habit saves energy?",
                answers = listOf(
                    ChallengeAnswer("steady-setting", "Choose a comfortable setting and close doors.", true),
                    ChallengeAnswer("coldest-setting", "Set the coldest temperature every time.", false),
                    ChallengeAnswer("open-windows", "Keep windows open while it runs.", false)
                ),
                explanation = "A comfortable setting and closed doors help your aircon work efficiently."
            ),
            ChallengeQuestion(
                prompt = "The afternoon sun heats your room. What can help?",
                answers = listOf(
                    ChallengeAnswer("more-heat", "Open curtains to let more sun in.", false),
                    ChallengeAnswer("close-curtains", "Close curtains or blinds during the hottest hours.", true),
                    ChallengeAnswer("colder-aircon", "Set the aircon to its coldest setting.", false)
                ),
                explanation = "Shading sunny windows can reduce heat entering the room."
            ),
            ChallengeQuestion(
                prompt = "Your aircon airflow feels weak. What should you do?",
                answers = listOf(
                    ChallengeAnswer("block-filter", "Cover the air intake.", false),
                    ChallengeAnswer("ignore-filter", "Ignore the filter until next year.", false),
                    ChallengeAnswer("clean-filter", "Clean the filter as the manual recommends.", true)
                ),
                explanation = "A clean filter supports airflow. Follow the appliance manual for safe cleaning."
            ),
            ChallengeQuestion(
                prompt = "The aircon is on. What should you do with the windows?",
                answers = listOf(
                    ChallengeAnswer("close-windows", "Keep windows and doors closed.", true),
                    ChallengeAnswer("open-window", "Leave a window open for fresh air.", false),
                    ChallengeAnswer("fan-window", "Point a fan out the open window.", false)
                ),
                explanation = "Closed windows and doors help keep cooled air inside."
            ),
            ChallengeQuestion(
                prompt = "What is a sensible aircon temperature habit?",
                answers = listOf(
                    ChallengeAnswer("lowest", "Always choose the lowest temperature.", false),
                    ChallengeAnswer("comfortable", "Choose a comfortable setting for the people in the room.", true),
                    ChallengeAnswer("change-often", "Change the setting every few minutes.", false)
                ),
                explanation = "A comfortable, steady setting helps avoid unnecessary cooling."
            )
        ),
        "bill-basics" to listOf(
            ChallengeQuestion(
                prompt = "What does kWh tell you?",
                answers = listOf(
                    ChallengeAnswer("energy-used", "How much energy you used.", true),
                    ChallengeAnswer("peso-cost", "Exactly how much it costs in pesos.", false),
                    ChallengeAnswer("current-flow", "How fast current flows.", false)
                ),
                explanation = "A kWh measures energy use. Your rate helps turn that use into a bill estimate."
            ),
            ChallengeQuestion(
                prompt = "What do you need to estimate the peso cost of your electricity use?",
                answers = listOf(
                    ChallengeAnswer("appliance-color", "The color of your appliances.", false),
                    ChallengeAnswer("usage-rate", "Your kWh use and the applicable rate.", true),
                    ChallengeAnswer("house-age", "The age of your house only.", false)
                ),
                explanation = "Multiply energy use by the applicable rate for a simple cost estimate."
            ),
            ChallengeQuestion(
                prompt = "Your bill is higher than last month. What is a useful first check?",
                answers = listOf(
                    ChallengeAnswer("ignore-bill", "Ignore it; bills change at random.", false),
                    ChallengeAnswer("buy-device", "Replace every appliance immediately.", false),
                    ChallengeAnswer("compare-kwh", "Compare kWh use and billing-period days.", true)
                ),
                explanation = "Comparing kWh and the number of billing days helps explain changes in total cost."
            ),
            ChallengeQuestion(
                prompt = "Which appliance use is more likely to raise energy use?",
                answers = listOf(
                    ChallengeAnswer("high-use", "A high-power appliance running for many hours.", true),
                    ChallengeAnswer("short-light", "A small light on for a few minutes.", false),
                    ChallengeAnswer("unplugged", "An appliance that is unplugged.", false)
                ),
                explanation = "Energy use depends on both an appliance’s power and how long it runs."
            ),
            ChallengeQuestion(
                prompt = "A 1,000-watt appliance runs for 2 hours. About how much energy is that?",
                answers = listOf(
                    ChallengeAnswer("one-kwh", "1 kWh.", false),
                    ChallengeAnswer("two-kwh", "2 kWh.", true),
                    ChallengeAnswer("two-hundred", "200 kWh.", false)
                ),
                explanation = "1,000 watts is 1 kilowatt. One kilowatt running for 2 hours uses 2 kWh."
            )
        ),
        "leaving-home" to listOf(
            ChallengeQuestion(
                prompt = "Before leaving home, what should you switch off?",
                answers = listOf(
                    ChallengeAnswer("nonessential", "Nonessential appliances; keep the fridge on.", true),
                    ChallengeAnswer("everything", "Everything, including the fridge.", false),
                    ChallengeAnswer("standby", "Nothing; leave devices on standby.", false)
                ),
                explanation = "Switch off nonessential appliances. Keep essential devices like the refrigerator powered."
            ),
            ChallengeQuestion(
                prompt = "You finished using a flat iron. What should you do?",
                answers = listOf(
                    ChallengeAnswer("leave-iron", "Leave it on for the next person.", false),
                    ChallengeAnswer("iron-off", "Switch it off and unplug it when safe.", true),
                    ChallengeAnswer("cover-iron", "Cover it while it is still hot.", false)
                ),
                explanation = "Turn off heating appliances after use. Let them cool in a safe place before storing."
            ),
            ChallengeQuestion(
                prompt = "You leave a room for the day. What is a simple energy-saving step?",
                answers = listOf(
                    ChallengeAnswer("leave-lights", "Leave every light on.", false),
                    ChallengeAnswer("remove-bulb", "Remove the light bulb.", false),
                    ChallengeAnswer("switch-lights", "Turn off lights that are not needed.", true)
                ),
                explanation = "Turning off unneeded lights is a simple way to reduce electricity use."
            ),
            ChallengeQuestion(
                prompt = "An outlet feels hot or smells like burning. What should you do?",
                answers = listOf(
                    ChallengeAnswer("touch-outlet", "Touch it to check how hot it is.", false),
                    ChallengeAnswer("get-help", "Stay clear and tell an adult or qualified electrician.", true),
                    ChallengeAnswer("plug-more", "Plug in another device to test it.", false)
                ),
                explanation = "Do not touch a hot or damaged outlet. Keep away and get help from a responsible adult or qualified electrician."
            ),
            ChallengeQuestion(
                prompt = "Before a trip, what is a safe way to manage appliances?",
                answers = listOf(
                    ChallengeAnswer("checklist", "Switch off nonessential devices; keep essential ones on.", true),
                    ChallengeAnswer("all-off", "Turn off every appliance, including the refrigerator.", false),
                    ChallengeAnswer("leave-on", "Leave everything running as usual.", false)
                ),
                explanation = "Check each appliance. Turn off what is not needed and keep essential appliances operating."
            )
        )
    )

    fun questionsFor(lessonId: String): List<ChallengeQuestion> =
        quizzes[lessonId] ?: quizzes.getValue("phantom-loads")
}
