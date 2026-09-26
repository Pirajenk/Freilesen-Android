package de.freilesen.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ArrowBack
import androidx.compose.material.icons.rounded.ArrowForward
import androidx.compose.material.icons.rounded.BookmarkBorder
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Link
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

private val Ink = Color(0xFF20231F)
private val Muted = Color(0xFF777B73)
private val Paper = Color(0xFFF7F7F4)
private val Green = Color(0xFF346653)
private val Line = Color(0xFFE6E7E1)

private data class Story(
    val source: String,
    val title: String,
    val detail: String,
    val url: String,
    val language: String,
    val published: String = "",
    val score: Int = 0
)

private data class SearchResponse(
    val metadataTitle: String,
    val metadataDescription: String,
    val metadataPublisher: String,
    val metadataPublished: String,
    val topics: String,
    val results: List<Story>,
    val message: String
)

private suspend fun findArticles(articleUrl: String): SearchResponse = withContext(Dispatchers.IO) {
    val endpoint = "http://10.0.2.2:8765/api/search?url=${Uri.encode(articleUrl)}"
    val connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
        requestMethod = "GET"
        connectTimeout = 12_000
        readTimeout = 45_000
    }
    try {
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        val json = JSONObject(body)
        if (!json.optBoolean("ok")) throw IllegalStateException(json.optString("error", "Die Suche ist fehlgeschlagen."))
        val meta = json.optJSONObject("metadata") ?: JSONObject()
        val items = json.optJSONArray("results")
        val results = buildList {
            if (items != null) for (i in 0 until items.length()) {
                val item = items.optJSONObject(i) ?: continue
                add(Story(
                    source = item.optString("source", "Freie Quelle"),
                    title = item.optString("title", "Artikel"),
                    detail = item.optString("description", ""),
                    url = item.optString("url", ""),
                    language = item.optString("lang", "de"),
                    published = item.optString("published", ""),
                    score = item.optInt("score", 0).coerceIn(0, 100)
                ))
            }
        }
        SearchResponse(
            metadataTitle = meta.optString("title", "Artikel"),
            metadataDescription = meta.optString("description", ""),
            metadataPublisher = meta.optString("publisher", ""),
            metadataPublished = meta.optString("published", ""),
            topics = (json.optJSONArray("topics")?.let { a -> (0 until a.length()).joinToString(" · ") { a.optString(it) } } ?: ""),
            results = results,
            message = json.optString("message", "")
        )
    } finally {
        connection.disconnect()
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { FreilesenApp() }
    }
}

