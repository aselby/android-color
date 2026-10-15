package com.anthonyselby.coloring

import android.app.Application
import com.anthonyselby.coloring.data.PageRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class ColoringApplication : Application() {
    lateinit var repository: PageRepository
        private set

    /** Long-lived scope for saves that must outlive a screen. */
    val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    override fun onCreate() {
        super.onCreate()
        repository = PageRepository(this)
    }
}
