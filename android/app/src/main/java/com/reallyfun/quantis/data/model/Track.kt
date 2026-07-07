package com.reallyfun.quantis.data.model

enum class TrackSource(val value: String) {
    YANDEX("yandex"),
    YOUTUBE("youtube"),
    ;

    companion object {
        fun from(raw: String): TrackSource? =
            entries.firstOrNull { it.value.equals(raw, ignoreCase = true) }
    }
}

data class Track(
    val trackId: String,
    val title: String,
    val author: String,
    val source: TrackSource,
    val downloaded: Boolean = false,
) {
    val key: String get() = "${source.value}:$trackId"
}
