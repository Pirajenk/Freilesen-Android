plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val freilesenApiBaseUrl = providers.gradleProperty("freilesenApiBaseUrl").orNull.orEmpty()

android {
    namespace = "de.freilesen.app"
    compileSdk = 36
    defaultConfig {
        applicationId = "de.freilesen.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8765\"")
        }
        release {
            // Keep project configuration and debug builds usable without a deployed backend.
            // A real HTTPS endpoint is supplied explicitly when a production release is built.
            val releaseApiBaseUrl = freilesenApiBaseUrl.ifBlank { "https://example.invalid" }
            buildConfigField("String", "API_BASE_URL", "\"${releaseApiBaseUrl.replace("\\", "\\\\").replace("\"", "\\\"")}\"")
        }
    }
}

tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_1_8)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation(platform("androidx.compose:compose-bom:2025.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
