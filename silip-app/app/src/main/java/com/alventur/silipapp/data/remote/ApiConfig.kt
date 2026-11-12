package com.alventur.silipapp.data.remote

import com.alventur.silipapp.BuildConfig

object ApiConfig {
    val baseUrl: String
        get() = BuildConfig.API_BASE_URL.trimEnd('/')
}
