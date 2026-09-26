pluginManagement {
    repositories {
        maven(url = "https://maven-central.storage-download.googleapis.com/maven2")
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        maven(url = "https://maven-central.storage-download.googleapis.com/maven2")
        google()
        mavenCentral()
    }
}
rootProject.name = "Freilesen"
include(":app")
