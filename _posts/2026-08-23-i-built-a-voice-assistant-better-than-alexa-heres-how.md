---
layout: post
title: "I Built a Voice Assistant Better Than Alexa — Here's How"
date: 2026-08-23
excerpt: "A practical look at building a local-first Home Assistant voice assistant with wake word detection, cloud STT/TTS, LLM-backed conversation, and real automations that go beyond rigid smart-speaker commands."
og_image: /assets/og/i-built-a-voice-assistant-better-than-alexa-heres-how.png
og_slug: i-built-a-voice-assistant-better-than-alexa-heres-how
image:
  path: /assets/og/i-built-a-voice-assistant-better-than-alexa-heres-how.png
  width: 1200
  height: 630
  alt: Home Assistant voice assistant branded social preview image
tags:
  - Home Assistant
  - Voice Assistant
  - Automation
  - AI Agents
---

Alexa is convenient until you ask it to do something that does not fit the exact command shape Amazon expected. Then it becomes a polite plastic hockey puck with a cloud dependency and commitment issues.

I wanted something better: a voice assistant that could understand natural requests, operate my smart home, trigger real automations, and eventually reason over context instead of matching a short list of canned phrases.

That is where Home Assistant comes in. Home Assistant is an open-source home automation platform that lets you connect devices, automations, scripts, dashboards, sensors, media players, thermostats, and voice assistants under one local-first control plane. Instead of every device answering to a vendor cloud, Home Assistant becomes the system that coordinates them.

For a technical user, that matters. A local-first, LLM-backed voice assistant can be more private, more flexible, and more useful than Alexa or Google Home because the logic lives in infrastructure you control. It can call your scripts. It can use your naming conventions. It can route requests through your own automation layer. And when something breaks, you can inspect the pipeline instead of waiting for a vendor forum thread from 2021 to become relevant.

I named mine Jarvis. Obviously.

## 1. The goal

The goal was not to build another voice toy.

The goal was to build a practical Home Assistant voice stack that could:

- listen for a local wake word,
- transcribe speech into text,
- send the request into a conversation engine,
- run custom Home Assistant scripts for real device control,
- speak back through a voice satellite,
- and leave enough of the system inspectable that failures could be diagnosed.

The important part is the separation of layers. Wake word detection, speech-to-text, text-to-speech, conversation handling, and device control are different jobs. Treating them as separate layers makes the system easier to debug and easier to improve.

## 2. Architecture: from wake word to action

At a high level, the pipeline looks like this:

```text
Wake word -> speech-to-text -> conversation engine -> Home Assistant action -> text-to-speech response
```

The wake word layer uses openWakeWord through the Wyoming voice stack. In plain English, openWakeWord is the local listener that decides, "someone is talking to Jarvis now." Wyoming is the protocol layer Home Assistant uses to connect voice components like wake word detection, speech-to-text, and text-to-speech services.

That matters because the assistant does not need to send every sound in the room to a vendor just to decide whether it should wake up. The wake word decision can happen locally. Good. That is how this should work.

For speech-to-text and text-to-speech, this build currently uses Home Assistant Cloud providers. Speech-to-text turns the spoken request into text. Text-to-speech turns the assistant's reply back into audio. Those services are boring when they work, which is the highest compliment infrastructure can receive.

The conversation engine is the interesting layer. That is where Home Assistant decides what the request means. A traditional smart speaker tries to match commands against known intents. An LLM-backed conversation layer can handle more flexible phrasing, infer intent from messy human language, and route the result into Home Assistant services or scripts.

The Jarvis pipeline is configured around that shape:

```yaml
# Generic example, not copied from the live system
assist_pipeline:
  name: Jarvis
  wake_word: openWakeWord
  speech_to_text: Home Assistant Cloud
  text_to_speech: Home Assistant Cloud
  conversation_engine: LLM-backed conversation provider
  language: en
```

That example is deliberately generic. The live configuration contains environment-specific entity IDs and provider details. Those do not belong in a public article, because apparently publishing your house wiring diagram to the internet is still considered bad practice.

## 3. The custom automation layer

The useful part of this build is not the wake word. It is what happens after Jarvis understands enough to act.

Home Assistant already has scripts and automations. Jarvis uses that instead of trying to make the conversation engine directly know every device. The conversation layer can route a request into a script, and the script handles the specific device control.

The main control script takes a command and, when needed, a temperature value. Internally, it branches across the common smart-home actions I actually care about:

- media playback control for a Sonos zone,
- grouped light control,
- media activity control through a Harmony-style remote layer,
- thermostat changes through a Nest-style climate layer,
- and scene activation for common lighting modes.

The real script has environment-specific entity IDs, selectors, and scene names. The public-safe structure looks like this:

```yaml
# Generic example, not copied from the live system
jarvis_control:
  mode: single
  fields:
    command:
      description: Normalized action name from the conversation layer
    temperature:
      description: Optional target temperature for climate commands
  sequence:
    - choose:
        - conditions: "{{ command == 'media_play' }}"
          sequence:
            - action: media_player.media_play
              target:
                entity_id: "<speaker_entity>"

        - conditions: "{{ command == 'lights_on' }}"
          sequence:
            - action: light.turn_on
              target:
                entity_id: "<light_group_entity>"

        - conditions: "{{ command == 'start_media_activity' }}"
          sequence:
            - action: select.select_option
              target:
                entity_id: "<activity_selector_entity>"
              data:
                option: Example Activity

        - conditions: "{{ command == 'set_temperature' }}"
          sequence:
            - action: climate.set_temperature
              target:
                entity_id: "<thermostat_entity>"
              data:
                temperature: "{{ temperature }}"
```

