"""The Settings page: pronunciation dictionary, local API and the log."""


class AdvancedPage:
    """The Settings page: pronunciation dictionary, local API and log. Mixed into ChatterboxApp."""

    def _build_advanced_page(self):
        advanced_page, advanced_layout = self._make_page(
            "Settings", "Pronunciation, the local API, and the technical log.")
        advanced_layout.addWidget(self._build_pronunciation_card())
        self.update_pronunciation_summary()
        advanced_layout.addWidget(self._build_api_card())
        advanced_layout.addWidget(self._build_log_card(), 1)
        self.pages.addWidget(advanced_page)

