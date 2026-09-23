package com.foodai.app.core.network

import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

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
    suspend fun me(): CurrentUserDto

    @POST("auth/verify-email")
    suspend fun verifyEmail(@Body body: TokenMessageRequest): GenericMessageDto

    @POST("auth/resend-verification")
    suspend fun resendVerification(@Body body: EmailOnlyRequest): GenericMessageDto

    @POST("auth/forgot-password")
    suspend fun forgotPassword(@Body body: EmailOnlyRequest): GenericMessageDto

    @POST("auth/reset-password")
    suspend fun resetPassword(@Body body: ResetPasswordRequest): GenericMessageDto

    @GET("users/me/sessions")
    suspend fun listSessions(): List<SessionDto>

    @DELETE("users/me/sessions/{sessionId}")
    suspend fun revokeSession(@Path("sessionId") sessionId: String)

    @POST("users/me/sessions/revoke-all")
    suspend fun revokeAllSessions()

    @GET("users/me/export")
    suspend fun exportData(): kotlinx.serialization.json.JsonObject

    /**
     * Preferred: POST with confirmation body (DELETE bodies are unreliable on some stacks).
     * Returns [ResponseBody] so HTTP 204 empty responses are not parsed as JSON Unit.
     */
    @POST("users/me/delete")
    suspend fun deleteAccount(@Body body: DeleteAccountRequest): Response<ResponseBody>
}

interface AnalyticsApi {
    @POST("events")
    suspend fun postEvents(@Body body: AnalyticsBatchRequest): AnalyticsAcceptedDto
}

interface NutritionApi {
    @GET("nutrition/logs")
    suspend fun listLogs(@Query("date") date: String? = null): List<NutritionLogDto>

    @POST("nutrition/logs")
    suspend fun createLog(@Body body: NutritionLogCreateRequest): NutritionLogDto

    @DELETE("nutrition/logs/{id}")
    suspend fun deleteLog(@Path("id") id: String)
}