That is the pattern that makes Jarvis useful. The LLM does not need direct knowledge of every entity. It needs to classify the request well enough to call the right script with the right normalized command.

This is also where Home Assistant beats vendor smart speakers for technical users. If I do not like the command layer, I can change it. If I want a script to do three things in sequence, I can write that. If I want to gate an action behind conditions, I can do that too. Alexa gives you routines. Home Assistant gives you an automation engine.

There is also a timer-finished automation. It listens for the Home Assistant timer finished event and sends a spoken announcement through the voice device using text-to-speech.

Again, public-safe shape only:

```yaml
# Generic example, not copied from the live system
automation:
  alias: Voice Timer Finished Announcement
  trigger:
    - platform: event
      event_type: timer.finished
      event_data:
        entity_id: "<timer_entity>"
  action:
    - action: tts.speak
      target:
        entity_id: "<tts_provider_entity>"
      data:
        media_player_entity_id: "<voice_device_entity>"
        message: "Your timer is finished."
```

Small automation. High value. The assistant should not just set a timer. It should close the loop and tell you when the timer is done. Radical, apparently.

## 4. The honest problem: the configured engine was dead

The part that did not work cleanly was the conversation engine.

The Jarvis Assist pipeline was configured to use the Extended OpenAI Conversation engine. On paper, that was the intended LLM-backed brain for the assistant.

At runtime, it was not actually loaded. Home Assistant showed it as unavailable and restored, which means the entity existed from prior configuration state but the integration was not actively providing a working runtime entity.

That is the kind of failure that wastes time because the configuration can look right while the runtime is quietly dead. There is no dramatic explosion. No helpful villain monologue. Just a pipeline pointing at something that is technically configured and functionally useless.

The fallback that did work was the Claude conversation provider. It was loaded at runtime, available to Home Assistant, and usable as the conversation engine while the Extended OpenAI path was being diagnosed.

The lesson is simple: do not trust the YAML-shaped object. Verify the runtime entity.

For this class of problem, the troubleshooting flow is:

1. Check what the Assist pipeline is configured to use.
2. Check whether the target conversation entity is actually loaded and available.
3. If it is restored or unavailable, treat it as dead until proven otherwise.
4. Switch to a known-working conversation provider to restore functionality.
5. Then debug the broken integration separately.

That is not glamorous. It is just operations. Glamour is what people use when they do not have logs.

## 5. Why LLM-backed conversation beats rigid command matching

Traditional smart speakers are good at narrow commands:

```text
Turn on the lights.
Set a timer for ten minutes.
Play music.
```

That works until the request gets slightly more human:

```text
Make it brighter in here.
Pause whatever is playing.
Set the room to something comfortable.
Start the usual TV setup.
```

Rigid command matching wants exact phrasing. An LLM-backed conversation layer can map intent to action. It can understand that "make it brighter" probably means a light command, that "whatever is playing" probably maps to the media target, and that "comfortable" may need a default climate behavior rather than a literal value.

That flexibility is the point.

The best design is not to let the LLM freely mutate the house. That would be stupid, and not even creatively stupid. The better design is to let the LLM interpret intent and then route into a constrained automation layer with known commands.

In other words:

```text
Human language in -> constrained command out -> Home Assistant script executes known actions
```

That gives you the natural-language advantage without turning the model into an unsupervised electrician.

## 6. Lessons learned

A few lessons were obvious after building and troubleshooting this:

- Separate the voice pipeline into layers. Wake word, transcription, conversation, action, and speech response should be independently inspectable.
- Local wake word detection is worth it. Not every sound needs to leave the house just to decide whether the assistant should listen.
- Scripts are the control boundary. Let the conversation engine choose from constrained actions, not arbitrary device mutations.
- Runtime state matters more than configured state. A pipeline can point at a conversation provider that is not actually loaded.
- Keep generic examples generic. Public posts do not need real entity IDs, hardware suffixes, private room names, or personal automation names.
- Vendor assistants optimize for the average household. Home Assistant optimizes for the person willing to own the system.

That last one is both the benefit and the cost. You get control. You also get responsibility. Nietzsche probably warned someone about this, but with worse debugging tools.

## 7. What's next

The next steps are straightforward:

- finish diagnosing why the Extended OpenAI Conversation integration is configured but unavailable at runtime,
- keep the Claude-backed conversation path as the working fallback,
- tighten the command schema between conversation intent and Home Assistant scripts,
- add more robust confirmations for commands that affect security, climate, or expensive devices,
- and publish a sanitized build repo only after the examples are scrubbed for secrets, internal topology, entity names, and device-specific identifiers.

The end state I want is not a novelty assistant. It is a local-first voice operator for the home: fast wake word detection, reliable speech handling, LLM-backed understanding, and constrained Home Assistant execution.

Better than Alexa is not a high bar. But clearing it with infrastructure you control is still satisfying.