@Composable
private fun FreilesenApp() {
    var url by remember { mutableStateOf("") }
    var searchGeneration by remember { mutableIntStateOf(0) }
    var selected by remember { mutableIntStateOf(-1) }
    var tab by remember { mutableStateOf("Entdecken") }
    var languageFilter by remember { mutableStateOf("all") }
    var searching by remember { mutableStateOf(false) }
    var results by remember { mutableStateOf(emptyList<Story>()) }
    var status by remember { mutableStateOf("Füge einen Artikel-Link ein, um passende Berichte zu finden.") }
    var metadataTitle by remember { mutableStateOf("") }
    var metadataDescription by remember { mutableStateOf("") }
    var metadataPublisher by remember { mutableStateOf("") }
    var metadataPublished by remember { mutableStateOf("") }
    var topics by remember { mutableStateOf("") }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    fun search() {
        if (url.isBlank()) {
            status = "Füge zuerst einen Artikellink ein."
            return
        }
        val generation = ++searchGeneration
        searching = true
        results = emptyList()
        status = "Metadaten werden gelesen und passende Artikel gesucht …"
        scope.launch {
            try {
                val response = findArticles(url.trim())
                if (generation != searchGeneration) return@launch
                metadataTitle = response.metadataTitle
                metadataDescription = response.metadataDescription
                metadataPublisher = response.metadataPublisher
                metadataPublished = response.metadataPublished
                topics = response.topics
                results = response.results
                status = response.message.ifBlank { if (results.isEmpty()) "Keine ausreichend ähnlichen Artikel gefunden." else "" }
            } catch (e: Exception) {
                if (generation != searchGeneration) return@launch
                status = e.message ?: "Suche nicht erreichbar. Starte den lokalen Vorschau-Server und versuche es erneut."
            } finally {
                if (generation == searchGeneration) searching = false
            }
        }
    }

    val visibleResults = when (languageFilter) {
        "de" -> results.filter { it.language == "de" }
        "en" -> results.filter { it.language == "en" }
        else -> results
    }

    MaterialTheme {
        Surface(Modifier.fillMaxSize(), color = Paper) {
            Column(Modifier.fillMaxSize()) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 18.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("f", fontSize = 28.sp, fontWeight = FontWeight.Bold, color = Green)
                    Spacer(Modifier.width(10.dp))
                    Text("freilesen", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = Ink)
                    Spacer(Modifier.weight(1f))
                    Text("DE  ·  EN", fontSize = 11.sp, letterSpacing = 1.sp, color = Muted)
                }
                HorizontalDivider(color = Line)
                if (selected >= 0 && selected < visibleResults.size) {
                    Reader(visibleResults[selected], onBack = { selected = -1 })
                } else {
                    Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 22.dp)) {
                        Spacer(Modifier.height(28.dp))
                        Text("GUT INFORMIERT.", fontSize = 10.sp, letterSpacing = 2.sp, color = Green, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Text("Lesen, was\nweiterführt.", fontSize = 34.sp, lineHeight = 39.sp, fontWeight = FontWeight.SemiBold, color = Ink)
                        Spacer(Modifier.height(10.dp))
                        Text("Gib einen Artikel-Link ein. Wir lesen Titel und Metadaten aus und suchen passende Perspektiven.", fontSize = 15.sp, lineHeight = 22.sp, color = Muted)
                        Spacer(Modifier.height(22.dp))
                        Row(Modifier.fillMaxWidth().background(Color.White, RoundedCornerShape(16.dp)).border(1.dp, Line, RoundedCornerShape(16.dp)).padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Rounded.Link, null, tint = Muted, modifier = Modifier.padding(horizontal = 9.dp))
                            BasicTextField(
                                value = url,
                                onValueChange = { next ->
                                    url = next
                                    if (searching || results.isNotEmpty() || metadataTitle.isNotBlank()) {
                                        searchGeneration++
                                        results = emptyList(); metadataTitle = ""; metadataDescription = ""; metadataPublisher = ""; metadataPublished = ""; topics = ""
                                        status = "Neuer Link eingegeben. Suche erneut, um passende Artikel zu laden."; searching = false
                                    }
                                },
                                modifier = Modifier.weight(1f).padding(vertical = 12.dp),
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                                keyboardActions = KeyboardActions(onSearch = { search() }),
                                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = Ink),
                                decorationBox = { inner ->
                                    if (url.isEmpty()) Text("Link zum Artikel einfügen", fontSize = 14.sp, color = Muted)
                                    inner()
                                }
                            )
                            Box(Modifier.background(if (searching) Muted else Green, RoundedCornerShape(11.dp)).clickable(enabled = !searching) { search() }.padding(horizontal = 15.dp, vertical = 12.dp)) {
                                Text(if (searching) "Suche …" else "Suchen", color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                            }
                        }
                        Spacer(Modifier.height(13.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Rounded.CheckCircle, null, tint = Green, modifier = Modifier.size(15.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Wir umgehen keine Paywalls. Prüfe die Zugänglichkeit bei der Originalquelle.", fontSize = 11.sp, color = Muted)
                        }
                        Spacer(Modifier.height(28.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(if (results.isEmpty()) "Passende Perspektiven" else "Passende Perspektiven", fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = Ink)
                            Spacer(Modifier.weight(1f))
                            Icon(Icons.Rounded.Tune, null, tint = Muted, modifier = Modifier.size(19.dp))
                        }
                        Spacer(Modifier.height(5.dp))
                        Text(if (metadataTitle.isNotBlank()) "Artikel: $metadataTitle" else "Artikel werden passend zu deinem Link gesucht", fontSize = 12.sp, color = Muted)
                        if (metadataPublisher.isNotBlank() || metadataPublished.isNotBlank()) {
                            Spacer(Modifier.height(4.dp))
                            Text(listOf(metadataPublisher, metadataPublished).filter { it.isNotBlank() }.joinToString(" · "), fontSize = 11.sp, color = Muted)
                        }
                        if (metadataDescription.isNotBlank()) {
                            Spacer(Modifier.height(5.dp))
                            Text(metadataDescription, fontSize = 12.sp, lineHeight = 17.sp, color = Muted, maxLines = 3, overflow = TextOverflow.Ellipsis)
                        }
                        if (topics.isNotBlank()) {
                            Spacer(Modifier.height(6.dp))
                            Text("Themen: $topics", fontSize = 11.sp, color = Green)
                        }
                        Spacer(Modifier.height(14.dp))
                        Row(Modifier.fillMaxWidth().background(Color(0xFFECEDE7), RoundedCornerShape(12.dp)).padding(4.dp)) {
                            listOf("Alle" to "all", "Deutsch" to "de", "English" to "en").forEach { (label, value) ->
                                Box(Modifier.weight(1f).background(if (languageFilter == value) Color.White else Color.Transparent, RoundedCornerShape(9.dp)).clickable { languageFilter = value }.padding(vertical = 9.dp), contentAlignment = Alignment.Center) {
                                    Text(label, fontSize = 12.sp, color = if (languageFilter == value) Ink else Muted, fontWeight = if (languageFilter == value) FontWeight.SemiBold else FontWeight.Normal)
                                }
                            }
                        }
                        Spacer(Modifier.height(14.dp))
                        if (visibleResults.isEmpty()) {
                            Text(status, Modifier.fillMaxWidth().padding(vertical = 14.dp), fontSize = 13.sp, lineHeight = 19.sp, color = Muted)
                        } else {
                            visibleResults.forEachIndexed { i, story -> StoryCard(story) { selected = i } }
                        }
                        Spacer(Modifier.height(14.dp))
                        Text("QUELLEN, DIE WIR MÖGEN", fontSize = 10.sp, letterSpacing = 1.5.sp, color = Muted, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Text("Tagesschau   ·   BBC   ·   DW   ·   The Guardian   ·   Deutschlandfunk   ·   Reuters   ·   NPR", fontSize = 12.sp, lineHeight = 20.sp, color = Muted)
                        Spacer(Modifier.height(20.dp))
                        Column(Modifier.fillMaxWidth().background(Color(0xFFEDF1EA), RoundedCornerShape(15.dp)).border(1.dp, Color(0xFFDCE4DA), RoundedCornerShape(15.dp)).padding(17.dp)) {
                            Text("Freilesen bleibt kostenlos.", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = Ink)
                            Spacer(Modifier.height(6.dp))
                            Text("Wenn dir die App gefällt, kannst du mir freiwillig einen Kaffee spendieren. Danke, dass du unabhängigen Journalismus unterstützt.", fontSize = 12.sp, lineHeight = 18.sp, color = Muted)
                            Spacer(Modifier.height(13.dp))
                            Box(Modifier.background(Green, RoundedCornerShape(10.dp)).clickable { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://www.paypal.com/donate/?business=dome0903%40yahoo.de&item_name=Freilesen&currency_code=EUR"))) }.padding(horizontal = 14.dp, vertical = 11.dp)) {
                                Text("☕  Kaffee spendieren", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
                            }
                        }
                        Spacer(Modifier.height(24.dp))
                    }
                }
                Row(Modifier.fillMaxWidth().background(Color.White).border(width = 1.dp, color = Line).padding(top = 10.dp, bottom = 12.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
                    listOf("Entdecken", "Merkliste", "Über uns").forEach { label ->
                        Column(Modifier.clickable { tab = label }.padding(horizontal = 14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(if (label == "Entdecken") "⌂" else if (label == "Merkliste") "♡" else "i", fontSize = 19.sp, color = if (tab == label) Green else Muted)
                            Text(label, fontSize = 10.sp, color = if (tab == label) Green else Muted)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StoryCard(story: Story, onClick: () -> Unit) {
    val scoreHue = story.score * 1.2f
    val scoreColor = Color.hsv(scoreHue, 0.76f, 0.72f)
    val scoreBackground = Color.hsv(scoreHue, 0.28f, 0.98f)
    val tint = if (story.language == "de") Color(0xFFEAE5DB) else Color(0xFFE1E8E8)
    Column(Modifier.fillMaxWidth().padding(bottom = 11.dp).background(Color.White, RoundedCornerShape(15.dp)).border(1.dp, Line, RoundedCornerShape(15.dp)).clickable(onClick = onClick)) {
        Box(Modifier.fillMaxWidth().height(82.dp).background(tint, RoundedCornerShape(topStart = 15.dp, topEnd = 15.dp)), contentAlignment = Alignment.CenterStart) {
            Row(Modifier.padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(38.dp).background(Color.White.copy(alpha = .58f), CircleShape), contentAlignment = Alignment.Center) {
                    Text(story.source.take(1).uppercase(), color = Green, fontSize = 15.sp, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    Text("THEMATISCHER TREFFER", fontSize = 9.sp, letterSpacing = 1.2.sp, color = Green, fontWeight = FontWeight.Bold)
                    Text(story.source, fontSize = 11.sp, color = Ink, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }
        }
        Column(Modifier.padding(15.dp)) {
            Text(story.title, fontSize = 17.sp, lineHeight = 22.sp, fontWeight = FontWeight.SemiBold, color = Ink)
            if (story.detail.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Text(story.detail, fontSize = 13.sp, lineHeight = 19.sp, color = Muted, maxLines = 3, overflow = TextOverflow.Ellipsis)
            }
            Spacer(Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text((if (story.language == "de") "DEUTSCH" else "ENGLISH") + if (story.published.isNotBlank()) " · ${story.published}" else "", fontSize = 9.sp, letterSpacing = 1.sp, color = Muted, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Box(Modifier.background(scoreBackground, RoundedCornerShape(50)).padding(horizontal = 9.dp, vertical = 6.dp)) { Text("${story.score}/100", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = scoreColor) }
                Spacer(Modifier.width(8.dp))
                Icon(Icons.Rounded.BookmarkBorder, null, tint = Muted, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(10.dp))
                Icon(Icons.Rounded.ArrowForward, null, tint = Green, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
private fun Reader(story: Story, onBack: () -> Unit) {
    val context = LocalContext.current
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp)) {
        Row(Modifier.fillMaxWidth().clickable(onClick = onBack).padding(vertical = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.ArrowBack, null, tint = Green)
            Spacer(Modifier.width(8.dp))
            Text("Zurück zu den Treffern", fontSize = 13.sp, color = Green)
        }
        Spacer(Modifier.height(35.dp))
        Text("FREI LESBAR  ·  ${story.source}", fontSize = 10.sp, letterSpacing = 1.4.sp, color = Green, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(18.dp))
        Text(story.title, fontSize = 32.sp, lineHeight = 38.sp, fontWeight = FontWeight.SemiBold, color = Ink)
        Spacer(Modifier.height(16.dp))
        Text(story.detail, fontSize = 18.sp, lineHeight = 27.sp, color = Muted)
        Spacer(Modifier.height(24.dp))
        HorizontalDivider(color = Line)
        Spacer(Modifier.height(22.dp))
        Text("Suchtreffer · Die Zugänglichkeit kann sich ändern.", fontSize = 12.sp, color = Muted)
        Spacer(Modifier.height(30.dp))
        Text("Eine andere Perspektive zum Thema", fontSize = 21.sp, fontWeight = FontWeight.SemiBold, color = Ink)
        Spacer(Modifier.height(12.dp))
        Text("Der Score vergleicht erkannte Themen in Titel, URL und öffentlicher Beschreibung. Er ist eine Relevanzhilfe und kein Vergleich des vollständigen Artikeltexts. Öffne die Originalseite, um den Artikel zu lesen und die aktuelle Zugänglichkeit zu prüfen.", fontSize = 16.sp, lineHeight = 26.sp, color = Ink)
        Spacer(Modifier.height(12.dp))
        Text("Themenübereinstimmung: ${story.score}/100", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Green)
        Spacer(Modifier.height(20.dp))
        Box(Modifier.background(Green, RoundedCornerShape(10.dp)).clickable { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(story.url))) }.padding(horizontal = 16.dp, vertical = 12.dp)) {
            Text("Originalquelle öffnen ↗", color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(40.dp))
    }
}
