package com.uiblueprint.android

import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.uiblueprint.android.databinding.ActivityVideoPlayerBinding

/**
 * Plays a locally saved clip inside the app using Media3 ExoPlayer.
 *
 * Expects [EXTRA_URI_STRING] as the MediaStore uri string stored in [MainActivity.SessionItem.uri].
 * Shows a toast and finishes if the uri is missing, invalid, or playback fails.
 */
class VideoPlayerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityVideoPlayerBinding
    private var player: ExoPlayer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityVideoPlayerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val uriString = intent.getStringExtra(EXTRA_URI_STRING)
        if (uriString.isNullOrBlank()) {
            showErrorAndFinish()
            return
        }

        val uri: Uri = try {
            Uri.parse(uriString)
        } catch (_: Exception) {
            showErrorAndFinish()
            return
        }

        initPlayer(uri)
    }

    private fun initPlayer(uri: Uri) {
        val exoPlayer = ExoPlayer.Builder(this).build().also { player = it }
        binding.playerView.player = exoPlayer

        exoPlayer.addListener(object : Player.Listener {
            override fun onPlayerError(error: PlaybackException) {
                showErrorAndFinish()
            }
        })

        exoPlayer.setMediaItem(MediaItem.fromUri(uri))
        exoPlayer.prepare()
        exoPlayer.playWhenReady = true
    }

    override fun onStop() {
        super.onStop()
        releasePlayer()
    }

    private fun releasePlayer() {
        player?.release()
        player = null
    }

    private fun showErrorAndFinish() {
        Toast.makeText(this, getString(R.string.error_video_open), Toast.LENGTH_SHORT).show()
        finish()
    }

    companion object {
        const val EXTRA_URI_STRING = "uri_string"
    }
}
