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
import org.json.JSONArray
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
    val score: Int = 0,
    val access: String = "",
    val commonTopics: String = ""
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
                    score = item.optInt("score", 0).coerceIn(0, 100),
                    access = item.optString("access", ""),
                    commonTopics = item.optJSONArray("matchedTopics")?.let { a -> (0 until a.length()).take(4).joinToString(" · ") { a.optString(it) } } ?: ""
                ))
            }
        }
        SearchResponse(
            metadataTitle = meta.optString("title", "Artikel"),
            metadataDescription = meta.optString("description", ""),
            metadataPublisher = meta.optString("publisher", ""),
            metadataPublished = meta.optString("published", ""),
            topics = (json.optJSONArray("topics")?.let { a -> (0 until a.length()).joinToString(" · ") { a.optString(it) } } ?: ""),
            results = results.filter { it.access != "paywall" && it.access != "unavailable" },
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
    val libraryPrefs = remember { context.getSharedPreferences("freilesen-library", android.content.Context.MODE_PRIVATE) }
    var folders by remember { mutableStateOf(runCatching { val a=JSONArray(libraryPrefs.getString("folders", "[\"Allgemein\"]")); (0 until a.length()).map { a.getString(it) } }.getOrDefault(listOf("Allgemein"))) }
    var savedStories by remember { mutableStateOf(runCatching { val a=JSONArray(libraryPrefs.getString("bookmarks", "[]")); (0 until a.length()).mapNotNull { i -> a.optJSONObject(i)?.let { o -> Story(o.optString("source"), o.optString("title"), o.optString("detail"), o.optString("url"), o.optString("language"), o.optString("published"), o.optInt("score"), o.optString("access"), o.optString("commonTopics")) to o.optString("folder", "Allgemein") } } }.getOrDefault(emptyList())) }
    var showFolderDialog by remember { mutableStateOf(false) }
    var folderName by remember { mutableStateOf("") }
    var storyToSave by remember { mutableStateOf<Story?>(null) }
    var openedSavedStory by remember { mutableStateOf<Story?>(null) }
    var currentFolder by remember { mutableStateOf("Allgemein") }
    fun persistLibrary() {
        val fs = JSONArray().apply { folders.forEach { put(it) } }
        val bs = JSONArray().apply { savedStories.forEach { (s,f) -> put(JSONObject().put("source",s.source).put("title",s.title).put("detail",s.detail).put("url",s.url).put("language",s.language).put("published",s.published).put("score",s.score).put("access",s.access).put("commonTopics",s.commonTopics).put("folder",f)) } }
        libraryPrefs.edit().putString("folders",fs.toString()).putString("bookmarks",bs.toString()).apply()
    }

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
                if (tab == "Merkliste") {
                    BookmarkManager(folders, savedStories, currentFolder, onFolderSelect = { currentFolder=it }, onAddFolder = { showFolderDialog=true }, onOpen = { story, folder -> openedSavedStory=story; currentFolder=folder; tab="Entdecken" }, onRemove = { story -> savedStories=savedStories.filterNot { it.first.url==story.url }; persistLibrary() })
                } else if (openedSavedStory != null) {
                    Reader(openedSavedStory!!) { openedSavedStory=null; tab="Merkliste" }
                } else if (selected >= 0 && selected < visibleResults.size) {
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
                            visibleResults.forEachIndexed { i, story -> StoryCard(story, savedStories.any { it.first.url==story.url }, { storyToSave=story }) { selected = i } }
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
                        Column(Modifier.clickable { tab = label; selected = -1 }.padding(horizontal = 14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(if (label == "Entdecken") "⌂" else if (label == "Merkliste") "♡" else "i", fontSize = 19.sp, color = if (tab == label) Green else Muted)
                            Text(label, fontSize = 10.sp, color = if (tab == label) Green else Muted)
                        }
                    }
                }
            }
        }
        if (showFolderDialog) AlertDialog(onDismissRequest={showFolderDialog=false}, title={Text("Themenordner anlegen")}, text={OutlinedTextField(folderName,{folderName=it},label={Text("Ordnername")},singleLine=true)}, confirmButton={TextButton(onClick={val n=folderName.trim(); if(n.isNotEmpty()){if(n !in folders) folders=folders+n;currentFolder=n;storyToSave?.let { savedStories=savedStories.filterNot{entry->entry.first.url==it.url}+(it to n);storyToSave=null };persistLibrary()};folderName="";showFolderDialog=false}){Text("Anlegen")}}, dismissButton={TextButton(onClick={showFolderDialog=false}){Text("Abbrechen")}})
        storyToSave?.let { target -> AlertDialog(onDismissRequest={storyToSave=null}, title={Text("In Themenordner speichern")}, text={Column { folders.forEach { name -> TextButton(onClick={savedStories=savedStories.filterNot{it.first.url==target.url}+(target to name);currentFolder=name;persistLibrary();storyToSave=null}){Text(name)} }; TextButton(onClick={showFolderDialog=true}){Text("＋ Neuen Ordner anlegen")}}},confirmButton={},dismissButton={TextButton(onClick={storyToSave=null}){Text("Schließen")}}) }
    }
}

