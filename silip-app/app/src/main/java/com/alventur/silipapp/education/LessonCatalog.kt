package com.alventur.silipapp.education

data class Lesson(
    val id: String,
    val title: String,
    val description: String,
    val estimatedMinutes: Int,
    val points: Int
)

object LessonCatalog {
    val starterLessons = listOf(
        Lesson(
            id = "cooling-wisely",
            title = "Cool your home wisely",
            description = "Small air-conditioner habits that can lower energy use.",
            estimatedMinutes = 3,
            points = 20
        ),
        Lesson(
            id = "standby-power",
            title = "What can stay plugged in?",
            description = "Know what to switch off and what should keep running.",
            estimatedMinutes = 2,
            points = 15
        ),
        Lesson(
            id = "leaving-home",
            title = "Before you leave home",
            description = "A quick safety check for lights and non-essential appliances.",
            estimatedMinutes = 1,
            points = 10
        )
    )
}
