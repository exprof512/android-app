package com.foodai.app.di

import com.foodai.app.BuildConfig
import com.foodai.app.core.auth.SecureTokenStore
import com.foodai.app.core.auth.TokenStore
import com.foodai.app.core.network.AuthApi
import com.foodai.app.core.network.AuthApiProvider
import com.foodai.app.core.network.AuthInterceptor
import com.foodai.app.core.network.MealPlanApi
import com.foodai.app.core.network.ProfileApi
import com.foodai.app.core.network.TokenAuthenticator
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Named
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class AuthBindModule {
    @Binds
    @Singleton
    abstract fun bindTokenStore(impl: SecureTokenStore): TokenStore
}

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
    }

    @Provides
    @Singleton
    @Named("bare")
    fun provideBareOkHttp(): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BASIC
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
        return OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideOkHttp(
        authInterceptor: AuthInterceptor,
        tokenAuthenticator: TokenAuthenticator,
        @Named("bare") bare: OkHttpClient,
    ): OkHttpClient = bare.newBuilder()
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .addInterceptor(authInterceptor)
        .authenticator(tokenAuthenticator)
        .build()

    @Provides
    @Singleton
    @Named("bare")
    fun provideBareRetrofit(
        @Named("bare") client: OkHttpClient,
        json: Json,
    ): Retrofit = buildRetrofit(client, json)

    @Provides
    @Singleton
    fun provideRetrofit(
        client: OkHttpClient,
        json: Json,
    ): Retrofit = buildRetrofit(client, json)

    @Provides
    @Singleton
    @Named("bare")
    fun provideBareAuthApi(
        @Named("bare") bareRetrofit: Retrofit,
        authApiProvider: AuthApiProvider,
    ): AuthApi {
        val api = bareRetrofit.create(AuthApi::class.java)
        authApiProvider.authApi = api
        return api
    }

    @Provides
    @Singleton
    @Named("authed")
    fun provideAuthedAuthApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideProfileApi(retrofit: Retrofit): ProfileApi = retrofit.create(ProfileApi::class.java)

    @Provides
    @Singleton
    fun provideMealPlanApi(retrofit: Retrofit): MealPlanApi = retrofit.create(MealPlanApi::class.java)

    private fun buildRetrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
}
