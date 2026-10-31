import os
import tempfile
import unittest
import wave

import numpy as np

from this_voice_thing.core.live_voice import AudioFileSpeechSession, CachedSpeechSession, LiveSpeechSession


class NativeModel:
    sr = 48000
    native_streaming = True

    def generate_streaming_pcm(self, text, audio_prompt_path=None):
        self.seen = (text, audio_prompt_path)
        yield b"\x01\x02"
        yield b"\x03\x04"


class SegmentedModel:
    sr = 24000
    segmented_streaming = True

    def generate_segmented_pcm(self, text, language_id=None, paragraph_pause=0.35):
        self.seen = (text, language_id, paragraph_pause)
        yield b"\x05\x06"


class BufferedModel:
    sr = 16000

    def generate(self, text, **kwargs):
        self.seen = (text, kwargs)
        return np.asarray([[0.5, -0.5]], dtype=np.float32)


class Pronunciations:
    def apply_section(self, text):
        return text.replace("SQL", "sequel"), 1


class AudioFileSpeechSessionTests(unittest.TestCase):
    def test_audio_file_streams_as_mono_pcm(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = handle.name
        handle.close()
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(22050)
                # Opposite stereo channels should downmix close to silence.
                frames = b"".join(
                    int(1000).to_bytes(2, "little", signed=True)
                    + int(-1000).to_bytes(2, "little", signed=True)
                    for _ in range(64)
                )
                output.writeframes(frames)

            session = AudioFileSpeechSession(path)
            chunks = list(session.frames())
            samples = np.frombuffer(b"".join(frame.pcm for frame in chunks), dtype="<i2")

            self.assertEqual(session.delivery_mode, "audio")
            self.assertEqual(session.sample_rate, 22050)
            self.assertGreater(len(samples), 0)
            self.assertLessEqual(int(np.max(np.abs(samples))), 2)
            self.assertEqual(session.metrics()["provenance"], "soundboard-audio-file")
        finally:
            os.remove(path)


class CachedSpeechSessionTests(unittest.TestCase):
    def test_cached_wav_uses_same_pcm_frame_interface(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = handle.name
        handle.close()
        pcm = b"\x01\x00\x02\x00" * 16
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
                output.writeframes(pcm)

            session = CachedSpeechSession(
                path, provenance="live-native-unwatermarked"
            )
            frames = list(session.frames())

            self.assertEqual(session.delivery_mode, "cached")
            self.assertEqual(session.sample_rate, 24000)
            self.assertEqual(b"".join(frame.pcm for frame in frames), pcm)
            self.assertEqual(
                session.metrics()["provenance"],
                "live-native-unwatermarked",
            )
        finally:
            os.remove(path)

    def test_cached_wav_defaults_to_unknown_source_provenance(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = handle.name
        handle.close()
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(b"\x00\x00")

            session = CachedSpeechSession(path)

            self.assertEqual(
                session.metrics()["provenance"],
                "soundboard-cache-unknown",
            )
        finally:
            os.remove(path)

    def test_cached_wav_rejects_stereo(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = handle.name
        handle.close()
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(b"\x00\x00\x00\x00")

            with self.assertRaisesRegex(ValueError, "mono 16-bit PCM"):
                CachedSpeechSession(path)
        finally:
            os.remove(path)


class CachedPadStartsOnTheFirstWord(unittest.TestCase):
    """#13: a cached pad played the engine's leading silence (Kokoro: 165 ms) before the first
    word, so the audible latency was ~190 ms though the audio path took ~40 ms."""

    def write(self, samples, rate=24000):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        handle.close()
        with wave.open(handle.name, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes(np.asarray(samples, dtype="<i2").tobytes())
        self.addCleanup(os.remove, handle.name)
        return handle.name

    def test_leading_silence_is_skipped_with_a_short_preroll(self):
        rate = 24000
        silence = np.zeros(int(0.165 * rate), dtype=np.int16)
        noise = np.full(int(0.165 * rate), 3, dtype=np.int16)          # dither-level hiss, not a word
        word = (8000 * np.sin(np.arange(rate // 2) * 0.2)).astype(np.int16)
        for lead in (silence, noise):
            path = self.write(np.concatenate([lead, word]))
            session = CachedSpeechSession(path)
            played = np.frombuffer(b"".join(f.pcm for f in session.frames()), dtype="<i2")
            preroll = int(0.02 * rate)
            self.assertEqual(session.start_frame, len(lead) - preroll + 1)  # word[0] is 0; word[1] is the first sound
            self.assertEqual(len(played), len(word) + preroll - 1)
            self.assertTrue(np.array_equal(played[preroll - 1:], word))     # the word itself is untouched

    def test_a_clip_that_starts_loud_or_is_all_quiet_plays_whole(self):
        loud = self.write((8000 * np.sin(np.arange(2400) * 0.2 + 1.0)).astype(np.int16))
        quiet = self.write(np.full(2400, 2, dtype=np.int16))
        for path in (loud, quiet):
            session = CachedSpeechSession(path)
            self.assertEqual(session.start_frame, 0)
            self.assertEqual(len(b"".join(f.pcm for f in session.frames())), 4800)


class LiveSpeechSessionTests(unittest.TestCase):
    def test_native_mode_yields_pcm_and_applies_pronunciation(self):
        model = NativeModel()
        session = LiveSpeechSession(
            model, "SQL works.", audio_prompt_path="voice.wav",
            pronunciations=Pronunciations(),
        )

        frames = list(session.frames())

        self.assertEqual(session.delivery_mode, "native")
        self.assertEqual([frame.pcm for frame in frames], [b"\x01\x02", b"\x03\x04"])
        self.assertEqual(model.seen, ("sequel works.", "voice.wav"))
        self.assertEqual(session.metrics()["frames"], 2)

    def test_segmented_mode_receives_language_and_pause(self):
        model = SegmentedModel()
        session = LiveSpeechSession(
            model, "Hello.", language_id="fr", paragraph_pause=0.6,
        )

        frames = list(session.frames())

        self.assertEqual(session.delivery_mode, "segmented")
        self.assertEqual(frames[0].pcm, b"\x05\x06")
        self.assertEqual(model.seen, ("Hello.", "fr", 0.6))

    def test_buffered_fallback_converts_float_waveform_to_s16(self):
        model = BufferedModel()
        session = LiveSpeechSession(model, "Hello.", generate_kwargs={"temperature": 0.7})

        frames = list(session.frames())
        samples = np.frombuffer(frames[0].pcm, dtype="<i2")

        self.assertEqual(session.delivery_mode, "buffered")
        self.assertEqual(len(samples), 2)
        self.assertGreater(samples[0], 16000)
        self.assertLess(samples[1], -16000)
        self.assertEqual(model.seen[0], "Hello.")

    def test_cancellation_closes_after_first_frame(self):
        model = NativeModel()
        session = LiveSpeechSession(model, "Hello.")
        checks = {"count": 0}

        def cancelled():
            checks["count"] += 1
            return checks["count"] > 1

        frames = list(session.frames(cancelled))

        self.assertEqual(len(frames), 1)
        self.assertTrue(session.cancelled)


if __name__ == "__main__":
    unittest.main()
