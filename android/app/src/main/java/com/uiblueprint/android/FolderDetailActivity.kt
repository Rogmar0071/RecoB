package com.uiblueprint.android

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.uiblueprint.android.databinding.ActivityFolderDetailBinding
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.Executors

/**
 * Per-folder detail screen.
 *
 * Shows:
 *  - Folder title, status, and UUID
 *  - Jobs list (type + status + progress)
 *  - Artifacts list (type)
 *  - Per-folder chat (GET/POST /v1/folders/{id}/messages)
 *
 * Requires [EXTRA_FOLDER_ID] to be set in the launching Intent.
 *
 * Authorization: Bearer <BACKEND_API_KEY> is added when non-empty.
 * The API key is never logged.
 */
class FolderDetailActivity : AppCompatActivity() {

    private lateinit var binding: ActivityFolderDetailBinding
    private lateinit var folderId: String
    private val executor = Executors.newSingleThreadExecutor { Thread(it, "FolderDetail-worker") }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityFolderDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        folderId = intent.getStringExtra(EXTRA_FOLDER_ID)
            ?: run {
                finish()
                return
            }

        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = getString(R.string.folder_detail_title)

        binding.btnSend.setOnClickListener { onSendClicked() }
        binding.tvFolderTitle.text = getString(R.string.folder_detail_title)
        binding.tvFolderStatus.text = getString(R.string.folder_loading)
        binding.tvFolderId.text = getString(R.string.label_folder_id, folderId)

