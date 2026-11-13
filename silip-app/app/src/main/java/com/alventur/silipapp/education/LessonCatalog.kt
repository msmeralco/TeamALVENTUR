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
            id = "phantom-loads",
            title = "Find standby power",
            description = "Spot what stays on.",
            estimatedMinutes = 2,
            points = 15
        ),
        Lesson(
            id = "cooling-wisely",
            title = "Cool your home",
            description = "Use your aircon wisely.",
            estimatedMinutes = 3,
            points = 20
        ),
        Lesson(
            id = "bill-basics",
            title = "Understand your bill",
            description = "See how use affects cost.",
            estimatedMinutes = 2,
            points = 15
        ),
        Lesson(
            id = "leaving-home",
            title = "Leaving home",
            description = "Switch off what you can.",
            estimatedMinutes = 1,
            points = 10
        )
    )
}
