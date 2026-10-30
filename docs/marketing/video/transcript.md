# “A World in Sound: Evening Tide, The Beacon”: transcript and text alternative

About 103 seconds. The real Sonic Rift app (build `d9e8179`, Windows 11) in one session, in a fresh demo profile; waits for renders are shortened. Every voice and sound is the app's own output. A narrator (the Guide) speaks over the picture; the Keeper and the Traveler are characters in the scene; a brand narrator says the closing line.

**Short description:** a small scene is built in the Sonic Rift Studio, from an empty project to a saved, exported mix: two characters' lines from Speech, an ocean bed from Sounds, and a cloned voice that keeps the Keeper's character for a new line.

## 00:00: An empty world

The Studio opens on a new, empty project, “Evening Tide: The Beacon”, with one empty Dialogue track. It is already saved.

> **Guide:** A world can begin with just a few words.  

## 00:06: Give it a keeper

On Speech, the saved voice “Keeper” is picked, the line is typed and generated, and Add to Studio places the take on the Dialogue track.

> **Keeper:** The beacon is still burning.  
> **Keeper:** Follow it toward shore.  

## 00:21: Someone answers

Still on Speech, the voice changes to “Traveler”; the answer is generated and added to the Studio after the Keeper's line.

> **Guide:** Then someone answers from across the water.  
> **Traveler:** I see it now.  
> **Traveler:** Keep the light on.  

## 00:35: Give it a shoreline

On Sounds, the procedural Ocean waves preset renders two 20-second takes with loudness figures. One is kept in the Sound library as “Shoreline waves” and added to the Studio on its own track.

> **Guide:** Give their conversation a shoreline.  
> [Ocean waves]  

## 00:48: Keep a character's voice

On Voices, New voice, Clone, the Keeper's take is the source; VoxCPM2 makes two clone takes, the test line is tried, and the result is saved as “Keeper (cloned)”. Back on Speech, the cloned voice speaks a new line, which goes to the Studio.

> **Guide:** A character can return without losing their voice.  
> **Keeper (clone):** I'll keep it burning until you're home.  

## 01:07: Arrange, balance and save

In the Studio the three lines are dragged into place (the Keeper at 2 s, the Traveler after a short pause, the cloned Keeper last), the Shoreline waves track is lowered by 6 dB, and the project is saved.

> **Guide:** Place every line where it belongs, and let the sea sit underneath.  
> **Guide:** A voice... an answer... the sound of the sea.  
> **Guide:** Together, they become a scene.  
> [Ocean waves under the scene]  

## 01:19: Hear the scene

Play mix plays the whole arranged scene, uninterrupted: both voices over the sea.

> **Keeper:** The beacon is still burning.  
> **Keeper:** Follow it toward shore.  
> **Traveler:** I see it now.  
> **Traveler:** Keep the light on.  
> **Keeper (clone):** I'll keep it burning until you're home.  

## 01:33: Export the mix

Export mix writes a mastered WAV, one stem per track and a manifest; the confirmation names the export folder.


## 01:36: Sonic Rift

End card: the Sonic Rift logo, “Make worlds you can hear.” and the words Voice, Soundscapes, Audio Studio.

> **Brand narrator:** Sonic Rift.  
> **Brand narrator:** Make worlds you can hear.  

## Voices

- **Guide** (narrator), **Keeper** and **Traveler**: synthetic voices designed with Qwen3-TTS VoiceDesign from written descriptions (no real person's voice), saved in the app's voice library; their lines were spoken with Qwen3-TTS voice cloning from those designs.
- **Keeper (cloned)**: VoxCPM2 cloning the Keeper's own take, shown in the film.
- **Brand narrator**: a separate Qwen3-TTS VoiceDesign voice for the closing line only.