@Composable
private fun BookmarkManager(folders: List<String>, saved: List<Pair<Story,String>>, selectedFolder: String, onFolderSelect: (String)->Unit, onAddFolder: ()->Unit, onOpen: (Story,String)->Unit, onRemove: (Story)->Unit) {
    Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal=22.dp)) {
        Spacer(Modifier.height(28.dp)); Text("DEINE SAMMLUNG",fontSize=10.sp,letterSpacing=2.sp,color=Green,fontWeight=FontWeight.Bold)
        Spacer(Modifier.height(8.dp)); Text("Merkliste",fontSize=32.sp,fontWeight=FontWeight.SemiBold,color=Ink)
        Spacer(Modifier.height(6.dp)); Text("Lege Themenordner an und speichere Artikel für später.",fontSize=14.sp,lineHeight=21.sp,color=Muted)
        Spacer(Modifier.height(18.dp)); Row(verticalAlignment=Alignment.CenterVertically) { Text("Ordner",fontSize=19.sp,fontWeight=FontWeight.SemiBold,color=Ink); Spacer(Modifier.weight(1f)); TextButton(onClick=onAddFolder){Text("＋ Ordner") } }
        folders.forEach { folder -> Row(Modifier.fillMaxWidth().padding(bottom=8.dp).background(if(folder==selectedFolder) Color(0xFFE7EEE7) else Color.White,RoundedCornerShape(12.dp)).clickable { onFolderSelect(folder) }.padding(horizontal=14.dp, vertical=13.dp),verticalAlignment=Alignment.CenterVertically){Text("▤  $folder",Modifier.weight(1f),fontSize=14.sp,color=if(folder==selectedFolder) Green else Ink,fontWeight=FontWeight.Medium);Text("${saved.count{it.second==folder}}",fontSize=12.sp,color=Muted)} }
        Spacer(Modifier.height(18.dp)); Text("$selectedFolder",fontSize=20.sp,fontWeight=FontWeight.SemiBold,color=Ink); Spacer(Modifier.height(12.dp))
        val items=saved.filter{it.second==selectedFolder}
        if(items.isEmpty()) Text("In diesem Ordner sind noch keine Artikel. Speichere einen Treffer über das Lesezeichen-Symbol.",Modifier.padding(vertical=10.dp),fontSize=13.sp,lineHeight=20.sp,color=Muted)
        items.forEach { (story,folder) -> Column(Modifier.fillMaxWidth().padding(bottom=10.dp).background(Color.White,RoundedCornerShape(14.dp)).clickable { onOpen(story,folder) }.padding(15.dp)){Text(story.source.uppercase(),fontSize=9.sp,letterSpacing=1.sp,color=Green,fontWeight=FontWeight.Bold);Spacer(Modifier.height(6.dp));Text(story.title,fontSize=16.sp,lineHeight=21.sp,fontWeight=FontWeight.SemiBold,color=Ink);Spacer(Modifier.height(8.dp));Row(verticalAlignment=Alignment.CenterVertically){Text("${story.score}/100 · ${when (story.access) { "verified_free" -> "frei geprüft"; "likely_free" -> "wahrscheinlich frei"; else -> "möglicherweise frei" }}",Modifier.weight(1f),fontSize=11.sp,color=Muted);TextButton(onClick={onRemove(story)}){Text("Entfernen",color=Muted)}}} }
    }
}

