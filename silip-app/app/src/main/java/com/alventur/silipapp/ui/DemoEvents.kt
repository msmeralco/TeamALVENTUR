package com.alventur.silipapp.ui

import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/** Demo triggers sent from Settings (or anywhere) to the screen that shows them. */
sealed interface DemoEvent {
    /** Show the sample steady-load-while-away alert (Home opens SafetyAlertSheet). */
    data object ShowSafetyAlert : DemoEvent

    /** Start the sample grid event (Grid events screen). */
    data object StartGridEvent : DemoEvent
}

/**
 * One pending demo event, held by SilipApp and passed down. It is plain Compose state, so the
 * receiving screen reacts even if it was not on screen when the event was sent.
 *
 * Receiver pattern:
 * ```
 * val pending = demoEvents.pending
 * if (pending == DemoEvent.ShowSafetyAlert) { ...show sheet...; onDismiss = { demoEvents.consume(pending) } }
 * ```
 */
@Stable
class DemoEventBus {
    var pending: DemoEvent? by mutableStateOf(null)
        private set

    fun send(event: DemoEvent) {
        pending = event
    }

    /** Clears [event] if it is still the pending one. */
    fun consume(event: DemoEvent) {
        if (pending == event) pending = null
    }
}
