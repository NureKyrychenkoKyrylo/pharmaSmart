package com.example.pharmasmart.network

import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface PharmaSmartApi {
    @FormUrlEncoded
    @POST("auth/login")
    suspend fun login(
        @Field("username") username: String,
        @Field("password") password: String,
    ): LoginResponse

    @GET("admin/dashboard-stats")
    suspend fun getDashboardStats(
        @Header("Authorization") authorization: String,
    ): DashboardStatsDto

    @GET("iot/alerts")
    suspend fun getAlerts(
        @Header("Authorization") authorization: String,
    ): List<ActiveAlertDto>

    @GET("pharmacies/")
    suspend fun getPharmacies(
        @Header("Authorization") authorization: String,
    ): List<PharmacyDto>
}
