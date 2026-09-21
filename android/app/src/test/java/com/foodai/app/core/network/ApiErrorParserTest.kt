package com.foodai.app.core.network

import com.google.common.truth.Truth.assertThat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Test

class ApiErrorParserTest {
    @Test
    fun unwrapsErrorEnvelope() {
        val body = """
            {"error":{"code":"invalid_credentials","message":"Неверный email или пароль.","request_id":"abc"}}
        """.trimIndent().toResponseBody("application/json".toMediaType())
        val error = ApiErrorParser.fromHttp(401, body)
        assertThat(error).isInstanceOf(ApiException.Unauthorized::class.java)
        assertThat(error.code).isEqualTo("invalid_credentials")
        assertThat(error.message).contains("Неверный")
    }

    @Test
    fun parsesNutritionDetails() {
        val body = """
            {"error":{"code":"nutrition_validation_error","message":"Цель небезопасна","details":[{"field":"target_weight_kg","reason":"must_be_below_current_weight"}]}}
        """.trimIndent().toResponseBody("application/json".toMediaType())
        val error = ApiErrorParser.fromHttp(422, body)
        assertThat(error).isInstanceOf(ApiException.Validation::class.java)
        assertThat(error.code).isEqualTo("nutrition_validation_error")
        assertThat(error.message).contains("target_weight_kg")
    }

    @Test
    fun parsesConflict() {
        val body = """{"error":{"code":"email_already_registered","message":"Email занят"}}"""
            .toResponseBody("application/json".toMediaType())
        val error = ApiErrorParser.fromHttp(409, body)
        assertThat(error).isInstanceOf(ApiException.Conflict::class.java)
        assertThat(error.code).isEqualTo("email_already_registered")
    }

    @Test
    fun fallsBackWhenBodyMissing() {
        val error = ApiErrorParser.fromHttp(500, null)
        assertThat(error).isInstanceOf(ApiException.Unexpected::class.java)
        assertThat(error.httpStatus).isEqualTo(500)
    }
}
