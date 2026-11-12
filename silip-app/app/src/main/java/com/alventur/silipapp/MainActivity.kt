package com.alventur.silipapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.alventur.silipapp.data.remote.HttpHouseholdApi
import com.alventur.silipapp.notifications.NotificationChannels
import com.alventur.silipapp.ui.SilipApp
import com.alventur.silipapp.ui.theme.SilipTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        NotificationChannels.create(this)

        setContent {
            SilipTheme {
                SilipApp(householdApi = HttpHouseholdApi())
            }
        }
    }
}
