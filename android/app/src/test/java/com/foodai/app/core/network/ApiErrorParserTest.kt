package com.foodai.app.core.network

import com.google.common.truth.Truth.assertThat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Test

class ApiErrorParserTest {
    @Test
    fun parsesUnauthorizedCode() {
        val body = """{"code":"invalid_credentials","message":"Неверный email или пароль"}"""
            .toResponseBody("application/json".toMediaType())
        val error = ApiErrorParser.fromHttp(401, body)
        assertThat(error).isInstanceOf(ApiException.Unauthorized::class.java)
        assertThat(error.code).isEqualTo("invalid_credentials")
        assertThat(error.message).contains("Неверный")
    }

    @Test
    fun parsesConflict() {
        val body = """{"code":"email_already_registered","message":"Email занят"}"""
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
