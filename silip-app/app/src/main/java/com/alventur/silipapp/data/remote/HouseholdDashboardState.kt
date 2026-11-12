package com.alventur.silipapp.data.remote

sealed interface HouseholdDashboardState {
    data object Loading : HouseholdDashboardState
    data class NotFound(val clampId: String) : HouseholdDashboardState
    data class Loaded(val device: DeviceUsage) : HouseholdDashboardState
    data class Error(val message: String) : HouseholdDashboardState
}
