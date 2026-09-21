package com.foodai.app.core.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface AuthApi {
    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequest): TokenPairResponse

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): TokenPairResponse

    @POST("auth/refresh")
    suspend fun refresh(@Body body: RefreshRequest): TokenPairResponse

    @POST("auth/logout")
    suspend fun logout(@Body body: LogoutRequest)

    @GET("users/me")
    suspend fun me(): UserSummaryDto
}
