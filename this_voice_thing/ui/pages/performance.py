"""Settings › Performance: how much of the PC generation may use, and warnings before heavy jobs."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from this_voice_thing.core import resources


class PerformancePage:
    """Resource limits with machine-based defaults. Mixed into the main window."""

    def apply_resource_limits(self):
        """Read the saved limits (clamped to this PC), put them in force, and cap this process's
        own PyTorch threads (in-process engines such as Chatterbox)."""
        if not hasattr(self, "system_info"):
            self.system_info = resources.detect()
        self.resource_limits = resources.from_settings(self.app_settings.get("performance"), self.system_info)
        resources.set_current(self.resource_limits)
        try:
            import torch
            torch.set_num_threads(self.resource_limits.cpu_threads)
        except Exception as exc:
            print(f"Couldn't limit PyTorch threads: {exc}")
        return self.resource_limits

    def _build_performance_card(self):
        system, limits = self.system_info, self.resource_limits
        card, layout = self._make_card("Performance")
        gpu = f"{system.gpu_name}, {system.gpu_gb:g} GB" if system.gpu_name else "no NVIDIA GPU found"
        machine = QLabel(f"This PC: {system.cpu_threads} CPU threads, {system.ram_gb:.0f} GB RAM, {gpu}. "
                         "These limits apply to every model the app runs; a change applies the next time a "
                         "model starts.")
        machine.setObjectName("Muted")
        machine.setWordWrap(True)
        layout.addWidget(machine)

        row = QHBoxLayout()
        row.addWidget(QLabel("CPU threads"))
        self.perf_threads_spin = QSpinBox()
        self.perf_threads_spin.setRange(1, system.cpu_threads)
        self.perf_threads_spin.setValue(limits.cpu_threads)
        self.perf_threads_spin.setAccessibleName("CPU threads per model")
        self.perf_threads_spin.setToolTip("How many CPU threads one model may use for its maths. Fewer keeps "
                                          "the PC responsive; more can make CPU-heavy steps faster.")
        row.addWidget(self.perf_threads_spin)
        row.addSpacing(12)
        row.addWidget(QLabel("Priority"))
        self.perf_priority_combo = QComboBox()
        self.perf_priority_combo.setAccessibleName("Model priority")
        for key in resources.PRIORITIES:
            self.perf_priority_combo.addItem(resources.PRIORITY_LABELS[key], key)
        self.perf_priority_combo.setCurrentIndex(self.perf_priority_combo.findData(limits.priority))
        self.perf_priority_combo.setToolTip("Models run as separate processes. Below normal lets games and "
                                            "other apps go first; Low runs models only on spare CPU time.")
        row.addWidget(self.perf_priority_combo)
        row.addSpacing(12)
        row.addWidget(QLabel("GPU memory limit"))
        self.perf_gpu_spin = QDoubleSpinBox()
        self.perf_gpu_spin.setDecimals(1)
        self.perf_gpu_spin.setSingleStep(0.5)
        self.perf_gpu_spin.setSuffix(" GB")
        self.perf_gpu_spin.setRange(0.0, max(0.0, system.gpu_gb))
        self.perf_gpu_spin.setValue(limits.gpu_memory_gb)
        self.perf_gpu_spin.setEnabled(bool(system.gpu_gb))
        self.perf_gpu_spin.setAccessibleName("GPU memory limit")
        self.perf_gpu_spin.setToolTip("The most GPU memory one model may take. A model that needs more stops "
                                      "with an out-of-memory message instead of spilling into system memory and "
                                      f"slowing the whole PC. The default keeps {resources.GPU_HEADROOM_GB:g} GB for "
                                      "the display; heavy jobs warn when little is left for games.")
        row.addWidget(self.perf_gpu_spin)
        row.addStretch(1)
        layout.addLayout(row)

        bottom = QHBoxLayout()
        self.perf_warn_checkbox = QCheckBox("Warn me before long or heavy jobs")
        self.perf_warn_checkbox.setChecked(limits.warn_heavy_jobs)
        self.perf_warn_checkbox.setToolTip("Shows the expected time, GPU memory and CPU use before a job that "
                                           "can slow the PC, so you can pick a better moment.")
        bottom.addWidget(self.perf_warn_checkbox)
        bottom.addStretch(1)
        self.perf_status = QLabel()
        self.perf_status.setObjectName("Muted")
        bottom.addWidget(self.perf_status)
        reset = QPushButton("Use recommended")
        reset.setToolTip("Half the CPU threads, below-normal priority, and nearly all GPU memory (a little kept for the display).")
        reset.clicked.connect(self.reset_resource_limits)
        bottom.addWidget(reset)
        layout.addLayout(bottom)

        self.perf_threads_spin.valueChanged.connect(self.save_resource_limits)
        self.perf_priority_combo.currentIndexChanged.connect(self.save_resource_limits)
        self.perf_gpu_spin.valueChanged.connect(self.save_resource_limits)
        self.perf_warn_checkbox.toggled.connect(self.save_resource_limits)
        return card

    def save_resource_limits(self, *_args):
        self.app_settings["performance"] = {
            "cpu_threads": self.perf_threads_spin.value(), "priority": self.perf_priority_combo.currentData(),
            "gpu_memory_gb": round(self.perf_gpu_spin.value(), 1), "warn_heavy_jobs": self.perf_warn_checkbox.isChecked()}
        self.save_app_settings()
        self.apply_resource_limits()
        self.perf_status.setText("Saved; applies the next time a model starts.")

    def reset_resource_limits(self):
        limits = resources.recommended(self.system_info)
        for widget, value in ((self.perf_threads_spin, limits.cpu_threads), (self.perf_gpu_spin, limits.gpu_memory_gb),
                              (self.perf_warn_checkbox, limits.warn_heavy_jobs)):
            widget.blockSignals(True)
            (widget.setChecked if isinstance(widget, QCheckBox) else widget.setValue)(value)
            widget.blockSignals(False)
        self.perf_priority_combo.blockSignals(True)
        self.perf_priority_combo.setCurrentIndex(self.perf_priority_combo.findData(limits.priority))
        self.perf_priority_combo.blockSignals(False)
        self.save_resource_limits()

    def confirm_heavy_job(self, cost, title):
        """Explain what `cost` will take before it runs. False if the user cancels, or if it can't
        fit the limits (then it says why). Quiet for light jobs or when warnings are off."""
        limits, system = resources.current() or self.apply_resource_limits(), self.system_info
        problems = resources.over_budget(cost, limits, system)
        if problems:
            QMessageBox.warning(self, title, f"{cost.label} won't fit: it " + "; it ".join(problems) +
                                ".\n\nRaise the limit in Settings › Performance, or choose a smaller job.")
            return False
        if not limits.warn_heavy_jobs or not resources.heavy(cost, limits):
            return True
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"{cost.label} is a heavy job.")
        box.setInformativeText(resources.warning_text(cost, limits, system))
        go = box.addButton("Start", QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(go)
        box.exec()
        return box.clickedButton() is go