@Composable
private fun StoryCard(story: Story, isSaved: Boolean, onSave: () -> Unit, onClick: () -> Unit) {
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
                    Text((when (story.access) { "verified_free" -> "FREI GEPRÜFT"; "likely_free" -> "WAHRSCHEINLICH FREI"; else -> "MÖGLICHERWEISE FREI" }) + " · THEMENMATCH", fontSize = 9.sp, letterSpacing = 1.1.sp, color = Green, fontWeight = FontWeight.Bold)
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
            if (story.commonTopics.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Text("Gemeinsame Themen: ${story.commonTopics}", fontSize = 10.sp, lineHeight = 14.sp, color = Green, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
            Spacer(Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text((if (story.language == "de") "DEUTSCH" else "ENGLISH") + if (story.published.isNotBlank()) " · ${story.published}" else "", fontSize = 9.sp, letterSpacing = 1.sp, color = Muted, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Box(Modifier.background(scoreBackground, RoundedCornerShape(50)).padding(horizontal = 9.dp, vertical = 6.dp)) { Text("${story.score}/100", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = scoreColor) }
                Spacer(Modifier.width(8.dp))
                Icon(Icons.Rounded.BookmarkBorder, "In Themenordner speichern", tint = if(isSaved) Green else Muted, modifier = Modifier.size(18.dp).clickable { onSave() })
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
        Text((when (story.access) { "verified_free" -> "FREI ZUGÄNGLICH GEPRÜFT"; "likely_free" -> "ZUGRIFF WAHRSCHEINLICH FREI"; else -> "ZUGRIFF MÖGLICHERWEISE FREI" }) + "  ·  ${story.source}", fontSize = 10.sp, letterSpacing = 1.1.sp, color = Green, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(18.dp))
        Text(story.title, fontSize = 32.sp, lineHeight = 38.sp, fontWeight = FontWeight.SemiBold, color = Ink)
        Spacer(Modifier.height(16.dp))
        Text(story.detail, fontSize = 18.sp, lineHeight = 27.sp, color = Muted)
        Spacer(Modifier.height(24.dp))
        HorizontalDivider(color = Line)
        Spacer(Modifier.height(22.dp))
        Text(when (story.access) { "verified_free" -> "Beim Verlag ohne erkannte Bezahlschranke geprüft."; "likely_free" -> "Wahrscheinlich frei: Die Seite war lesbar, ein eindeutiges Freizugriffs-Merkmal fehlte."; else -> "Möglicherweise frei: Die Seite ließ sich nicht zuverlässig prüfen; ein eindeutiger Paywall-Hinweis wurde nicht erkannt." }, fontSize = 12.sp, color = Muted)
        Spacer(Modifier.height(5.dp))
        Text("Der Zugriff kann sich ändern; im Zweifel zeigt die Originalseite, ob eine Paywall erscheint.", fontSize = 12.sp, color = Muted)
        Spacer(Modifier.height(30.dp))
        Text("Eine andere Perspektive zum Thema", fontSize = 21.sp, fontWeight = FontWeight.SemiBold, color = Ink)
        Spacer(Modifier.height(12.dp))
        Text("Der Score vergleicht erkannte Themen in verfügbaren Metadaten und nicht den vollständigen Artikeltext.", fontSize = 16.sp, lineHeight = 26.sp, color = Ink)
        Spacer(Modifier.height(12.dp))
        Text("Themenübereinstimmung: ${story.score}/100", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Green)
        Spacer(Modifier.height(14.dp))
        Text("Urheberrecht beachten: Die angezeigten Treffer sind eigenständige Alternativen zum Originalartikel, keine Kopien oder wortgleichen Fassungen. Ein niedriger Score bedeutet nur eine geringere erkannte Themenüberschneidung – der Artikel kann trotzdem die gesuchten Informationen enthalten. Für den vollständigen Inhalt und Kontext öffne bitte die Originalquelle.", fontSize = 13.sp, lineHeight = 20.sp, color = Muted)
        Spacer(Modifier.height(20.dp))
        Box(Modifier.background(Green, RoundedCornerShape(10.dp)).clickable { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(story.url))) }.padding(horizontal = 16.dp, vertical = 12.dp)) {
            Text("Originalquelle öffnen ↗", color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(40.dp))
    }
}