        loadFolder()
        loadMessages()
    }

    override fun onDestroy() {
        super.onDestroy()
        executor.shutdownNow()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    // -------------------------------------------------------------------------
    // Load folder detail
    // -------------------------------------------------------------------------

    private fun loadFolder() {
        val baseUrl = BuildConfig.BACKEND_BASE_URL.trimEnd('/')
        val apiKey = BuildConfig.BACKEND_API_KEY

        val request = Request.Builder()
            .url("$baseUrl/v1/folders/$folderId")
            .get()
            .apply { if (apiKey.isNotEmpty()) addHeader("Authorization", "Bearer $apiKey") }
            .build()

        executor.execute {
            try {
                val response = BackendClient.executeWithRetry(request)
                response.use { resp ->
                    val bodyStr = resp.body?.string() ?: ""
                    runOnUiThread {
                        if (resp.isSuccessful) {
                            renderFolder(JSONObject(bodyStr))
                        } else {
                            binding.tvFolderStatus.text = getString(
                                R.string.folder_load_error,
                            )
                        }
                    }
                }
            } catch (e: IOException) {
                runOnUiThread {
                    binding.tvFolderStatus.text = getString(R.string.folder_load_error)
                }
            }
        }
    }

    private fun renderFolder(json: JSONObject) {
        val title = json.optString("title", "")
        val shortId = folderId.take(8)
        binding.tvFolderTitle.text = if (title.isNotEmpty()) title else "Folder $shortId"
        binding.tvFolderStatus.text = getString(R.string.label_folder_status, json.optString("status", "?"))
        binding.tvFolderId.text = getString(R.string.label_folder_id, folderId)

        // Jobs
        val jobs = json.optJSONArray("jobs")
        binding.tvJobs.text = if (jobs == null || jobs.length() == 0) {
            getString(R.string.folder_no_jobs)
        } else {
            buildString {
                for (i in 0 until jobs.length()) {
                    val job = jobs.getJSONObject(i)
                    appendLine(
                        "${job.optString("type")}  –  ${job.optString("status")} " +
                            "(${job.optInt("progress")}%)",
                    )
                }
            }.trim()
        }

        // Artifacts
        val artifacts = json.optJSONArray("artifacts")
        binding.tvArtifacts.text = if (artifacts == null || artifacts.length() == 0) {
            getString(R.string.folder_no_artifacts)
        } else {
            buildString {
                for (i in 0 until artifacts.length()) {
                    val a = artifacts.getJSONObject(i)
                    appendLine("• ${a.optString("type")}")
                }
            }.trim()
        }
    }

    // -------------------------------------------------------------------------
    // Load and render chat messages
    // -------------------------------------------------------------------------

    private fun loadMessages() {
        val baseUrl = BuildConfig.BACKEND_BASE_URL.trimEnd('/')
        val apiKey = BuildConfig.BACKEND_API_KEY

        val request = Request.Builder()
            .url("$baseUrl/v1/folders/$folderId/messages")
            .get()
            .apply { if (apiKey.isNotEmpty()) addHeader("Authorization", "Bearer $apiKey") }
            .build()

        executor.execute {
            try {
                val response = BackendClient.executeWithRetry(request)
                response.use { resp ->
                    val bodyStr = resp.body?.string() ?: ""
                    if (resp.isSuccessful) {
                        val messages = JSONObject(bodyStr).optJSONArray("messages")
                        runOnUiThread { renderMessages(messages) }
                    }
                }
            } catch (_: IOException) {
                // Best-effort; chat log stays empty on error
            }
        }
    }

    private fun renderMessages(messages: JSONArray?) {
        if (messages == null || messages.length() == 0) return
        val sb = StringBuilder()
        for (i in 0 until messages.length()) {
            val msg = messages.getJSONObject(i)
            val role = msg.optString("role", "?")
            val content = msg.optString("content", "")
            val prefix = if (role == "user") "You" else "AI"
            if (sb.isNotEmpty()) sb.append("\n")
            sb.append("$prefix: $content")
        }
        binding.tvChatLog.text = sb.toString()
        scrollChatToBottom()
    }

    // -------------------------------------------------------------------------
    // Send chat message
    // -------------------------------------------------------------------------

    private fun onSendClicked() {
        val message = binding.etMessage.text.toString().trim()
        if (message.isBlank()) return

        binding.etMessage.setText("")
        binding.btnSend.isEnabled = false
        appendChatLine("You: $message")

        val baseUrl = BuildConfig.BACKEND_BASE_URL.trimEnd('/')
        val apiKey = BuildConfig.BACKEND_API_KEY

        val bodyJson = JSONObject().put("message", message).toString()
        val request = Request.Builder()
            .url("$baseUrl/v1/folders/$folderId/messages")
            .post(bodyJson.toRequestBody("application/json".toMediaType()))
            .apply { if (apiKey.isNotEmpty()) addHeader("Authorization", "Bearer $apiKey") }
            .build()

        executor.execute {
            try {
                val response = BackendClient.executeWithRetry(request) { attempt, total ->
                    runOnUiThread {
                        appendChatLine(getString(R.string.folder_chat_retrying, attempt, total))
                    }
                }
                response.use { resp ->
                    val bodyStr = resp.body?.string() ?: ""
                    runOnUiThread {
                        if (resp.isSuccessful) {
                            val reply = runCatching {
                                JSONObject(bodyStr)
                                    .getJSONObject("assistant_message")
                                    .getString("content")
                            }.getOrElse { "Error: unexpected response" }
                            appendChatLine("AI: $reply")
                        } else {
                            appendChatLine("Error: HTTP ${resp.code}")
                        }
                        binding.btnSend.isEnabled = true
                    }
                }
            } catch (e: IOException) {
                runOnUiThread {
                    appendChatLine("Error: ${e.message ?: "Network error"}")
                    binding.btnSend.isEnabled = true
                }
            }
        }
    }

    private fun appendChatLine(line: String) {
        val current = binding.tvChatLog.text
        binding.tvChatLog.text = if (current.isNullOrEmpty()) line else "$current\n$line"
        scrollChatToBottom()
    }

    private fun scrollChatToBottom() {
        binding.scrollChat.post {
            binding.scrollChat.fullScroll(View.FOCUS_DOWN)
        }
    }

    companion object {
        const val EXTRA_FOLDER_ID = "folder_id"
    }
}
