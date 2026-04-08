package com.uiblueprint.android

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.uiblueprint.android.databinding.ItemSessionBinding

/**
 * RecyclerView adapter for the in-memory session list shown on [MainActivity].
 *
 * Saved items are clickable; failed items are visually dimmed and non-interactive.
 */
class SessionAdapter(
    private val sessions: List<MainActivity.SessionItem>,
    private val onSavedItemClick: (MainActivity.SessionItem) -> Unit,
) : RecyclerView.Adapter<SessionAdapter.ViewHolder>() {

    inner class ViewHolder(private val binding: ItemSessionBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(item: MainActivity.SessionItem) {
            binding.tvLabel.text = item.label
            binding.tvStatus.text = "[${item.status}]"

            val isSaved = item.status == MainActivity.STATUS_SAVED
            binding.root.isEnabled = isSaved
            binding.root.alpha = if (isSaved) 1.0f else 0.4f
            binding.root.setOnClickListener(null)
            if (isSaved) {
                binding.root.setOnClickListener { onSavedItemClick(item) }
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemSessionBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(sessions[position])
    }

    override fun getItemCount(): Int = sessions.size
}
