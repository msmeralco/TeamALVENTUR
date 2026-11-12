package com.alventur.silipapp.auth

/** Supplies the current Cognito access token to authenticated SILIP API requests. */
fun interface AccessTokenProvider {
    suspend fun accessToken(): String?
}
